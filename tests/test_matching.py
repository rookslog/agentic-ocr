"""Tests for eval.lib.matching module."""


from eval.lib.matching import (
    ElementMatch,
    MatchConfig,
    match_elements,
)
from eval.lib.normalize import NormalizedElement


def make_element(
    element_type: str = "footnote",
    element_id: str = "fn_1",
    pages: list[int] | None = None,
    text: str = "Test text",
    char_offset: int | None = None,
) -> NormalizedElement:
    """Helper to create test elements."""
    return NormalizedElement(
        element_type=element_type,
        element_id=element_id,
        pages=pages or [0],
        text=text,
        char_offset=char_offset,
    )


class TestMatchConfig:
    """Tests for MatchConfig defaults."""

    def test_defaults(self):
        """Test default configuration values."""
        config = MatchConfig()
        assert config.threshold == 0.5
        assert config.text_weight == 0.5
        assert config.position_weight == 0.3
        assert config.attributes_weight == 0.2
        assert config.position_tolerance == 50


class TestElementMatch:
    """Tests for ElementMatch dataclass."""

    def test_is_match_exact(self):
        """Test is_match for exact match."""
        match = ElementMatch(
            ground_truth=make_element(),
            predicted=make_element(),
            match_type="exact",
            similarity_score=1.0,
        )
        assert match.is_match is True

    def test_is_match_partial(self):
        """Test is_match for partial match."""
        match = ElementMatch(
            ground_truth=make_element(),
            predicted=make_element(),
            match_type="partial",
            similarity_score=0.7,
        )
        assert match.is_match is True

    def test_is_match_missed(self):
        """Test is_match for missed element."""
        match = ElementMatch(
            ground_truth=make_element(),
            predicted=None,
            match_type="missed",
            similarity_score=0.0,
        )
        assert match.is_match is False

    def test_is_match_spurious(self):
        """Test is_match for spurious detection."""
        match = ElementMatch(
            ground_truth=None,
            predicted=make_element(),
            match_type="spurious",
            similarity_score=0.0,
        )
        assert match.is_match is False


class TestMatchElements:
    """Tests for match_elements function."""

    def test_empty_inputs(self):
        """Test matching with empty lists."""
        matches = match_elements([], [], "footnote")
        assert matches == []

    def test_no_predictions(self):
        """Test matching with no predictions (all missed)."""
        gt = [
            make_element("footnote", "fn_1", [0], "First footnote"),
            make_element("footnote", "fn_2", [0], "Second footnote"),
        ]
        matches = match_elements(gt, [], "footnote")

        assert len(matches) == 2
        assert all(m.match_type == "missed" for m in matches)
        assert all(m.predicted is None for m in matches)

    def test_no_ground_truth(self):
        """Test matching with no ground truth (all spurious)."""
        pred = [
            make_element("footnote", "fn_1", [0], "First footnote"),
            make_element("footnote", "fn_2", [0], "Second footnote"),
        ]
        matches = match_elements([], pred, "footnote")

        assert len(matches) == 2
        assert all(m.match_type == "spurious" for m in matches)
        assert all(m.ground_truth is None for m in matches)

    def test_exact_match(self):
        """Test exact matching of identical elements."""
        gt = [make_element("footnote", "fn_1", [0], "Test footnote text", char_offset=100)]
        pred = [make_element("footnote", "pred_1", [0], "Test footnote text", char_offset=100)]

        matches = match_elements(gt, pred, "footnote")

        assert len(matches) == 1
        assert matches[0].match_type == "exact"
        assert matches[0].similarity_score >= 0.95

    def test_partial_match_text_diff(self):
        """Test partial match with text differences."""
        gt = [make_element("footnote", "fn_1", [0], "The original footnote text")]
        pred = [make_element("footnote", "pred_1", [0], "The modified footnote text")]

        matches = match_elements(gt, pred, "footnote")

        assert len(matches) == 1
        assert matches[0].match_type == "partial"
        assert 0.5 < matches[0].similarity_score < 0.95

    def test_filter_by_element_type(self):
        """Test that matching filters by element type."""
        gt = [
            make_element("footnote", "fn_1", [0], "Footnote"),
            make_element("citation", "cite_1", [0], "Citation"),
        ]
        pred = [
            make_element("footnote", "pred_fn", [0], "Footnote"),
            make_element("citation", "pred_cite", [0], "Citation"),
        ]

        fn_matches = match_elements(gt, pred, "footnote")
        assert len(fn_matches) == 1
        assert fn_matches[0].ground_truth.element_type == "footnote"

        cite_matches = match_elements(gt, pred, "citation")
        assert len(cite_matches) == 1
        assert cite_matches[0].ground_truth.element_type == "citation"

    def test_page_mismatch_no_match(self):
        """Test that elements on different pages don't match."""
        gt = [make_element("footnote", "fn_1", [0], "Same text")]
        pred = [make_element("footnote", "pred_1", [5], "Same text")]

        matches = match_elements(gt, pred, "footnote")

        # Should have 1 missed + 1 spurious
        assert len(matches) == 2
        missed = [m for m in matches if m.match_type == "missed"]
        spurious = [m for m in matches if m.match_type == "spurious"]
        assert len(missed) == 1
        assert len(spurious) == 1

    def test_one_to_one_matching(self):
        """Test that each prediction matches at most one ground truth."""
        gt = [
            make_element("footnote", "fn_1", [0], "Footnote A"),
            make_element("footnote", "fn_2", [0], "Footnote B"),
        ]
        pred = [make_element("footnote", "pred_1", [0], "Footnote A")]

        matches = match_elements(gt, pred, "footnote")

        # Should have 1 match + 1 missed
        assert len(matches) == 2
        matched = [m for m in matches if m.is_match]
        missed = [m for m in matches if m.match_type == "missed"]
        assert len(matched) == 1
        assert len(missed) == 1

    def test_custom_threshold(self):
        """Test matching with custom threshold."""
        gt = [make_element("footnote", "fn_1", [0], "Original text")]
        pred = [make_element("footnote", "pred_1", [0], "Very different text")]

        # With default threshold, might be partial match
        # With high threshold, should be missed
        config = MatchConfig(threshold=0.9)
        matches = match_elements(gt, pred, "footnote", config)

        assert len(matches) == 2  # 1 missed + 1 spurious
