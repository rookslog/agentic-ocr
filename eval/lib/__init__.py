"""Ground-truth evaluation library (ported from scholardoc ground_truth/lib).

Scoring core for the agentic-ocr checker suite (PLAN.md §5): edit-distance /
matching / normalization / reports against ground truth. Ported as-is from
scholardoc with imports rebased onto the ``eval.lib`` package.

Modules:
    normalize: Convert ground truth (and, later, pipeline docs) to a common format
    matching: Match predicted elements to ground truth
    metrics: Compute precision, recall, F1 scores
    reports: Generate evaluation reports (CLI, JSON, HTML)
"""

from eval.lib.matching import (
    ElementMatch,
    MatchConfig,
    match_elements,
)
from eval.lib.metrics import (
    AggregateMetrics,
    ElementMetrics,
    aggregate_metrics,
    compute_metrics,
)
from eval.lib.normalize import (
    NormalizedElement,
    load_ground_truth_elements,
    scholar_doc_to_elements,  # DEFERRED until pipeline/ lands; see normalize.py
)

__all__ = [
    # normalize
    "NormalizedElement",
    "load_ground_truth_elements",
    "scholar_doc_to_elements",
    # matching
    "ElementMatch",
    "MatchConfig",
    "match_elements",
    # metrics
    "ElementMetrics",
    "AggregateMetrics",
    "compute_metrics",
    "aggregate_metrics",
]
