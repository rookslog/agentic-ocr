"""Compute evaluation metrics from element matches.

This module provides:
1. ElementMetrics - Metrics for a single element type
2. AggregateMetrics - Metrics across all element types
3. compute_metrics() - Compute metrics from matches
4. aggregate_metrics() - Combine per-type metrics
"""

from __future__ import annotations

from dataclasses import dataclass, field

from eval.lib.matching import ElementMatch


@dataclass
class ElementMetrics:
    """Metrics for a single element type."""

    # Detection counts
    true_positives: int = 0
    false_positives: int = 0
    false_negatives: int = 0

    # Quality metrics (for matched elements)
    total_text_similarity: float = 0.0
    total_position_similarity: float = 0.0
    matched_count: int = 0

    # Error analysis
    error_counts: dict[str, int] = field(default_factory=dict)

    @property
    def precision(self) -> float:
        """Precision = TP / (TP + FP)."""
        denom = self.true_positives + self.false_positives
        if denom == 0:
            return 0.0
        return self.true_positives / denom

    @property
    def recall(self) -> float:
        """Recall = TP / (TP + FN)."""
        denom = self.true_positives + self.false_negatives
        if denom == 0:
            return 0.0
        return self.true_positives / denom

    @property
    def f1(self) -> float:
        """F1 = 2 * (precision * recall) / (precision + recall)."""
        p, r = self.precision, self.recall
        if p + r == 0:
            return 0.0
        return 2 * (p * r) / (p + r)

    @property
    def mean_text_similarity(self) -> float:
        """Average text similarity for matched elements."""
        if self.matched_count == 0:
            return 0.0
        return self.total_text_similarity / self.matched_count

    @property
    def mean_position_similarity(self) -> float:
        """Average position similarity for matched elements."""
        if self.matched_count == 0:
            return 0.0
        return self.total_position_similarity / self.matched_count

    @property
    def support(self) -> int:
        """Total ground truth elements (TP + FN)."""
        return self.true_positives + self.false_negatives

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "true_positives": self.true_positives,
            "false_positives": self.false_positives,
            "false_negatives": self.false_negatives,
            "precision": round(self.precision, 4),
            "recall": round(self.recall, 4),
            "f1": round(self.f1, 4),
            "mean_text_similarity": round(self.mean_text_similarity, 4),
            "mean_position_similarity": round(self.mean_position_similarity, 4),
            "support": self.support,
            "error_counts": self.error_counts,
        }


@dataclass
class AggregateMetrics:
    """Aggregate metrics across all element types."""

    by_type: dict[str, ElementMetrics] = field(default_factory=dict)

    @property
    def total_true_positives(self) -> int:
        """Total TP across all types."""
        return sum(m.true_positives for m in self.by_type.values())

    @property
    def total_false_positives(self) -> int:
        """Total FP across all types."""
        return sum(m.false_positives for m in self.by_type.values())

    @property
    def total_false_negatives(self) -> int:
        """Total FN across all types."""
        return sum(m.false_negatives for m in self.by_type.values())

    @property
    def micro_precision(self) -> float:
        """Micro-averaged precision (across all elements)."""
        denom = self.total_true_positives + self.total_false_positives
        if denom == 0:
            return 0.0
        return self.total_true_positives / denom

    @property
    def micro_recall(self) -> float:
        """Micro-averaged recall (across all elements)."""
        denom = self.total_true_positives + self.total_false_negatives
        if denom == 0:
            return 0.0
        return self.total_true_positives / denom

    @property
    def micro_f1(self) -> float:
        """Micro-averaged F1 (across all elements)."""
        p, r = self.micro_precision, self.micro_recall
        if p + r == 0:
            return 0.0
        return 2 * (p * r) / (p + r)

    @property
    def macro_precision(self) -> float:
        """Macro-averaged precision (unweighted average across types)."""
        if not self.by_type:
            return 0.0
        return sum(m.precision for m in self.by_type.values()) / len(self.by_type)

    @property
    def macro_recall(self) -> float:
        """Macro-averaged recall (unweighted average across types)."""
        if not self.by_type:
            return 0.0
        return sum(m.recall for m in self.by_type.values()) / len(self.by_type)

    @property
    def macro_f1(self) -> float:
        """Macro-averaged F1 (unweighted average across types)."""
        if not self.by_type:
            return 0.0
        return sum(m.f1 for m in self.by_type.values()) / len(self.by_type)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "micro_precision": round(self.micro_precision, 4),
            "micro_recall": round(self.micro_recall, 4),
            "micro_f1": round(self.micro_f1, 4),
            "macro_precision": round(self.macro_precision, 4),
            "macro_recall": round(self.macro_recall, 4),
            "macro_f1": round(self.macro_f1, 4),
            "by_type": {k: v.to_dict() for k, v in self.by_type.items()},
        }


def compute_metrics(matches: list[ElementMatch]) -> ElementMetrics:
    """Compute metrics from a list of element matches.

    Args:
        matches: List of ElementMatch objects for a single element type

    Returns:
        ElementMetrics with precision, recall, F1, etc.
    """
    metrics = ElementMetrics()

    for match in matches:
        if match.match_type == "exact":
            metrics.true_positives += 1
            metrics.matched_count += 1
            metrics.total_text_similarity += match.text_similarity
            metrics.total_position_similarity += match.position_similarity

        elif match.match_type == "partial":
            # Count partial matches as TP for detection metrics
            metrics.true_positives += 1
            metrics.matched_count += 1
            metrics.total_text_similarity += match.text_similarity
            metrics.total_position_similarity += match.position_similarity

            # Track error types
            if match.error_details:
                for error_key in match.error_details:
                    metrics.error_counts[error_key] = metrics.error_counts.get(error_key, 0) + 1

        elif match.match_type == "missed":
            metrics.false_negatives += 1

            # Track miss reasons
            if match.error_details and "reason" in match.error_details:
                reason = match.error_details["reason"]
                metrics.error_counts[f"missed_{reason}"] = (
                    metrics.error_counts.get(f"missed_{reason}", 0) + 1
                )

        elif match.match_type == "spurious":
            metrics.false_positives += 1

            # Track spurious reasons
            if match.error_details and "reason" in match.error_details:
                reason = match.error_details["reason"]
                metrics.error_counts[f"spurious_{reason}"] = (
                    metrics.error_counts.get(f"spurious_{reason}", 0) + 1
                )

    return metrics


def aggregate_metrics(by_type: dict[str, ElementMetrics]) -> AggregateMetrics:
    """Create aggregate metrics from per-type metrics.

    Args:
        by_type: Dictionary mapping element type to ElementMetrics

    Returns:
        AggregateMetrics with micro/macro averages
    """
    return AggregateMetrics(by_type=by_type)
