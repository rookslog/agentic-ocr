"""Tests for deterministic region alignment (eval.checkers.align).

The load-bearing property (review finding D-008): a candidate that merely lists the
same regions in a different order is *semantically identical*, so it must produce an
identical alignment — and therefore identical verdicts. Tie-breaks key on intrinsic
region ids, never on array position.
"""

from __future__ import annotations

import copy

from eval.checkers import build_default_suite, run_checkers
from eval.checkers.align import align_regions
from eval.checkers.pagegt import PageView

# A bbox shared by both regions — the exact IoU-tie scenario an array-order
# tie-break would resolve unstably.
_BBOX = {"x0": 0.1, "y0": 0.1, "x1": 0.9, "y1": 0.9}

# GT with two regions sharing _BBOX but distinct types.
_TIE_GT = {
    "regions": [
        {"id": "gt-body", "label": "text_block", "bbox": _BBOX,
         "text": "alpha beta gamma delta", "reading_order_index": 0},
        {"id": "gt-note", "label": "note_area", "semantic_labels": ["note"], "bbox": _BBOX,
         "text": "epsilon zeta eta theta", "reading_order_index": 1},
    ],
    "reading_order": ["gt-body", "gt-note"],
}

# Candidate carrying the same two regions (same bboxes) but with model-chosen ids
# that don't match GT, forcing the Pass-2 bbox-IoU path with a tie.
_CAND_REGIONS = [
    {"id": "cand-x", "label": "text_block", "bbox": _BBOX,
     "text": "alpha beta gamma delta", "reading_order_index": 0},
    {"id": "cand-y", "label": "note_area", "semantic_labels": ["note"], "bbox": _BBOX,
     "text": "epsilon zeta eta theta", "reading_order_index": 1},
]


def _candidate(regions: list) -> dict:
    return {"regions": regions, "reading_order": [r["id"] for r in regions]}


def test_alignment_is_invariant_to_candidate_region_order_under_ties():
    forward = align_regions(PageView(_TIE_GT), PageView(_candidate(_CAND_REGIONS)))
    reversed_regions = list(reversed(copy.deepcopy(_CAND_REGIONS)))
    backward = align_regions(PageView(_TIE_GT), PageView(_candidate(reversed_regions)))
    assert forward == backward


def test_scorecard_is_invariant_to_candidate_region_order():
    # The whole suite's verdict must not change when the candidate's regions list is
    # permuted (a semantics-preserving transformation).
    forward = run_checkers(_candidate(_CAND_REGIONS), _TIE_GT, build_default_suite())
    reversed_regions = list(reversed(copy.deepcopy(_CAND_REGIONS)))
    backward = run_checkers(_candidate(reversed_regions), _TIE_GT, build_default_suite())
    assert forward.to_dict() == backward.to_dict()


def test_exact_id_match_takes_priority_over_bbox():
    gt = PageView(_TIE_GT)
    # Candidate reuses GT ids → Pass-1 exact match, regardless of bbox.
    cand = PageView(_candidate([dict(r) for r in _TIE_GT["regions"]]))
    mapping = align_regions(gt, cand)
    assert mapping == {"gt-body": "gt-body", "gt-note": "gt-note"}
