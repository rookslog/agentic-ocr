"""Tests for the reading-order checker (Kendall tau + LIS + coverage)."""

from __future__ import annotations

from eval.checkers.reading_order import ReadingOrderChecker, kendall_tau, lis_length
from tests import _mutations as M


def test_kendall_tau_helper():
    assert kendall_tau([0, 1, 2, 3]) == 1.0
    assert kendall_tau([3, 2, 1, 0]) == -1.0
    assert kendall_tau([0]) == 1.0  # vacuously ordered
    assert kendall_tau([]) == 1.0


def test_lis_length_helper():
    assert lis_length([0, 1, 2, 3]) == 4
    assert lis_length([0, 2, 1, 3]) == 3
    assert lis_length([3, 2, 1, 0]) == 1


def test_passes_when_order_preserved(apparatus_gt, apparatus_candidate):
    result = ReadingOrderChecker().check(apparatus_candidate, apparatus_gt)
    assert result.passed is True
    assert result.metrics["kendall_tau"] == 1.0
    assert result.metrics["coverage"] == 1.0


def test_fails_on_swap(apparatus_gt, apparatus_candidate):
    mutated = M.swap_blocks(apparatus_candidate, "body-1", "body-2")
    result = ReadingOrderChecker().check(mutated, apparatus_gt)
    assert result.passed is False
    assert result.metrics["kendall_tau"] < 1.0


def test_coverage_gate_fails_when_region_dropped(apparatus_gt, apparatus_candidate):
    # Drop body-2 from the candidate's reading order entirely: even if survivors
    # are correctly ordered, coverage < 1.0 fails the gate.
    import copy

    mutated = copy.deepcopy(apparatus_candidate)
    mutated["reading_order"] = [r for r in mutated["reading_order"] if r != "body-2"]
    mutated["regions"] = [r for r in mutated["regions"] if r["id"] != "body-2"]
    result = ReadingOrderChecker().check(mutated, apparatus_gt)
    assert result.passed is False
    assert result.metrics["coverage"] < 1.0
    assert result.metrics["missing"] == 1


def test_falls_back_to_reading_order_index_when_list_absent(apparatus_gt):
    # Candidate expresses order only via reading_order_index, not the list.
    import copy

    cand = copy.deepcopy(apparatus_gt)
    cand.pop("reading_order", None)
    result = ReadingOrderChecker().check(cand, apparatus_gt)
    assert result.passed is True


def test_deterministic(apparatus_gt, apparatus_candidate):
    a = ReadingOrderChecker().check(apparatus_candidate, apparatus_gt)
    b = ReadingOrderChecker().check(apparatus_candidate, apparatus_gt)
    assert a.to_dict() == b.to_dict()
