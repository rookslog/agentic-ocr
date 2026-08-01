"""Reading-order checker: the GT block sequence must be preserved in the candidate.

Reading order across registers is an L2 structure property (PLAN §4): for an
audiobook the body must read in order with apparatus separated, for a citation the
print-position mapping must hold. This checker compares the candidate's reading
order against the GT's over the **aligned** region pairs — GT region → its
counterpart under :func:`eval.checkers.align.align_regions`, which falls back to
bbox IoU when the candidate invents its own ids.

Comparing raw id sequences was a review finding (H1 / D-237) in both directions: an
honest candidate with model-generated ids scored coverage 0, while a candidate could
copy the GT's id list into its ``reading_order`` as a phantom order — its regions'
actual ``reading_order_index`` values reversed — and pass. Order is therefore always
derived from the candidate's *own* regions
(:attr:`eval.checkers.pagegt.PageView.reading_order` resolves the declared list
against that page's own region ids), and an entry naming no region of that page is a
structural violation reported by
:class:`~eval.checkers.contract.StructuralContractChecker`, never silently a match or
a miss.

The comparison uses:

- **Kendall's tau** — concordant minus discordant pairs over total pairs, in
  [-1, 1]; 1.0 means no inversions. This is the pass gate.
- **Longest-increasing-subsequence ratio** — the largest fraction of shared
  regions already in correct relative order; reported as supporting detail.

Coverage (did the candidate keep every GT region in its reading order?) is a
separate gate: a candidate that silently drops a region — or supplies one that
aligns to nothing — fails even if the survivors are correctly ordered.
"""

from __future__ import annotations

from bisect import bisect_left

from .align import align_regions
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
        gt_view = PageView(gt)
        cand_view = PageView(candidate)
        mapping = align_regions(gt_view, cand_view)

        gt_order = gt_view.reading_order
        # The candidate's order comes from its own regions — never from ids it
        # merely lists (review finding H1 / D-237).
        cand_rank = {rid: i for i, rid in enumerate(cand_view.reading_order)}

        # Aligned GT regions, taken in GT order; the ranks of their candidate
        # counterparts form the permutation whose inversions we count.
        shared: list[str] = []
        missing: list[str] = []
        cand_positions: list[int] = []
        for rid in gt_order:
            counterpart = mapping.get(rid)
            if counterpart is not None and counterpart in cand_rank:
                shared.append(rid)
                cand_positions.append(cand_rank[counterpart])
            else:
                missing.append(rid)
        coverage = len(shared) / len(gt_order) if gt_order else 1.0

        tau = kendall_tau(cand_positions)
        lis = lis_length(cand_positions)
        lis_ratio = lis / len(shared) if shared else 1.0

        passed = coverage >= self.min_coverage and tau >= self.min_tau
        detail = (
            f"coverage {coverage:.6f} (floor {self.min_coverage:.6f}), "
            f"Kendall tau {tau:.6f} (floor {self.min_tau:.6f}), "
            f"LIS {lis}/{len(shared)} in order"
        )
        if missing:
            detail += f"; {len(missing)} GT region(s) with no aligned candidate order: {missing}"

        return self._result(
            passed=passed,
            detail=detail,
            metrics={
                "n_shared": len(shared),
                # Raw, unrounded: these are the exact floats the gate compares, so
                # stored reward telemetry can never disagree with the verdict.
                # round(tau, 4) reported a perfect 1.0 for a page of 300 regions
                # with one adjacent inversion, which actually FAILED min_tau=1.0
                # (review finding L8 / D-237). Rounding is for the rendered table only.
                "coverage": coverage,
                "kendall_tau": tau,
                "lis_ratio": lis_ratio,
                "missing": len(missing),
                # Which of the three signals actually ordered each page: "declared"
                # (a canonical reading_order list), "indices", or "array" (nothing
                # declared — file order, the last resort). Surfaced so a consumer can
                # see the evidence a page was scored on rather than inferring it: on
                # "array" the verdict is sensitive to the regions list's order, which
                # is genuine order information only because nothing better exists
                # (round-4 MAJOR-2).
                "order_signal": cand_view.order_signal,
                "gt_order_signal": gt_view.order_signal,
            },
        )
