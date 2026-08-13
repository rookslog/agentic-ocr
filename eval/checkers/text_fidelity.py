"""Text-fidelity checker: normalized n-gram containment of GT text in candidate.

The **hard gate** is *recall* containment: the fraction of the GT page's word
n-grams that appear in the candidate (goal packet milestone 2a: "n-gram containment
of GT text in candidate text"). High recall means the candidate did not *drop* or
*corrupt* GT wording. This catches omission and character corruption.

It does **not**, on its own, catch *hallucination*: a candidate that reproduces all
GT text and *also* fabricates extra text still has recall 1.0. So the hard gate is
recall-only by design, and "anti-hallucination" is **not** a property of this gate
(review finding D-008). The hallucination-facing direction — *precision*, the
fraction of candidate n-grams that are actually in the GT — is computed and reported
in ``metrics`` (``precision``, ``excess_ngrams``) but is **not hard-gated**: the
acceptable excess threshold is an experiments-track design decision (the packet's
pause/escalate clause), so it is surfaced, not silently turned into a reward.

Order-invariance of the page-level recall term is deliberate. N-grams are
accumulated **per region** and unioned across regions, so reordering regions does not
change the multiset. That keeps text-fidelity blind to a reading-order swap (the
reading-order checker's job) and blind to a dropped footnote *marker* (normalization
strips markers) — while still catching corrupted *characters*, which change tokens.

A page-level metric alone, however, is blind to *where* the text went (review
findings H2/H3 / D-237). Pooled page-wide, swapping the complete texts of a heading
and a body block leaves the multiset identical (containment 1.0), and the page-global
n-gram backoff meant that once any long region produced trigrams, every one- or
two-token region contributed **zero** evidence — so blanking a "Book I" heading also
scored 1.0. Pooling is also blind in the opposite direction: setting *every* region's
text to the whole page's text (the "smear") gave every GT region a perfect
containment somewhere in its counterpart, and passed (round 3).

The hard gate is therefore **three-part**, over the *aligned* GT→candidate region
pairs:

1. **Page-level recall** — the original containment floor, unchanged.
2. **Per-region retention** — did this GT region's text survive *in this block*?
   Scored as the better of n-gram containment (with the region's own backoff) and
   normalized character similarity, so a short heading carries evidence and ordinary
   OCR noise does not read as deletion. Graded: a *gross* shortfall (blanked,
   swapped, missing) is never tolerated, while *minor* shortfalls get a small
   page-scaled allowance, because a stochastic pipeline produces some.
3. **Per-region misplacement** — is this block holding text that belongs to a
   *different* GT block? Never tolerated. Deliberately scoped to misplacement only:
   novel text remains ungated (see :data:`MAX_REGION_FOREIGN_RATIO`).
"""

from __future__ import annotations

from collections import Counter
from math import ceil

from rapidfuzz.distance import Levenshtein

from ._normalize import containment, ngram_multiset, normalize_text, tokens
from .align import align_regions
from .base import Checker, CheckResult, PageLike
from .pagegt import PageView

# ── Per-region retention: did *this* GT region's text survive, in this block? ──
# A region's retention score is the better of two views of the same question:
# n-gram containment (right for prose) and normalized character similarity (right
# for the short regions n-grams cannot see). Taking the max makes the character
# view a *rescue*, never an extra hurdle — round 3 found the n-gram-only rule
# false-failed ordinary OCR noise, e.g. one changed character in a two-token
# heading drove containment to 0.0 on an otherwise perfect page.
MIN_REGION_RETENTION = 0.95

# Below this, the region is not "noisy", it is *gone or replaced* — blanked,
# swapped with another block, or never emitted. Gross defects are tolerated zero
# times, whatever the page size. 0.60 sits well below any plausible OCR-noise
# level and well above the ~0.0-0.2 that deletion and text-swapping produce.
GROSS_REGION_RETENTION = 0.60

# Retention in [GROSS, MIN) is *minor*: real transcription noise (a hyphenation
# artifact, a single-character confusion) that a stochastic pipeline will produce
# at some rate on any long page. Zero tolerance here was the round-3 false-fail
# finding. The allowance scales with the page — one bad region in 40 is noise, one
# bad region in 2 is not — with a floor of 1 so a short page is not held to a
# stricter standard than a long one.
#
# MEASURED LIMIT — this aggregate is NOT yet a defensible reward signal, and an
# earlier version of this comment claimed the opposite ("the page-level containment
# floor still applies on top, so minor defects cannot accumulate into a materially
# degraded page"). That claim is false and was falsified by probe P5b: RELOCATING
# text preserves page-pooled containment exactly, so the page-level floor is not a
# backstop against it at all. Because the allowance counts regions rather than
# weighing their text, it admits roughly 0.39 x (the text share of the
# ceil(0.05 x R) largest regions) of a page sitting in the wrong block — measured at
# 20.6% of page trigrams on a skewed 100-region page under the current constants,
# with every checker passing. Both round-4 reviewers independently reached the same
# conclusion (codex: "farmable ... needs a continuous penalty or a non-farmable
# aggregate before reward use").
#
# The aggregate is therefore PRE-REGISTERED for redesign — a magnitude-weighted
# budget rather than a count — BEFORE any reward use, and these constants await
# calibration against real OCR error distributions (E2 / vision-pilot data). They are
# frozen pending that operator decision; they are a workable CI false-fail
# accommodation today and nothing more. See the evidence doc, "KNOWN-OPEN".
MINOR_REGION_DEFECT_RATE = 0.05

# ── Misplacement: is this block holding text that belongs to a different block? ──
# The fraction of a candidate region's n-grams that are absent from its own aligned
# GT region but present elsewhere in the GT page. Above this, the candidate has
# imported another block's content — the "smear" exploit, where every region is set
# to the whole page text, passed all five checkers because every GT region was
# perfectly *contained* somewhere in its counterpart.
#
# SCOPE GUARD — this gates MISPLACEMENT ONLY. An n-gram absent from the whole GT
# page is novel text, and novel text stays **ungated**: the acceptable-excess
# threshold for hallucination is an escalated experiments-track decision (review
# finding D-008) that this packet must not silently settle. Novel text is therefore
# excluded from the ratio entirely — numerator *and* denominator — and reported
# through `precision` / `excess_ngrams` instead. It was in the denominator only
# until round 4, which meant enough padding could hide a smear (codex HIGH); neutral
# has to mean neutral in both directions, unpunished and non-exculpatory. Do not
# repurpose this constant into a hallucination gate without that escalation resolved.
MAX_REGION_FOREIGN_RATIO = 0.5

# Misplacement is categorical, not stochastic: a pipeline does not accidentally put
# half of block B inside block A at a low background rate. Zero tolerance, page-size
# invariant (the reasoning that makes structure-typing's gate an integer, D-008).
MAX_REGION_MISPLACEMENTS = 0


class TextFidelityChecker(Checker):
    """Fraction of GT word n-grams contained in the candidate must clear a floor.

    Args:
        n: n-gram order (default 3 = word trigrams).
        min_containment: pass threshold on the page-level containment ratio
            (default 0.95).
        min_region_retention: per-region floor (:data:`MIN_REGION_RETENTION`).
        gross_region_retention: below this a region counts as a *gross* defect,
            tolerated zero times (:data:`GROSS_REGION_RETENTION`).
        minor_region_defect_rate: fraction of scored regions allowed to be minor
            defects, floor 1 (:data:`MINOR_REGION_DEFECT_RATE`).
        max_region_foreign_ratio: misplacement threshold
            (:data:`MAX_REGION_FOREIGN_RATIO`).
        max_region_misplacements: how many misplaced regions are tolerated
            (:data:`MAX_REGION_MISPLACEMENTS` = 0).
        severity: overrides the default hard severity if given.
    """

    id = "text-fidelity"

    def __init__(
        self,
        *,
        n: int = 3,
        min_containment: float = 0.95,
        min_region_retention: float = MIN_REGION_RETENTION,
        gross_region_retention: float = GROSS_REGION_RETENTION,
        minor_region_defect_rate: float = MINOR_REGION_DEFECT_RATE,
        max_region_foreign_ratio: float = MAX_REGION_FOREIGN_RATIO,
        max_region_misplacements: int = MAX_REGION_MISPLACEMENTS,
        severity=None,
    ) -> None:
        super().__init__(severity=severity)
        self.n = n
        self.min_containment = min_containment
        self.min_region_retention = min_region_retention
        self.gross_region_retention = gross_region_retention
        self.minor_region_defect_rate = minor_region_defect_rate
        self.max_region_foreign_ratio = max_region_foreign_ratio
        self.max_region_misplacements = max_region_misplacements

    def _page_ngrams(self, page: PageView, n: int) -> Counter:
        """Union of per-region word n-gram multisets across the page."""
        total: Counter = Counter()
        for region in page.regions:
            if region.text:
                total += ngram_multiset(region.text, n)
        return total

    def _backed_off(self, text: str, n: int) -> tuple[Counter, int]:
        """N-gram multiset of ``text``, backing ``n`` off until it yields evidence.

        Per *region*, not per page: a 2-token heading must still contribute
        bigrams even when the page's long regions produce trigrams (review finding
        H3 / D-237). Returns an empty Counter when the text has no tokens at all.
        """
        used = n
        grams = ngram_multiset(text, used)
        while sum(grams.values()) == 0 and used > 1:
            used -= 1
            grams = ngram_multiset(text, used)
        return grams, used

    def _retention(self, gt_text: str, cand_text: str) -> float:
        """How much of ``gt_text`` survives in ``cand_text``, in [0, 1].

        The better of n-gram containment (with this region's own backoff, so a
        two-token heading still yields evidence — review finding H3) and normalized
        character similarity over the normalized strings. The character view is what
        makes ordinary OCR noise survivable: "Book I" -> "Book l" has containment 0.0
        at every n but character similarity ~0.83, while a blanked or swapped region
        scores ~0.0 on both.
        """
        gt_grams, used_n = self._backed_off(gt_text, self.n)
        by_ngram = 0.0
        if sum(gt_grams.values()):
            by_ngram = containment(gt_grams, ngram_multiset(cand_text, used_n))
        by_chars = Levenshtein.normalized_similarity(
            normalize_text(gt_text), normalize_text(cand_text)
        )
        return max(by_ngram, by_chars)

    def _region_scores(
        self, gt_view: PageView, cand_view: PageView, page_gt_grams: Counter, used_n: int
    ) -> tuple[list[tuple[str, float]], list[tuple[str, float]]]:
        """Per-region retention and misplacement over the aligned GT->candidate pairs.

        Returns ``([(gt_id, retention), ...], [(gt_id, foreign_ratio), ...])``: the
        first entry per scored GT region (sorted ascending, so ``[0]`` is the worst),
        the second only for regions whose counterpart imported another block's text.
        GT regions whose text normalizes to nothing carry no evidence and are skipped
        rather than scored as a free pass or a free failure.
        """
        mapping = align_regions(gt_view, cand_view)
        retentions: list[tuple[str, float]] = []
        misplacements: list[tuple[str, float]] = []
        for region in gt_view.regions:
            if not tokens(region.text):
                continue
            counterpart_id = mapping.get(region.id)
            counterpart = cand_view.region(counterpart_id) if counterpart_id else None
            cand_text = counterpart.text if counterpart is not None else ""
            retentions.append((region.id, self._retention(region.text, cand_text)))

            # Misplacement: of the candidate n-grams attributable to the GT page at
            # all, what fraction belongs to a *different* GT region?
            #
            # Novel n-grams — in neither this region's GT nor anywhere else on the
            # page — are excluded from BOTH numerator and denominator. Neutral has to
            # mean neutral in both directions: unpunished (the D-008 hallucination
            # escalation stands) but also non-exculpatory. They used to sit in the
            # denominator only, so padding a smeared region with enough novel tokens
            # pushed the ratio under the threshold and hid the misplacement — a
            # round-4 HIGH, where hallucination actively masked a gated failure.
            cand_grams = ngram_multiset(cand_text, used_n)
            own = ngram_multiset(region.text, used_n)
            own_matched = foreign = 0
            for gram, count in cand_grams.items():
                mine = min(count, own.get(gram, 0))
                own_matched += mine
                if gram in page_gt_grams:
                    foreign += count - mine
            attributable = own_matched + foreign
            if not attributable:
                continue
            ratio = foreign / attributable
            if ratio > self.max_region_foreign_ratio:
                misplacements.append((region.id, ratio))
        retentions.sort(key=lambda d: (d[1], d[0]))
        misplacements.sort(key=lambda d: (-d[1], d[0]))
        return retentions, misplacements

    def check(self, candidate: PageLike, gt: PageLike) -> CheckResult:
        gt_view = PageView(gt)
        cand_view = PageView(candidate)

        # Back off n when the GT page is too short to form n-grams of the chosen
        # order (e.g. a page of one-word regions), so the checker still measures
        # *something* rather than passing vacuously.
        used_n = self.n
        gt_ngrams = self._page_ngrams(gt_view, used_n)
        while sum(gt_ngrams.values()) == 0 and used_n > 1:
            used_n -= 1
            gt_ngrams = self._page_ngrams(gt_view, used_n)

        cand_ngrams = self._page_ngrams(cand_view, used_n)
        # Recall: GT n-grams present in candidate (the hard gate).
        ratio = containment(gt_ngrams, cand_ngrams)
        total = sum(gt_ngrams.values())
        covered = sum(min(c, cand_ngrams.get(g, 0)) for g, c in gt_ngrams.items())

        # Per-region scoring over the aligned pairs — the half of the gate that is
        # sensitive to *where* the text is, which page-pooled n-grams cannot see.
        retentions, misplacements = self._region_scores(
            gt_view, cand_view, gt_ngrams, used_n
        )
        regions_scored = len(retentions)
        gross = [d for d in retentions if d[1] < self.gross_region_retention]
        minor = [
            d
            for d in retentions
            if self.gross_region_retention <= d[1] < self.min_region_retention
        ]
        minor_allowance = (
            max(1, ceil(self.minor_region_defect_rate * regions_scored))
            if regions_scored
            else 0
        )
        worst_region = retentions[0][1] if retentions else 1.0  # reported only when scored

        passed = (
            ratio >= self.min_containment
            and not gross
            and len(minor) <= minor_allowance
            and len(misplacements) <= self.max_region_misplacements
        )

        # Precision: candidate n-grams present in GT (hallucination-facing signal).
        # Reported, not gated — the acceptable-excess threshold is escalated to the
        # experiments track (review finding D-008).
        cand_total = sum(cand_ngrams.values())
        precision = containment(cand_ngrams, gt_ngrams)
        excess = cand_total - sum(min(c, gt_ngrams.get(g, 0)) for g, c in cand_ngrams.items())

        if total == 0 and not regions_scored:
            detail = "GT page has no comparable text; nothing to contain (vacuous pass)."
        else:
            detail = (
                f"recall {covered}/{total} GT {used_n}-grams contained "
                f"(containment {ratio:.4f}, floor {self.min_containment}); "
                f"per-region retention: {len(gross)} gross (tolerated 0), "
                f"{len(minor)} minor (tolerated {minor_allowance}) "
                f"of {regions_scored} region(s), worst {worst_region:.4f}, "
                f"floor {self.min_region_retention} / gross {self.gross_region_retention}; "
                f"misplaced {len(misplacements)} (tolerated {self.max_region_misplacements}); "
                f"precision {precision:.4f}, {excess} candidate {used_n}-gram(s) not in GT "
                "(reported, not gated)"
            )
            if gross or minor:
                shown = ", ".join(f"{rid} {value:.4f}" for rid, value in gross + minor)
                detail += f"; retention defects: [{shown}]"
            if misplacements:
                shown = ", ".join(f"{rid} {value:.4f} foreign" for rid, value in misplacements)
                detail += f"; misplaced: [{shown}]"

        return self._result(
            passed=passed,
            detail=detail,
            metrics={
                "n": used_n,
                "gt_ngrams": total,
                "contained": covered,
                "regions_scored": regions_scored,
                "region_defects": len(gross) + len(minor),
                "gross_region_defects": len(gross),
                "minor_region_defects": len(minor),
                "minor_region_defects_allowed": minor_allowance,
                "misplaced_regions": len(misplacements),
                # The freeze, made machine-visible. KNOWN-OPEN-1 lives in a doc and a
                # source comment, which a consumer wiring exit codes into a reward
                # loop may never open — so the verdict carries its own caveat, the way
                # order_signal, crashed and the raw gated floats already do.
                "reward_ready": False,
                "reward_block_reason": (
                    "pre-registered magnitude-weighted redesign of the region-defect "
                    "aggregate before any reward use (KNOWN-OPEN-1)"
                ),
                "min_region_retention": self.min_region_retention,
                "gross_region_retention": self.gross_region_retention,
                # The true minimum over every scored region, not merely the worst
                # *defect* — the first version reported a flattering 1.0 whenever
                # nothing crossed the floor (review finding L2-6). Absent, rather than
                # 1.0, when no region was scored: "nothing was measured" and "every
                # region was perfect" are different facts, and reporting the second
                # for the first is the same flattering-default mistake (round-4
                # MINOR-3). Consumers must handle the key being missing.
                **({"worst_region_retention": worst_region} if regions_scored else {}),
                # Store the exact float the gate compares (not rounded), so the
                # telemetry can never disagree with the verdict at the boundary
                # (review finding D-008).
                "containment": ratio,
                "min_containment": self.min_containment,
                "precision": precision,
                "excess_ngrams": excess,
            },
        )
