"""Tests for eval.lib.normalize module."""

from pathlib import Path

import pytest

from eval.lib.normalize import (
    NormalizedElement,
    load_ground_truth_elements,
)

REPO_ROOT = Path(__file__).parent.parent
FIXTURES_DIR = REPO_ROOT / "eval" / "fixtures" / "test_yaml"


class TestNormalizedElement:
    """Tests for NormalizedElement dataclass."""

    def test_primary_page_single(self):
        """Test primary_page with single page element."""
        elem = NormalizedElement(
            element_type="footnote",
            element_id="fn_1",
            pages=[5],
            text="Test footnote",
        )
        assert elem.primary_page == 5

    def test_primary_page_multi(self):
        """Test primary_page with multi-page element."""
        elem = NormalizedElement(
            element_type="footnote",
            element_id="fn_1",
            pages=[5, 6, 7],
            text="Test footnote spanning pages",
        )
        assert elem.primary_page == 5

    def test_primary_page_empty(self):
        """Test primary_page with no pages."""
        elem = NormalizedElement(
            element_type="footnote",
            element_id="fn_1",
            pages=[],
            text="Orphan footnote",
        )
        assert elem.primary_page == -1


class TestLoadGroundTruthElements:
    """Tests for load_ground_truth_elements function."""

    def test_load_minimal_valid(self):
        """Test loading minimal valid ground truth file."""
        yaml_path = FIXTURES_DIR / "minimal_valid.yaml"
        elements = load_ground_truth_elements(yaml_path)

        assert len(elements) == 5
        types = [e.element_type for e in elements]
        assert types.count("footnote") == 2
        assert types.count("citation") == 1
        assert types.count("page_number") == 2

    def test_load_footnote_fields(self):
        """Test that footnote fields are correctly extracted."""
        yaml_path = FIXTURES_DIR / "minimal_valid.yaml"
        elements = load_ground_truth_elements(yaml_path)

        footnotes = [e for e in elements if e.element_type == "footnote"]
        assert len(footnotes) == 2

        fn1 = next(e for e in footnotes if e.element_id == "fn_1")
        assert fn1.marker_text == "1"
        assert fn1.marker_page == 0
        assert fn1.pages == [0]
        assert "first footnote" in fn1.text
        assert fn1.attributes["note_type"] == "author"

    def test_load_citation_fields(self):
        """Test that citation fields are correctly extracted."""
        yaml_path = FIXTURES_DIR / "minimal_valid.yaml"
        elements = load_ground_truth_elements(yaml_path)

        citations = [e for e in elements if e.element_type == "citation"]
        assert len(citations) == 1

        cite = citations[0]
        assert cite.text == "(Author 2024, 42)"
        assert cite.attributes["style"] == "author_date"
        assert cite.attributes["year"] == 2024

    def test_load_multi_page_footnote(self):
        """Test loading footnote that spans multiple pages."""
        yaml_path = FIXTURES_DIR / "multi_page_footnote.yaml"
        elements = load_ground_truth_elements(yaml_path)

        footnotes = [e for e in elements if e.element_type == "footnote"]
        assert len(footnotes) == 1

        fn = footnotes[0]
        assert fn.pages == [0, 1]
        assert fn.attributes["is_multi_page"] is True
        assert fn.attributes["note_type"] == "translator"
        assert "Geworfenheit" in fn.text

    def test_file_not_found(self):
        """Test error handling for missing file."""
        with pytest.raises(FileNotFoundError):
            load_ground_truth_elements(Path("/nonexistent/path.yaml"))
