"""Reading-order checker: the GT block sequence must be preserved in the candidate.

Reading order across registers is an L2 structure property (PLAN §4): for an
audiobook the body must read in order with apparatus separated, for a citation the
print-position mapping must hold. This checker compares the candidate's reading
order against the GT's over the region ids they share, using:

- **Kendall's tau** — concordant minus discordant pairs over total pairs, in
  [-1, 1]; 1.0 means no inversions. This is the pass gate.
- **Longest-increasing-subsequence ratio** — the largest fraction of shared
  regions already in correct relative order; reported as supporting detail.

Coverage (did the candidate keep every GT region in its reading order?) is a
separate gate: a candidate that silently drops a region from the order fails even
if the survivors are correctly ordered.
"""

from __future__ import annotations

from bisect import bisect_left

from .base import Checker, CheckResult, PageLike
from .pagegt import PageView


def kendall_tau(order: list[int]) -> float:
    """Kendall's tau of a permutation given as the rank sequence ``order``.

    ``order[i]`` is the GT rank of the element at candidate position ``i``.
    Returns (concordant - discordant) / total_pairs; 1.0 for <2 elements
    (vacuously ordered). O(n^2), fine for a page's worth of regions.
    """
    n = len(order)
    if n < 2:
        return 1.0
    concordant = discordant = 0
    for i in range(n):
        for j in range(i + 1, n):
            if order[i] < order[j]:
                concordant += 1
            elif order[i] > order[j]:
                discordant += 1
    total = concordant + discordant
    if total == 0:
        return 1.0
    return (concordant - discordant) / total


def lis_length(seq: list[int]) -> int:
    """Length of the longest strictly-increasing subsequence of ``seq``."""
    tails: list[int] = []
    for x in seq:
        i = bisect_left(tails, x)
        if i == len(tails):
            tails.append(x)
        else:
            tails[i] = x
    return len(tails)


class ReadingOrderChecker(Checker):
    """Reading order is preserved iff coverage and Kendall's tau clear their floors.

    Args:
        min_tau: Kendall's tau floor over shared regions (default 1.0 — no
            inversions; the natural "preserved" gate for a unit-test reward).
        min_coverage: fraction of GT reading-order ids that must also appear in
            the candidate's reading order (default 1.0).
        severity: overrides default hard severity if given.
    """

    id = "reading-order"

    def __init__(
        self,
        *,
        min_tau: float = 1.0,
        min_coverage: float = 1.0,
        severity=None,
    ) -> None:
        super().__init__(severity=severity)
        self.min_tau = min_tau
        self.min_coverage = min_coverage

    def check(self, candidate: PageLike, gt: PageLike) -> CheckResult:
        gt_order = PageView(gt).reading_order
        cand_order = PageView(candidate).reading_order
        cand_rank = {rid: i for i, rid in enumerate(cand_order)}

        # Shared ids, taken in GT order; their candidate ranks form the permutation.
        shared = [rid for rid in gt_order if rid in cand_rank]
        missing = [rid for rid in gt_order if rid not in cand_rank]
        coverage = len(shared) / len(gt_order) if gt_order else 1.0

        cand_positions = [cand_rank[rid] for rid in shared]
        tau = kendall_tau(cand_positions)
        lis = lis_length(cand_positions)
        lis_ratio = lis / len(shared) if shared else 1.0

        passed = coverage >= self.min_coverage and tau >= self.min_tau
        detail = (
            f"coverage {coverage:.3f} (floor {self.min_coverage:.3f}), "
            f"Kendall tau {tau:.3f} (floor {self.min_tau:.3f}), "
            f"LIS {lis}/{len(shared)} in order"
        )
        if missing:
            detail += f"; {len(missing)} GT region(s) absent from candidate order: {missing}"

        return self._result(
            passed=passed,
            detail=detail,
            metrics={
                "n_shared": len(shared),
                "coverage": round(coverage, 4),
                "kendall_tau": round(tau, 4),
                "lis_ratio": round(lis_ratio, 4),
                "missing": len(missing),
            },
        )
