"""Milestone 3: negative controls.

Each mutation must trip *exactly one* checker — its target — and leave the other
three passing. This is the discriminating property the goal packet requires: "each
checker demonstrably catches its target mutation and ignores the others." The test
runs the full default suite and asserts both halves (target fails AND the rest
pass) on the apparatus fixture (all four checkers exercised) and the minimal
scriptorium fixture (where applicable).
"""

from __future__ import annotations

import pytest

from eval.checkers import build_default_suite, run_checkers
from tests import _mutations as M

ALL_CHECKERS = {"text-fidelity", "reading-order", "footnote-anchor", "structure-typing"}


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


def test_mutators_are_deterministic(apparatus_candidate):
    # Same input → byte-identical mutated output (no RNG).
    import json

    a = json.dumps(M.corrupt_chars(apparatus_candidate, 0.05), sort_keys=True)
    b = json.dumps(M.corrupt_chars(apparatus_candidate, 0.05), sort_keys=True)
    assert a == b
