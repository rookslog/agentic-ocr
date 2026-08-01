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
scored 1.0. The hard gate is therefore **two-part**: the page-level floor, plus a
per-region containment floor over the *aligned* GT→candidate region pairs, with each
region backing off its own n-gram order so a short heading still carries evidence.
"""

from __future__ import annotations

from collections import Counter

from ._normalize import containment, ngram_multiset
from .align import align_regions
from .base import Checker, CheckResult, PageLike
from .pagegt import PageView

# Per-region containment floor. Deliberately the *same* bar as the page-level floor:
# the region gate is not a new, stricter standard, it is the existing fidelity
# standard applied where page-global pooling cannot dilute it. A GT region whose
# aligned candidate is missing scores 0.0 here, so deletion costs score too.
MIN_REGION_CONTAINMENT = 0.95

# How many GT regions may fall below that floor. Zero, and — as with
# structure-typing's integer type-error gate (review finding D-008) — an integer
# count rather than a ratio, so the gate's strictness does not depend on page size:
# "one region's text is in the wrong place" must fail a 4-region page and a
# 400-region page alike.
MAX_REGION_DEFECTS = 0


class TextFidelityChecker(Checker):
    """Fraction of GT word n-grams contained in the candidate must clear a floor.

    Args:
        n: n-gram order (default 3 = word trigrams).
        min_containment: pass threshold on the page-level containment ratio
            (default 0.95).
        min_region_containment: pass threshold on each *aligned region's* own
            containment (default :data:`MIN_REGION_CONTAINMENT`).
        max_region_defects: how many GT regions may fall below that per-region
            floor (default :data:`MAX_REGION_DEFECTS` = 0).
        severity: overrides the default hard severity if given.
    """

    id = "text-fidelity"

    def __init__(
        self,
        *,
        n: int = 3,
        min_containment: float = 0.95,
        min_region_containment: float = MIN_REGION_CONTAINMENT,
        max_region_defects: int = MAX_REGION_DEFECTS,
        severity=None,
    ) -> None:
        super().__init__(severity=severity)
        self.n = n
        self.min_containment = min_containment
        self.min_region_containment = min_region_containment
        self.max_region_defects = max_region_defects

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

    def _region_defects(
        self, gt_view: PageView, cand_view: PageView
    ) -> tuple[list[tuple[str, float]], int]:
        """Aligned GT regions whose own text is not contained in their counterpart.

        Returns ``([(gt_region_id, containment), ...], n_regions_scored)``, the
        defect list sorted by ascending containment then id (deterministic). GT
        regions whose text normalizes to no tokens carry no evidence and are skipped
        rather than counted as a free pass or a free failure.
        """
        mapping = align_regions(gt_view, cand_view)
        defects: list[tuple[str, float]] = []
        scored = 0
        for region in gt_view.regions:
            if not region.text:
                continue
            gt_grams, used_n = self._backed_off(region.text, self.n)
            if sum(gt_grams.values()) == 0:
                continue  # e.g. a region whose entire text is markup
            scored += 1
            counterpart_id = mapping.get(region.id)
            counterpart = cand_view.region(counterpart_id) if counterpart_id else None
            cand_grams = (
                ngram_multiset(counterpart.text, used_n)
                if counterpart is not None and counterpart.text
                else Counter()
            )
            ratio = containment(gt_grams, cand_grams)
            if ratio < self.min_region_containment:
                defects.append((region.id, ratio))
        defects.sort(key=lambda d: (d[1], d[0]))
        return defects, scored

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

        # Per-region recall over the aligned pairs — the half of the gate that is
        # sensitive to misplacement and to deletion of short regions.
        defects, regions_scored = self._region_defects(gt_view, cand_view)
        passed = (
            ratio >= self.min_containment and len(defects) <= self.max_region_defects
        )

        # Precision: candidate n-grams present in GT (hallucination-facing signal).
        # Reported, not gated — the acceptable-excess threshold is escalated to the
        # experiments track (review finding D-008).
        cand_total = sum(cand_ngrams.values())
        precision = containment(cand_ngrams, gt_ngrams)
        excess = cand_total - sum(min(c, gt_ngrams.get(g, 0)) for g, c in cand_ngrams.items())

        if total == 0 and not defects:
            detail = "GT page has no comparable text; nothing to contain (vacuous pass)."
        else:
            detail = (
                f"recall {covered}/{total} GT {used_n}-grams contained "
                f"(containment {ratio:.4f}, floor {self.min_containment}); "
                f"per-region: {regions_scored - len(defects)}/{regions_scored} region(s) "
                f"at or above floor {self.min_region_containment} "
                f"(tolerated {self.max_region_defects}); "
                f"precision {precision:.4f}, {excess} candidate {used_n}-gram(s) not in GT "
                "(reported, not gated)"
            )
            if defects:
                shown = ", ".join(f"{rid} {value:.4f}" for rid, value in defects)
                detail += f"; region defects: [{shown}]"

        return self._result(
            passed=passed,
            detail=detail,
            metrics={
                "n": used_n,
                "gt_ngrams": total,
                "contained": covered,
                "regions_scored": regions_scored,
                "region_defects": len(defects),
                "min_region_containment": self.min_region_containment,
                "worst_region_containment": defects[0][1] if defects else 1.0,
                # Store the exact float the gate compares (not rounded), so the
                # telemetry can never disagree with the verdict at the boundary
                # (review finding D-008).
                "containment": ratio,
                "min_containment": self.min_containment,
                "precision": precision,
                "excess_ngrams": excess,
            },
        )
