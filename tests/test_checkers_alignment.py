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


def _candidate(regions: list, order: list[str] | None = None) -> dict:
    # `order` is explicit so a test can permute the *regions array* while holding the
    # reading order fixed. Deriving the order from the array (as this helper used to
    # do unconditionally) meant "permute the regions" also permuted the declared
    # reading order — not a semantics-preserving transformation at all, which is why
    # the invariance test below used to compare two *equally failing* scorecards and
    # so missed review finding H1 / D-237.
    return {
        "regions": regions,
        "reading_order": order if order is not None else [r["id"] for r in regions],
    }


def test_alignment_is_invariant_to_candidate_region_order_under_ties():
    forward = align_regions(PageView(_TIE_GT), PageView(_candidate(_CAND_REGIONS)))
    reversed_regions = list(reversed(copy.deepcopy(_CAND_REGIONS)))
    backward = align_regions(PageView(_TIE_GT), PageView(_candidate(reversed_regions)))
    assert forward == backward


def test_scorecard_is_invariant_to_candidate_region_order():
    # The whole suite's verdict must not change when the candidate's regions list is
    # permuted with its declared reading order held fixed — *that* is the
    # semantics-preserving transformation.
    order = ["cand-x", "cand-y"]
    forward = run_checkers(_candidate(_CAND_REGIONS, order), _TIE_GT, build_default_suite())
    reversed_regions = list(reversed(copy.deepcopy(_CAND_REGIONS)))
    backward = run_checkers(_candidate(reversed_regions, order), _TIE_GT, build_default_suite())
    assert forward.to_dict() == backward.to_dict()
    # ...and it is a *passing* scorecard, not two identical failures (review finding
    # H1 / D-237: the old assertion held vacuously because both sides scored 0).
    assert forward.exit_code() == 0, forward.render()


def test_exact_id_match_takes_priority_over_bbox():
    gt = PageView(_TIE_GT)
    # Candidate reuses GT ids → Pass-1 exact match, regardless of bbox.
    cand = PageView(_candidate([dict(r) for r in _TIE_GT["regions"]]))
    mapping = align_regions(gt, cand)
    assert mapping == {"gt-body": "gt-body", "gt-note": "gt-note"}


# ── Review finding M6 / D-237: greedy assignment leaves a matchable region out ──
# Boxes chosen so the viable IoUs are A-X≈.905, A-Y≈.700, B-X=.600 and B-Y≈.453
# (below the 0.5 floor, so not viable). Greedy by descending IoU takes A-X and
# strands B; the optimal assignment takes A-Y + B-X and matches both.
def _box(y0: float, y1: float) -> dict:
    return {"x0": 0.1, "y0": y0, "x1": 0.9, "y1": y1}


_GREEDY_GT = {
    "regions": [
        {"id": "gt-a", "label": "text_block", "bbox": _box(0.2, 0.7),
         "text": "and also because I wanted to see the festival held here",
         "reading_order_index": 0},
        {"id": "gt-b", "label": "note_area", "semantic_labels": ["note"],
         "bbox": _box(0.1, 0.6),
         "text": "the festival of Bendis a Thracian goddess identified with Artemis",
         "reading_order_index": 1},
    ],
    "reading_order": ["gt-a", "gt-b"],
}

# Candidate: same two regions, own ids, same types and texts — an honest candidate.
_GREEDY_CAND = {
    "regions": [
        {"id": "cand-y", "label": "text_block", "bbox": _box(0.288235, 0.788235),
         "text": "and also because I wanted to see the festival held here",
         "reading_order_index": 0},
        {"id": "cand-x", "label": "note_area", "semantic_labels": ["note"],
         "bbox": _box(0.225, 0.725),
         "text": "the festival of Bendis a Thracian goddess identified with Artemis",
         "reading_order_index": 1},
    ],
    "reading_order": ["cand-y", "cand-x"],
}


def test_assignment_matches_both_regions_where_greedy_stranded_one():
    mapping = align_regions(PageView(_GREEDY_GT), PageView(_GREEDY_CAND))
    # Greedy would produce {"gt-a": "cand-x", "gt-b": None}.
    assert mapping == {"gt-a": "cand-y", "gt-b": "cand-x"}


def test_optimal_assignment_saves_an_honest_candidate_from_false_failure():
    card = run_checkers(_GREEDY_CAND, _GREEDY_GT, build_default_suite())
    assert card.exit_code() == 0, card.render()


def test_optimal_assignment_is_invariant_to_candidate_region_order():
    forward = align_regions(PageView(_GREEDY_GT), PageView(_GREEDY_CAND))
    permuted = copy.deepcopy(_GREEDY_CAND)
    permuted["regions"] = list(reversed(permuted["regions"]))
    assert align_regions(PageView(_GREEDY_GT), PageView(permuted)) == forward
