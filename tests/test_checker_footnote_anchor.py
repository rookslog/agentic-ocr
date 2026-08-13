"""Tests for the footnote-anchor integrity checker."""

from __future__ import annotations

import copy

from eval.checkers.footnote_anchor import FootnoteAnchorChecker
from tests import _mutations as M


def test_passes_on_apparatus_with_anchor(apparatus_gt, apparatus_candidate):
    result = FootnoteAnchorChecker().check(apparatus_candidate, apparatus_gt)
    assert result.passed is True
    assert result.metrics["notes_matched"] == 1
    assert result.metrics["spans_preserved"] == 1


def test_minimal_note_present_no_anchors_is_vacuous_pass(minimal_gt, minimal_candidate):
    # The minimal fixture declares a note but no notable span: the checker
    # verifies note presence and treats span preservation as vacuously satisfied.
    result = FootnoteAnchorChecker().check(minimal_candidate, minimal_gt)
    assert result.passed is True
    assert result.metrics["gt_spans"] == 0
    assert result.metrics["notes_matched"] == 1


def test_dropped_anchor_fails(apparatus_gt, apparatus_candidate):
    mutated = M.drop_anchor(apparatus_candidate)
    result = FootnoteAnchorChecker().check(mutated, apparatus_gt)
    assert result.passed is False
    assert result.metrics["span_defects"] == 1


def test_duplicated_anchor_fails(apparatus_gt, apparatus_candidate):
    mutated = copy.deepcopy(apparatus_candidate)
    for region in mutated["regions"]:
        if region["id"] == "body-1":
            region["text"] = region["text"] + " stray duplicate marker ¹"
    result = FootnoteAnchorChecker().check(mutated, apparatus_gt)
    assert result.passed is False
    assert result.metrics["span_defects"] == 1


def test_span_declared_but_absent_from_gt_text_is_skipped_not_failed(apparatus_gt):
    # Review finding D-008 Case A: GT declares text_anchors=["1"] but its own region
    # text uses the superscript "¹". A faithful candidate that reproduces "¹" must
    # NOT be failed by fabricating an expected count of 1 for the literal "1".
    gt = copy.deepcopy(apparatus_gt)
    for region in gt["regions"]:
        if region["id"] == "body-1":
            region["text_anchors"] = ["1"]  # declared marker, but text has "¹"
    faithful = copy.deepcopy(gt)  # candidate reproduces GT exactly (incl. "¹")
    result = FootnoteAnchorChecker().check(faithful, gt)
    assert result.passed is True
    assert result.metrics["spans_skipped"] == 1
    assert result.metrics["span_defects"] == 0


def test_missing_note_region_fails(apparatus_gt, apparatus_candidate):
    mutated = copy.deepcopy(apparatus_candidate)
    mutated["regions"] = [r for r in mutated["regions"] if r["id"] != "note-1"]
    result = FootnoteAnchorChecker().check(mutated, apparatus_gt)
    assert result.passed is False
    assert result.metrics["missing_notes"] == 1


def test_note_recovered_but_mistyped_fails(apparatus_gt, apparatus_candidate):
    # The note region survives spatially but is typed as a plain text block (its
    # note-ness lost): note presence (b) fails because the counterpart isn't a note.
    mutated = copy.deepcopy(apparatus_candidate)
    for region in mutated["regions"]:
        if region["id"] == "note-1":
            region["label"] = "text_block"
            region["semantic_labels"] = []
    result = FootnoteAnchorChecker().check(mutated, apparatus_gt)
    assert result.passed is False
    assert result.metrics["mistyped_notes"] == 1


def test_deterministic(apparatus_gt, apparatus_candidate):
    a = FootnoteAnchorChecker().check(apparatus_candidate, apparatus_gt)
    b = FootnoteAnchorChecker().check(apparatus_candidate, apparatus_gt)
    assert a.to_dict() == b.to_dict()
