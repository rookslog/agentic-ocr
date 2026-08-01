"""Nested-region traversal (review finding M5 / D-237).

``Region.children`` is part of the PageGT contract (scholar-schema
``scholargt/schema/spatial.py``). Before the fix ``PageView`` walked only top-level
regions, so a GT ``text_block`` containing a nested ``block_quote`` — with all its
text — could be deleted by a candidate at zero cost: every checker passed.
These tests pin that a deleted (or mistyped) child now costs score.
"""

from __future__ import annotations

import copy

from eval.checkers import build_default_suite, run_checkers
from eval.checkers.pagegt import PageView

_CHILD = {
    "id": "quote-1",
    "label": "block_quote",
    "bbox": {"x0": 0.15, "y0": 0.25, "x1": 0.85, "y1": 0.40},
    "text": "the unexamined life is not worth living for a human being",
    "reading_order_index": 1,
}

NESTED_GT = {
    "regions": [
        {
            "id": "body-1",
            "label": "text_block",
            "bbox": {"x0": 0.12, "y0": 0.15, "x1": 0.88, "y1": 0.45},
            "text": "Socrates then addressed the jury with these words.",
            "reading_order_index": 0,
            "children": [_CHILD],
        },
        {
            "id": "body-2",
            "label": "text_block",
            "bbox": {"x0": 0.12, "y0": 0.47, "x1": 0.88, "y1": 0.70},
            "text": "And having said this he sat down among his friends again.",
            "reading_order_index": 2,
        },
    ],
    "reading_order": ["body-1", "body-2"],
}


def _verdicts(candidate, gt) -> dict[str, bool]:
    return {r.id: r.passed for r in run_checkers(candidate, gt, build_default_suite()).results}


def test_pageview_flattens_children_depth_first():
    view = PageView(NESTED_GT)
    assert [r.id for r in view.regions] == ["body-1", "quote-1", "body-2"]
    assert [r.id for r in view.top_level_regions] == ["body-1", "body-2"]
    assert view.region("quote-1") is not None
    # A child follows its parent in reading order, even though the declared
    # reading_order list names only the top-level regions.
    assert view.reading_order == ["body-1", "quote-1", "body-2"]


def test_child_region_text_is_scored():
    view = PageView(NESTED_GT)
    assert _CHILD["text"] in view.full_text()


def test_deleting_a_child_region_costs_score():
    faithful = copy.deepcopy(NESTED_GT)
    assert _verdicts(faithful, NESTED_GT) == {
        "structural-contract": True,
        "text-fidelity": True,
        "reading-order": True,
        "footnote-anchor": True,
        "structure-typing": True,
    }

    deleted = copy.deepcopy(NESTED_GT)
    deleted["regions"][0].pop("children")
    verdicts = _verdicts(deleted, NESTED_GT)
    # The child's text is gone (per-region containment) and its region is absent
    # from the candidate's reading order.
    assert verdicts["text-fidelity"] is False
    assert verdicts["reading-order"] is False


def test_mistyping_a_child_region_costs_score():
    mistyped = copy.deepcopy(NESTED_GT)
    mistyped["regions"][0]["children"][0]["label"] = "note_area"
    mistyped["regions"][0]["children"][0]["semantic_labels"] = ["note"]
    assert _verdicts(mistyped, NESTED_GT)["structure-typing"] is False
