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
