"""Text-fidelity checker: normalized n-gram containment of GT text in candidate.

PLAN §5 names "n-gram containment of output against GT/source" as an
anti-hallucination tripwire: the ground-truth wording should *appear* in the
candidate. This checker measures the fraction of the GT page's word n-grams that
are present in the candidate, after normalization.

Order-invariance is deliberate. N-grams are accumulated **per region** (within a
region's token stream) and unioned across regions, so reordering regions does not
change the n-gram multiset. That is what keeps text-fidelity blind to a
reading-order swap (the reading-order checker's job) and blind to a dropped
footnote *marker* (normalization strips markers) — while still catching corrupted
*characters*, which change tokens and therefore n-grams.
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
        ratio = containment(gt_ngrams, cand_ngrams)
        total = sum(gt_ngrams.values())
        covered = round(ratio * total)
        passed = ratio >= self.min_containment

        if total == 0:
            detail = "GT page has no comparable text; nothing to contain (vacuous pass)."
        else:
            detail = (
                f"{covered}/{total} GT {used_n}-grams contained in candidate "
                f"(containment {ratio:.3f}, floor {self.min_containment:.3f})"
            )

        return self._result(
            passed=passed,
            detail=detail,
            metrics={
                "n": used_n,
                "gt_ngrams": total,
                "contained": covered,
                "containment": round(ratio, 4),
                "min_containment": self.min_containment,
            },
        )
