"""Tests for the text-fidelity checker (n-gram containment)."""

from __future__ import annotations

from eval.checkers.text_fidelity import TextFidelityChecker
from tests import _mutations as M


def test_passes_on_faithful_candidate(minimal_gt, minimal_candidate):
    result = TextFidelityChecker().check(minimal_candidate, minimal_gt)
    assert result.passed is True
    assert result.metrics["containment"] == 1.0


def test_markup_and_whitespace_invariant(apparatus_gt, apparatus_candidate):
    # Dropping the footnote *marker* must not lower containment: normalization
    # strips markers, so the token stream is unchanged.
    mutated = M.drop_anchor(apparatus_candidate)
    result = TextFidelityChecker().check(mutated, apparatus_gt)
    assert result.passed is True
    assert result.metrics["containment"] == 1.0


def test_character_corruption_fails(apparatus_gt, apparatus_candidate):
    mutated = M.corrupt_chars(apparatus_candidate, rate=0.05)
    result = TextFidelityChecker().check(mutated, apparatus_gt)
    assert result.passed is False
    assert result.metrics["containment"] < 0.95


def test_deterministic(apparatus_gt, apparatus_candidate):
    a = TextFidelityChecker().check(apparatus_candidate, apparatus_gt)
    b = TextFidelityChecker().check(apparatus_candidate, apparatus_gt)
    assert a.to_dict() == b.to_dict()


def test_n_backoff_on_short_page():
    # A page whose regions are too short for trigrams should back off to a lower n
    # rather than passing vacuously on zero n-grams.
    gt = {"regions": [{"id": "r1", "label": "text_block", "text": "alpha beta"}]}
    cand = {"regions": [{"id": "r1", "label": "text_block", "text": "alpha beta"}]}
    result = TextFidelityChecker(n=3).check(cand, gt)
    assert result.metrics["n"] == 2  # backed off from 3 to 2 (bigram)
    assert result.passed is True


def test_vacuous_pass_when_gt_has_no_text():
    result = TextFidelityChecker().check({"regions": []}, {"regions": []})
    assert result.passed is True
    assert result.metrics["gt_ngrams"] == 0


def test_recall_gate_is_blind_to_hallucination_but_precision_surfaces_it(
    apparatus_gt, apparatus_candidate
):
    # Review finding D-008: the hard gate is recall-only, so appended fabricated
    # text passes (recall 1.0). The precision metric must surface the excess so the
    # hallucination is reported, not hidden.
    import copy

    mutated = copy.deepcopy(apparatus_candidate)
    for region in mutated["regions"]:
        if region["id"] == "body-2":
            region["text"] += " Furthermore the philosopher then flew to the moon."
    result = TextFidelityChecker().check(mutated, apparatus_gt)
    assert result.passed is True  # recall gate is intentionally hallucination-blind
    assert result.metrics["containment"] == 1.0
    assert result.metrics["precision"] < 1.0  # excess surfaced
    assert result.metrics["excess_ngrams"] > 0


def test_metric_matches_verdict_at_boundary(apparatus_gt, apparatus_candidate):
    # Review finding D-008: the stored containment must be the exact float the gate
    # compares, never a rounded value that could contradict the verdict.
    result = TextFidelityChecker().check(apparatus_candidate, apparatus_gt)
    gated = result.metrics["containment"] >= result.metrics["min_containment"]
    assert gated == result.passed
