"""Round-5 review items: nested index scoping, the freeze flag, bool-index coherence.

Round 6 was a micro-batch of conformance and honesty fixes on top of round 5. The
per-region tolerance semantics remain FROZEN pending an operator design decision.
"""

from __future__ import annotations

import copy

import pytest

from eval.checkers import build_default_suite, run_checkers
from eval.checkers.contract import StructuralContractChecker
from eval.checkers.pagegt import PageView
from eval.checkers.text_fidelity import TextFidelityChecker

_T = "{} carries its own distinct clause of ordinary prose here today"


def _nested_page(parent_index, child_index, declared=None, note_index=1) -> dict:
    child: dict = {
        "id": "c-1",
        "label": "block_quote",
        "bbox": {"x0": 0.2, "y0": 0.2, "x1": 0.8, "y1": 0.35},
        "text": _T.format("child"),
    }
    if child_index is not None:
        child["reading_order_index"] = child_index
    parent: dict = {
        "id": "p-1",
        "label": "text_block",
        "bbox": {"x0": 0.1, "y0": 0.1, "x1": 0.9, "y1": 0.4},
        "text": _T.format("parent"),
        "children": [child],
    }
    if parent_index is not None:
        parent["reading_order_index"] = parent_index
    note: dict = {
        "id": "n-1",
        "label": "note_area",
        "semantic_labels": ["note"],
        "bbox": {"x0": 0.1, "y0": 0.6, "x1": 0.9, "y1": 0.9},
        "text": _T.format("note"),
        "reading_order_index": note_index,
    }
    page: dict = {"regions": [parent, note]}
    if declared is not None:
        page["reading_order"] = declared
    return page


# ── MAJOR: nested reading_order_index must not be compared to the declared order ──


@pytest.mark.parametrize(
    "parent_index,child_index,note_index,label",
    [
        (0, 0, 1, "sibling-scoped: parent 0, its child 0, note 1"),
        (0, 1, 2, "page-global: parent 0, child 1, note 2"),
        (0, 7, 1, "child index arbitrary — it is never consumed"),
        (0, None, 1, "child declares no index at all"),
    ],
)
def test_nested_index_convention_does_not_affect_the_contradiction_gate(
    parent_index, child_index, note_index, label
):
    """Both depth conventions for reading_order_index must pass (round-5 adjudication).

    A nested region's index is never consumed — a child's position comes from its
    parent's ``children`` array on every signal path — so comparing nested indices
    against the declared order enforced a constraint on a field the suite does not
    read, and false-failed the natural sibling-scoped numbering convention.
    """
    page = _nested_page(parent_index, child_index, ["p-1", "c-1", "n-1"], note_index)
    result = StructuralContractChecker().check(page, page)
    assert result.passed is True, f"{label}: {result.detail}"
    assert result.metrics["candidate_order_contradicts_indices"] == 0
    assert PageView(page).reading_order == ["p-1", "c-1", "n-1"]
    assert run_checkers(page, page, build_default_suite()).exit_code() == 0


def test_top_level_index_contradiction_is_still_caught():
    # The gate it was scoped back to still bites: top-level indices that disagree with
    # the declared order remain a violation (the round-3 L1-1 property).
    page = _nested_page(0, 0, ["p-1", "c-1", "n-1"], note_index=1)
    page["regions"][0]["reading_order_index"] = 5  # parent now sorts after the note
    result = StructuralContractChecker().check(page, page)
    assert result.passed is False
    assert result.metrics["candidate_order_contradicts_indices"] > 0


def test_index_typing_validation_stays_depth_uniform():
    # Scoping the *comparison* to the top level must not weaken the *typing* rule:
    # a mistyped index at any depth is still a violation.
    page = _nested_page(0, 0, ["p-1", "c-1", "n-1"])
    page["regions"][0]["children"][0]["reading_order_index"] = 0.0
    result = StructuralContractChecker().check(page, page)
    assert result.passed is False
    assert result.metrics["candidate_non_integer_reading_order_index"] == 1


# ── F6: the index consumer and the index reporter must agree ──────────────────


def test_bool_reading_order_index_is_neither_consumed_nor_ignored():
    # bool is an int subclass. The contract checker calls True a mistyped index, so it
    # would be incoherent for RegionView to consume it as position 1.
    page = _nested_page(True, None, None)  # noqa: FBT003 — that is the point
    region = PageView(page).top_level_regions[0]
    assert region.reading_order_index is None  # not consumed as 1
    result = StructuralContractChecker().check(page, page)
    assert result.metrics["candidate_non_integer_reading_order_index"] == 1  # reported


def test_integer_reading_order_index_is_still_consumed():
    page = _nested_page(3, None, None)
    assert PageView(page).top_level_regions[0].reading_order_index == 3


# ── Reviewer recommendation: the freeze is machine-visible ────────────────────


def test_text_fidelity_declares_itself_not_reward_ready(apparatus_gt, apparatus_candidate):
    """A consumer wiring exit codes into a reward loop may never open the doc.

    KNOWN-OPEN-1 (the region-defect aggregate is farmable and awaits a
    magnitude-weighted redesign) must therefore travel with the verdict, the way
    order_signal, crashed and the raw gated floats already do.
    """
    result = TextFidelityChecker().check(apparatus_candidate, apparatus_gt)
    assert result.passed is True
    assert result.metrics["reward_ready"] is False
    assert "magnitude-weighted" in result.metrics["reward_block_reason"]
    assert "KNOWN-OPEN-1" in result.metrics["reward_block_reason"]


def test_reward_ready_survives_json_serialisation(apparatus_gt, apparatus_candidate):
    import json

    card = run_checkers(apparatus_candidate, apparatus_gt, build_default_suite())
    payload = json.loads(json.dumps(card.to_dict()))
    metrics = next(r for r in payload["results"] if r["id"] == "text-fidelity")["metrics"]
    assert metrics["reward_ready"] is False
    assert metrics["reward_block_reason"]


def test_committed_fixtures_stay_clean_under_the_scoped_rule(
    apparatus_gt, apparatus_candidate, minimal_gt, minimal_candidate
):
    for candidate, gt in ((apparatus_candidate, apparatus_gt), (minimal_candidate, minimal_gt)):
        card = run_checkers(copy.deepcopy(candidate), gt, build_default_suite())
        assert card.exit_code() == 0, card.render()
