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

Order-invariance of the recall term is deliberate. N-grams are accumulated **per
region** and unioned across regions, so reordering regions does not change the
multiset. That keeps text-fidelity blind to a reading-order swap (the reading-order
checker's job) and blind to a dropped footnote *marker* (normalization strips
markers) — while still catching corrupted *characters*, which change tokens.
"""

from __future__ import annotations

from collections import Counter

from ._normalize import containment, ngram_multiset
from .base import Checker, CheckResult, PageLike
from .pagegt import PageView


class TextFidelityChecker(Checker):
    """Fraction of GT word n-grams contained in the candidate must clear a floor.

    Args:
        n: n-gram order (default 3 = word trigrams).
        min_containment: pass threshold on the containment ratio (default 0.95).
        severity: overrides the default hard severity if given.
    """

    id = "text-fidelity"

    def __init__(
        self,
        *,
        n: int = 3,
        min_containment: float = 0.95,
        severity=None,
    ) -> None:
        super().__init__(severity=severity)
        self.n = n
        self.min_containment = min_containment

    def _page_ngrams(self, page: PageView, n: int) -> Counter:
        """Union of per-region word n-gram multisets across the page."""
        total: Counter = Counter()
        for region in page.regions:
            if region.text:
                total += ngram_multiset(region.text, n)
        return total

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
        passed = ratio >= self.min_containment

        # Precision: candidate n-grams present in GT (hallucination-facing signal).
        # Reported, not gated — the acceptable-excess threshold is escalated to the
        # experiments track (review finding D-008).
        cand_total = sum(cand_ngrams.values())
        precision = containment(cand_ngrams, gt_ngrams)
        excess = cand_total - sum(min(c, gt_ngrams.get(g, 0)) for g, c in cand_ngrams.items())

        if total == 0:
            detail = "GT page has no comparable text; nothing to contain (vacuous pass)."
        else:
            detail = (
                f"recall {covered}/{total} GT {used_n}-grams contained "
                f"(containment {ratio:.4f}, floor {self.min_containment}); "
                f"precision {precision:.4f}, {excess} candidate {used_n}-gram(s) not in GT "
                "(reported, not gated)"
            )

        return self._result(
            passed=passed,
            detail=detail,
            metrics={
                "n": used_n,
                "gt_ngrams": total,
                "contained": covered,
                # Store the exact float the gate compares (not rounded), so the
                # telemetry can never disagree with the verdict at the boundary
                # (review finding D-008).
                "containment": ratio,
                "min_containment": self.min_containment,
                "precision": precision,
                "excess_ngrams": excess,
            },
        )
