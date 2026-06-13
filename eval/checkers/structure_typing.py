"""Structure-typing checker: GT block types recovered, scored per-type P/R/F1.

PLAN §4 (L2) makes "typed semantics" a first-class property: body vs footnote vs
heading are different *types*, not markdown decorations. This checker aligns
candidate regions to GT regions and scores, per canonical block type
(body / footnote / heading / other), the standard detection triple:

- **TP** — a GT region of type T whose aligned candidate is also type T.
- **FN** — a GT region of type T with no aligned candidate of type T.
- **FP** — a candidate region of type T that is not the counterpart of any GT
  region of type T.

The per-type precision / recall / F1 and the micro/macro aggregates are computed
by **reusing** :mod:`eval.lib.metrics` (``ElementMetrics`` / ``AggregateMetrics``)
— the ported scoring core, not a reimplementation.

The pass gate is an **integer count of type-errors** (total FP + FN over all
types) and passes iff that count is zero — i.e. exact type recovery. A float micro-F1
floor was rejected (review finding D-008): micro-F1 = (N-1)/N for a single mistyped
region, so a floor like 0.999 silently tolerates one error on a 1000-region page
while demanding perfection on a small one — the gate's strictness would depend on
page size, not candidate quality, which is a reward-hack as pages scale. micro/macro
F1 are still reported (for later reward shaping), but the hard gate is page-size
invariant.
"""

from __future__ import annotations

from eval.lib.metrics import AggregateMetrics, ElementMetrics, aggregate_metrics

from .align import align_regions
from .base import Checker, CheckResult, PageLike
from .pagegt import PageView


class StructureTypingChecker(Checker):
    """Region block types must be recovered exactly; gate on zero type-errors.

    Args:
        max_type_errors: the largest tolerated count of (FP + FN) type-errors over
            all block types (default 0 = exact recovery). Page-size invariant,
            unlike a micro-F1 floor.
        severity: overrides default hard severity if given.
    """

    id = "structure-typing"

    def __init__(self, *, max_type_errors: int = 0, severity=None) -> None:
        super().__init__(severity=severity)
        self.max_type_errors = max_type_errors

    def _score(self, gt: PageView, candidate: PageView) -> AggregateMetrics:
        mapping = align_regions(gt, candidate)
        reverse = {cand_id: gt_id for gt_id, cand_id in mapping.items() if cand_id is not None}

        gt_by_id = {r.id: r for r in gt.regions if r.id}
        cand_by_id = {r.id: r for r in candidate.regions if r.id}

        types = {r.block_type for r in gt.regions} | {r.block_type for r in candidate.regions}

        by_type: dict[str, ElementMetrics] = {}
        for type_name in sorted(types):
            tp = fn = fp = 0

            # Recall side: walk GT regions of this type.
            for region in gt.regions:
                if region.block_type != type_name:
                    continue
                cand_id = mapping.get(region.id)
                cand_region = cand_by_id.get(cand_id) if cand_id else None
                if cand_region is not None and cand_region.block_type == type_name:
                    tp += 1
                else:
                    fn += 1

            # Precision side: candidate regions of this type that aren't a correct
            # counterpart of a same-type GT region are false positives.
            for region in candidate.regions:
                if region.block_type != type_name:
                    continue
                gt_id = reverse.get(region.id)
                gt_region = gt_by_id.get(gt_id) if gt_id else None
                if gt_region is not None and gt_region.block_type == type_name:
                    continue  # already counted as TP on the recall side
                fp += 1

            by_type[type_name] = ElementMetrics(
                true_positives=tp,
                false_positives=fp,
                false_negatives=fn,
            )
        return aggregate_metrics(by_type)

    def check(self, candidate: PageLike, gt: PageLike) -> CheckResult:
        metrics = self._score(PageView(gt), PageView(candidate))
        fp = metrics.total_false_positives
        fn = metrics.total_false_negatives
        type_errors = fp + fn
        passed = type_errors <= self.max_type_errors

        per_type = ", ".join(
            f"{t}: P{m.precision:.2f}/R{m.recall:.2f}/F{m.f1:.2f}"
            for t, m in sorted(metrics.by_type.items())
        )
        detail = (
            f"{type_errors} type-error(s) [FP {fp} + FN {fn}] "
            f"(tolerated {self.max_type_errors}); "
            f"micro-F1 {metrics.micro_f1:.3f}, macro-F1 {metrics.macro_f1:.3f}; [{per_type}]"
        )

        type_metrics: dict[str, float] = {}
        for type_name, m in metrics.by_type.items():
            type_metrics[f"{type_name}_f1"] = round(m.f1, 4)
        return self._result(
            passed=passed,
            detail=detail,
            metrics={
                "type_errors": type_errors,
                "false_positives": fp,
                "false_negatives": fn,
                "micro_f1": round(metrics.micro_f1, 4),
                "macro_f1": round(metrics.macro_f1, 4),
                **type_metrics,
            },
        )
