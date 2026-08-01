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
    # Depth-uniform since round 4: a declared reading_order must name every region at
    # every depth, descendants immediately following their parent. Declaring only the
    # top-level ids — which this fixture used to do — is now a contract violation; see
    # test_top_level_only_declared_order_is_a_violation and the evidence doc's E1 note
    # on the schema ambiguity this exposes.
    "reading_order": ["body-1", "quote-1", "body-2"],
}


def _verdicts(candidate, gt) -> dict[str, bool]:
    return {r.id: r.passed for r in run_checkers(candidate, gt, build_default_suite()).results}


def test_pageview_flattens_children_depth_first():
    view = PageView(NESTED_GT)
    assert [r.id for r in view.regions] == ["body-1", "quote-1", "body-2"]
    assert [r.id for r in view.top_level_regions] == ["body-1", "body-2"]
    assert view.region("quote-1") is not None
    # A child is ordered at its parent's position, on every signal path.
    assert view.reading_order == ["body-1", "quote-1", "body-2"]
    assert view.order_signal == "declared"


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


def test_top_level_only_declared_order_is_a_violation():
    """A declared order that names only the top-level regions no longer counts.

    Round-4 BLOCKER-1: the completeness rule was top-level-only, so a candidate could
    nest a child under the wrong parent and hide it behind a flattering declared
    order. Going depth-uniform closes that, and the cost is that the "declare only
    top-level ids" convention is no longer a legal declared order — a page following it
    must either name every region or declare no reading_order at all. Which convention
    the schema intends is genuinely unspecified; the rule is deliberately agnostic
    (it accepts neither silently) and the ambiguity is recorded for E1.
    """
    partial = copy.deepcopy(NESTED_GT)
    partial["reading_order"] = ["body-1", "body-2"]
    result = next(
        r
        for r in run_checkers(partial, partial, build_default_suite()).results
        if r.id == "structural-contract"
    )
    assert result.passed is False
    assert result.metrics["candidate_order_omits_regions"] == 1  # quote-1

    # Falling back to the index signal is what the rule says happens, and it still
    # puts the child at its parent's position.
    no_order = copy.deepcopy(NESTED_GT)
    no_order.pop("reading_order")
    view = PageView(no_order)
    assert view.order_signal == "indices"
    assert view.reading_order == ["body-1", "quote-1", "body-2"]
