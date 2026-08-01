"""Milestone 3: negative controls.

Each mutation must trip *exactly one* checker — its target — and leave the other
passing. This is the discriminating property the goal packet requires: "each
checker demonstrably catches its target mutation and ignores the others." The test
runs the full default suite and asserts both halves (target fails AND the rest
pass) on the apparatus fixture (every checker exercised) and the minimal
scriptorium fixture (where applicable).
"""

from __future__ import annotations

import pytest

from eval.checkers import build_default_suite, run_checkers
from eval.checkers.text_fidelity import TextFidelityChecker
from tests import _mutations as M
from tests.conftest import FIXTURES_DIR

ALL_CHECKERS = {
    "structural-contract",
    "text-fidelity",
    "reading-order",
    "footnote-anchor",
    "structure-typing",
}


def _verdicts(candidate, gt) -> dict[str, bool]:
    card = run_checkers(candidate, gt, build_default_suite())
    return {r.id: r.passed for r in card.results}


# (mutation-name, builder(gt, candidate) -> mutated_candidate, target-checker)
APPARATUS_CASES = [
    ("drop_anchor", lambda gt, c: M.drop_anchor(c), "footnote-anchor"),
    ("swap_blocks", lambda gt, c: M.swap_blocks(c, "body-1", "body-2"), "reading-order"),
    ("corrupt_chars", lambda gt, c: M.corrupt_chars(c, 0.05), "text-fidelity"),
    ("mislabel", lambda gt, c: M.mislabel(c, "head-1", "text_block"), "structure-typing"),
]


@pytest.mark.parametrize("name,mutate,target", APPARATUS_CASES, ids=[c[0] for c in APPARATUS_CASES])
def test_apparatus_negative_control_isolation(
    name, mutate, target, apparatus_gt, apparatus_candidate
):
    mutated = mutate(apparatus_gt, apparatus_candidate)
    verdicts = _verdicts(mutated, apparatus_gt)
    # Target checker catches its mutation.
    assert verdicts[target] is False, f"{name}: expected {target} to FAIL"
    # Every other checker ignores it.
    for checker_id in ALL_CHECKERS - {target}:
        assert verdicts[checker_id] is True, f"{name}: {checker_id} should be unaffected"


def test_apparatus_negative_controls_force_nonzero_exit(apparatus_gt, apparatus_candidate):
    for _name, mutate, _target in APPARATUS_CASES:
        mutated = mutate(apparatus_gt, apparatus_candidate)
        card = run_checkers(mutated, apparatus_gt, build_default_suite())
        assert card.exit_code() == 1


MINIMAL_CASES = [
    ("swap_blocks", lambda gt, c: M.swap_blocks(c, "body-1", "note-1"), "reading-order"),
    ("corrupt_chars", lambda gt, c: M.corrupt_chars(c, 0.05), "text-fidelity"),
    ("mislabel", lambda gt, c: M.mislabel(c, "body-1", "section_header"), "structure-typing"),
]


@pytest.mark.parametrize("name,mutate,target", MINIMAL_CASES, ids=[c[0] for c in MINIMAL_CASES])
def test_minimal_negative_control_isolation(name, mutate, target, minimal_gt, minimal_candidate):
    mutated = mutate(minimal_gt, minimal_candidate)
    verdicts = _verdicts(mutated, minimal_gt)
    assert verdicts[target] is False, f"{name}: expected {target} to FAIL"
    for checker_id in ALL_CHECKERS - {target}:
        assert verdicts[checker_id] is True, f"{name}: {checker_id} should be unaffected"


def test_clean_fixtures_produce_zero_crashes(
    apparatus_gt, apparatus_candidate, minimal_gt, minimal_candidate
):
    # Review finding D-008: a checker crash on a clean fixture must surface as a CI
    # failure (a checker bug), not as ordinary reward. Assert the default suite runs
    # crash-free on both faithful candidates.
    for cand, gt in [(apparatus_candidate, apparatus_gt), (minimal_candidate, minimal_gt)]:
        card = run_checkers(cand, gt, build_default_suite())
        assert card.crashed == []
        assert card.exit_code() == 0


# ── Review finding M7 / D-237: drop_anchor must not corrupt prose ─────────────
# `text.replace(marker, "")` removed *every* occurrence of the marker character.
# For an allowed alphabetic marker such as "a" that destroyed the region's prose,
# so the "footnote-anchor only" control also tripped text-fidelity.

_ALPHA_MARKER_PAGE = {
    "regions": [
        {
            "id": "body-1",
            "label": "text_block",
            "bbox": {"x0": 0.12, "y0": 0.15, "x1": 0.88, "y1": 0.45},
            "text": (
                "And also because I wanted to see in what manner they would "
                "celebrate the annual festival at the Piraeus. a"
            ),
            "text_anchors": ["a"],
            "reading_order_index": 0,
        },
        {
            "id": "note-1",
            "label": "note_area",
            "bbox": {"x0": 0.12, "y0": 0.82, "x1": 0.88, "y1": 0.90},
            "text": "a The festival of Bendis, a Thracian goddess.",
            "semantic_labels": ["note"],
            "reading_order_index": 1,
        },
    ],
    "reading_order": ["body-1", "note-1"],
}


def test_drop_anchor_removes_only_standalone_alphabetic_markers():
    mutated = M.drop_anchor(_ALPHA_MARKER_PAGE)
    body = next(r for r in mutated["regions"] if r["id"] == "body-1")
    # The prose survives verbatim; only the trailing standalone marker is gone.
    assert body["text"] == (
        "And also because I wanted to see in what manner they would "
        "celebrate the annual festival at the Piraeus. "
    )
    assert "annual" in body["text"]  # would be "nnul" under str.replace


def test_drop_anchor_on_alphabetic_marker_leaves_the_non_text_checkers_alone():
    # LIMIT, stated rather than papered over: an *alphabetic* marker is, after
    # normalization, an ordinary content token — "a" is indistinguishable from a
    # word, where "¹" is stripped as markup. So removing it necessarily costs
    # text-fidelity one token, and the control's "exactly one checker" claim holds
    # only for non-alphanumeric markers (which is what every committed fixture
    # uses). What the M7 fix buys is that the cost is now *one token* instead of
    # the region's whole prose. Isolation from the structural checkers is exact.
    mutated = M.drop_anchor(_ALPHA_MARKER_PAGE)
    verdicts = _verdicts(mutated, _ALPHA_MARKER_PAGE)
    assert verdicts["footnote-anchor"] is False
    for checker_id in ALL_CHECKERS - {"footnote-anchor", "text-fidelity"}:
        assert verdicts[checker_id] is True, f"{checker_id} should be unaffected"

    # The residual text cost is bounded by the single removed token: one of the
    # region's trigrams. Under the old str.replace the region lost every "a" and
    # retention collapsed far below this.
    result = TextFidelityChecker().check(mutated, _ALPHA_MARKER_PAGE)
    assert result.metrics["worst_region_retention"] > 0.9


def _declared_markers(page) -> list[str]:
    """Every marker declared in ``text_anchors`` anywhere on the page."""
    return [m for region in M._all_regions(page) for m in (region.get("text_anchors") or [])]


def _all_committed_fixtures() -> list[str]:
    """Every committed candidate fixture — discovered, not hand-listed."""
    return sorted(p.name for p in FIXTURES_DIR.glob("*.candidate.json"))


def test_the_fixture_guard_sees_every_committed_fixture():
    # The guard below is only as good as its inventory. If a fixture pair is added
    # and this list is not what the parametrize walks, a new fixture could escape the
    # isolation claim silently — which is how the alphabetic-marker case was missed.
    assert _all_committed_fixtures() == [
        "apparatus_page.candidate.json",
        "minimal_page.candidate.json",
    ]


@pytest.mark.parametrize("candidate_name", _all_committed_fixtures())
def test_drop_anchor_text_fidelity_effect_matches_the_marker_kind(candidate_name):
    """The control's isolation claim, asserted over *discovered* fixtures.

    The claim is conditional on the marker kind, and the condition is computed from
    the fixture rather than assumed: a marker normalization treats as markup (``¹``,
    ``*``, ``†``) leaves the token stream identical, so text-fidelity must be exactly
    untouched; an alphanumeric marker is a content token, so the most that can be
    claimed is a bounded residual. A future fixture with an alphabetic marker
    therefore lands in the second branch instead of silently failing the first.
    """
    import json

    candidate = json.loads((FIXTURES_DIR / candidate_name).read_text(encoding="utf-8"))
    gt = json.loads(
        (FIXTURES_DIR / candidate_name.replace(".candidate.", ".gt.")).read_text(
            encoding="utf-8"
        )
    )
    markers = _declared_markers(gt)
    result = TextFidelityChecker().check(M.drop_anchor(candidate), gt)

    if any(ch.isalnum() for marker in markers for ch in marker):
        assert result.metrics["worst_region_retention"] > 0.9, result.detail
    else:
        assert result.passed is True, result.detail
        assert result.metrics["containment"] == 1.0
        assert result.metrics["region_defects"] == 0
    assert result.metrics["region_defects"] == 0


def test_mutators_are_deterministic(apparatus_candidate):
    # Same input → byte-identical mutated output (no RNG).
    import json

    a = json.dumps(M.corrupt_chars(apparatus_candidate, 0.05), sort_keys=True)
    b = json.dumps(M.corrupt_chars(apparatus_candidate, 0.05), sort_keys=True)
    assert a == b
