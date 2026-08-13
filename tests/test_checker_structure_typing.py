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


def test_gate_is_page_size_invariant(apparatus_gt):
    # Review finding D-008: a float micro-F1 floor (e.g. 0.999) would PASS a large
    # page with one fully-mistyped region — micro-F1 = (N-1)/N → 0.999 at N=1000.
    # The integer zero-error gate must FAIL it regardless of page size.
    def page(n_regions: int, mistype_one: bool) -> dict:
        regions = []
        order = []
        for i in range(n_regions):
            label = "text_block"
            if mistype_one and i == 0:
                label = "section_header"  # one region typed wrong
            regions.append(
                {
                    "id": f"r{i}",
                    "label": label,
                    "bbox": {"x0": 0.1, "y0": 0.0, "x1": 0.9, "y1": 0.001},
                    "text": f"region {i} body text here",
                    "reading_order_index": i,
                }
            )
            order.append(f"r{i}")
        return {"regions": regions, "reading_order": order}

    gt = page(1000, mistype_one=False)
    good = page(1000, mistype_one=False)
    one_wrong = page(1000, mistype_one=True)

    assert StructureTypingChecker().check(good, gt).passed is True
    bad = StructureTypingChecker().check(one_wrong, gt)
    assert bad.passed is False  # would have passed a 0.999 float floor
    assert bad.metrics["type_errors"] >= 1
    assert bad.metrics["micro_f1"] >= 0.998  # still ~0.999 — but the gate is integer


def test_deterministic(apparatus_gt, apparatus_candidate):
    a = StructureTypingChecker().check(apparatus_candidate, apparatus_gt)
    b = StructureTypingChecker().check(apparatus_candidate, apparatus_gt)
    assert a.to_dict() == b.to_dict()


def _view(data):
    from eval.checkers.pagegt import PageView

    return PageView(data)
