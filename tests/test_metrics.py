"""Tests for eval.lib.metrics module."""

from typing import Literal

from eval.lib.matching import ElementMatch
from eval.lib.metrics import (
    AggregateMetrics,
    ElementMetrics,
    aggregate_metrics,
    compute_metrics,
)
from eval.lib.normalize import NormalizedElement


def make_element(element_id: str = "test") -> NormalizedElement:
    """Helper to create minimal test element."""
    return NormalizedElement(
        element_type="footnote",
        element_id=element_id,
        pages=[0],
        text="Test",
    )


def make_match(
    match_type: Literal["exact", "partial", "missed", "spurious"],
    text_sim: float = 0.0,
    pos_sim: float = 0.0,
) -> ElementMatch:
    """Helper to create test matches."""
    gt = make_element("gt") if match_type != "spurious" else None
    pred = make_element("pred") if match_type != "missed" else None

    return ElementMatch(
        ground_truth=gt,
        predicted=pred,
        match_type=match_type,
        similarity_score=(text_sim + pos_sim) / 2,
        text_similarity=text_sim,
        position_similarity=pos_sim,
        error_details={"reason": "test"} if match_type in ("missed", "spurious") else None,
    )


class TestElementMetrics:
    """Tests for ElementMetrics dataclass."""

    def test_precision_basic(self):
        """Test precision calculation."""
        metrics = ElementMetrics(true_positives=8, false_positives=2, false_negatives=0)
        assert metrics.precision == 0.8

    def test_precision_zero_denominator(self):
        """Test precision when no predictions."""
        metrics = ElementMetrics(true_positives=0, false_positives=0, false_negatives=5)
        assert metrics.precision == 0.0

    def test_recall_basic(self):
        """Test recall calculation."""
        metrics = ElementMetrics(true_positives=8, false_positives=0, false_negatives=2)
        assert metrics.recall == 0.8

    def test_recall_zero_denominator(self):
        """Test recall when no ground truth."""
        metrics = ElementMetrics(true_positives=0, false_positives=5, false_negatives=0)
        assert metrics.recall == 0.0

    def test_f1_basic(self):
        """Test F1 calculation."""
        metrics = ElementMetrics(true_positives=8, false_positives=2, false_negatives=2)
        # precision = 8/10 = 0.8, recall = 8/10 = 0.8
        # F1 = 2 * 0.8 * 0.8 / (0.8 + 0.8) = 0.8
        assert abs(metrics.f1 - 0.8) < 0.0001

    def test_f1_zero(self):
        """Test F1 when both precision and recall are 0."""
        metrics = ElementMetrics(true_positives=0, false_positives=0, false_negatives=0)
        assert metrics.f1 == 0.0

    def test_support(self):
        """Test support (ground truth count)."""
        metrics = ElementMetrics(true_positives=5, false_positives=3, false_negatives=2)
        assert metrics.support == 7  # TP + FN

    def test_mean_text_similarity(self):
        """Test mean text similarity calculation."""
        metrics = ElementMetrics(
            true_positives=2,
            total_text_similarity=1.8,
            matched_count=2,
        )
        assert metrics.mean_text_similarity == 0.9

    def test_mean_text_similarity_no_matches(self):
        """Test mean text similarity with no matches."""
        metrics = ElementMetrics(true_positives=0, matched_count=0)
        assert metrics.mean_text_similarity == 0.0

    def test_to_dict(self):
        """Test serialization to dictionary."""
        metrics = ElementMetrics(
            true_positives=8,
            false_positives=2,
            false_negatives=2,
        )
        d = metrics.to_dict()

        assert d["true_positives"] == 8
        assert d["precision"] == 0.8
        assert d["recall"] == 0.8
        assert d["f1"] == 0.8
        assert d["support"] == 10


class TestAggregateMetrics:
    """Tests for AggregateMetrics dataclass."""

    def test_micro_f1(self):
        """Test micro-averaged F1 calculation."""
        by_type = {
            "footnote": ElementMetrics(true_positives=5, false_positives=1, false_negatives=1),
            "citation": ElementMetrics(true_positives=3, false_positives=1, false_negatives=1),
        }
        agg = AggregateMetrics(by_type=by_type)

        # Total: TP=8, FP=2, FN=2
        # Precision = 8/10, Recall = 8/10, F1 = 0.8
        assert abs(agg.micro_f1 - 0.8) < 0.0001

    def test_macro_f1(self):
        """Test macro-averaged F1 calculation."""
        by_type = {
            "footnote": ElementMetrics(true_positives=5, false_positives=0, false_negatives=5),
            # F1 = 2 * (1.0 * 0.5) / 1.5 = 0.667
            "citation": ElementMetrics(true_positives=5, false_positives=5, false_negatives=0),
            # F1 = 2 * (0.5 * 1.0) / 1.5 = 0.667
        }
        agg = AggregateMetrics(by_type=by_type)

        # Macro F1 = average of type F1s
        assert abs(agg.macro_f1 - 0.667) < 0.01

    def test_empty(self):
        """Test aggregation with no types."""
        agg = AggregateMetrics(by_type={})
        assert agg.micro_f1 == 0.0
        assert agg.macro_f1 == 0.0

    def test_to_dict(self):
        """Test serialization to dictionary."""
        by_type = {
            "footnote": ElementMetrics(true_positives=10, false_positives=0, false_negatives=0),
        }
        agg = AggregateMetrics(by_type=by_type)
        d = agg.to_dict()

        assert d["micro_f1"] == 1.0
        assert "footnote" in d["by_type"]


class TestComputeMetrics:
    """Tests for compute_metrics function."""

    def test_empty_matches(self):
        """Test with no matches."""
        metrics = compute_metrics([])
        assert metrics.true_positives == 0
        assert metrics.false_positives == 0
        assert metrics.false_negatives == 0

    def test_all_exact(self):
        """Test with all exact matches."""
        matches = [
            make_match("exact", text_sim=1.0, pos_sim=1.0),
            make_match("exact", text_sim=1.0, pos_sim=1.0),
        ]
        metrics = compute_metrics(matches)

        assert metrics.true_positives == 2
        assert metrics.false_positives == 0
        assert metrics.false_negatives == 0
        assert metrics.f1 == 1.0

    def test_all_partial(self):
        """Test with all partial matches."""
        matches = [
            make_match("partial", text_sim=0.8, pos_sim=0.9),
            make_match("partial", text_sim=0.7, pos_sim=0.8),
        ]
        metrics = compute_metrics(matches)

        # Partial matches count as TP
        assert metrics.true_positives == 2
        assert metrics.matched_count == 2
        assert 0.7 < metrics.mean_text_similarity < 0.9

    def test_all_missed(self):
        """Test with all missed."""
        matches = [
            make_match("missed"),
            make_match("missed"),
        ]
        metrics = compute_metrics(matches)

        assert metrics.true_positives == 0
        assert metrics.false_negatives == 2
        assert metrics.recall == 0.0

    def test_all_spurious(self):
        """Test with all spurious."""
        matches = [
            make_match("spurious"),
            make_match("spurious"),
        ]
        metrics = compute_metrics(matches)

        assert metrics.true_positives == 0
        assert metrics.false_positives == 2
        assert metrics.precision == 0.0

    def test_mixed_results(self):
        """Test with mix of match types."""
        matches = [
            make_match("exact"),
            make_match("partial"),
            make_match("missed"),
            make_match("spurious"),
        ]
        metrics = compute_metrics(matches)

        assert metrics.true_positives == 2  # exact + partial
        assert metrics.false_positives == 1  # spurious
        assert metrics.false_negatives == 1  # missed
        assert metrics.precision == 2 / 3  # 2 / (2 + 1)
        assert metrics.recall == 2 / 3  # 2 / (2 + 1)

    def test_error_tracking(self):
        """Test that error types are tracked."""
        matches = [
            make_match("missed"),
            make_match("missed"),
            make_match("spurious"),
        ]
        metrics = compute_metrics(matches)

        assert "missed_test" in metrics.error_counts
        assert metrics.error_counts["missed_test"] == 2
        assert "spurious_test" in metrics.error_counts


class TestAggregateMetricsFunction:
    """Tests for aggregate_metrics function."""

    def test_creates_aggregate(self):
        """Test that function creates AggregateMetrics."""
        by_type = {"footnote": ElementMetrics(true_positives=5)}
        agg = aggregate_metrics(by_type)

        assert isinstance(agg, AggregateMetrics)
        assert "footnote" in agg.by_type
