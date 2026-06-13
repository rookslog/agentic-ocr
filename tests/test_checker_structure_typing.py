"""Tests for the structure-typing checker (per-type P/R via eval.lib.metrics)."""

from __future__ import annotations

from eval.checkers.structure_typing import StructureTypingChecker
from eval.lib.metrics import AggregateMetrics
from tests import _mutations as M


def test_passes_on_clean_candidate(apparatus_gt, apparatus_candidate):
    result = StructureTypingChecker().check(apparatus_candidate, apparatus_gt)
    assert result.passed is True
    assert result.metrics["micro_f1"] == 1.0
    # All three block types present and perfectly recovered.
    assert result.metrics["heading_f1"] == 1.0
    assert result.metrics["body_f1"] == 1.0
    assert result.metrics["footnote_f1"] == 1.0


def test_reuses_eval_lib_metrics(apparatus_gt, apparatus_candidate):
    # The checker scores via eval.lib.metrics.AggregateMetrics (the ported core),
    # not a private reimplementation.
    checker = StructureTypingChecker()
    agg = checker._score(_view(apparatus_gt), _view(apparatus_candidate))
    assert isinstance(agg, AggregateMetrics)
    assert agg.micro_f1 == 1.0


def test_mislabel_heading_as_body_fails(apparatus_gt, apparatus_candidate):
    mutated = M.mislabel(apparatus_candidate, "head-1", "text_block")
    result = StructureTypingChecker().check(mutated, apparatus_gt)
    assert result.passed is False
    # heading recall collapses (its only region became a body); body precision drops.
    assert result.metrics["heading_f1"] < 1.0


def test_semantic_note_beats_spatial_label(apparatus_gt):
    # A region typed text_block spatially but note semantically is a footnote.
    import copy

    cand = copy.deepcopy(apparatus_gt)
    for region in cand["regions"]:
        if region["id"] == "note-1":
            region["label"] = "text_block"  # spatial says body...
            region["semantic_labels"] = ["note"]  # ...semantic still says note
    result = StructureTypingChecker().check(cand, apparatus_gt)
    assert result.passed is True  # still recovered as footnote


def test_deterministic(apparatus_gt, apparatus_candidate):
    a = StructureTypingChecker().check(apparatus_candidate, apparatus_gt)
    b = StructureTypingChecker().check(apparatus_candidate, apparatus_gt)
    assert a.to_dict() == b.to_dict()


def _view(data):
    from eval.checkers.pagegt import PageView

    return PageView(data)
