"""Co-located unit tests for the GT-B aligner (eval.gtb.align).

Pure synthetic token streams — no corpus bytes, no network, deterministic. The
real-corpus smoke lives in ``.local/eval/gtb_smoke.py`` (reads gitignored
corpus/). Run:  uv run pytest eval/gtb/test_align.py
"""

from __future__ import annotations

import math
from itertools import product

import pytest

from eval.gtb.align import (
    ACCEPT_THRESHOLD,
    ANCHOR_N,
    MAX_GAP,
    _lcs_length,
    _lis_indices,
    _segment_lcs_match,
    _unique_positions,
    align,
    align_tokens,
    unique_shared_anchors,
)


def _words(*ws: str) -> list[str]:
    return list(ws)


# ── helpers ───────────────────────────────────────────────────────────────────────────────
def test_unique_positions_keeps_only_singletons() -> None:
    grams: list[tuple[str, ...]] = [("a",), ("b",), ("a",), ("c",)]
    up = _unique_positions(grams)
    assert up == {("b",): 1, ("c",): 3}  # ("a",) appears twice -> dropped


def test_lis_indices_strictly_increasing() -> None:
    # values 10 9 2 5 3 7 101 18 -> an LIS of length 4 (e.g. 2 3 7 18 / 2 5 7 18)
    idx = _lis_indices([10, 9, 2, 5, 3, 7, 101, 18])
    vals = [[10, 9, 2, 5, 3, 7, 101, 18][i] for i in idx]
    assert vals == sorted(vals)
    assert all(vals[i] < vals[i + 1] for i in range(len(vals) - 1))
    assert len(vals) == 4


def test_lis_indices_empty() -> None:
    assert _lis_indices([]) == []


def test_lcs_length_basic() -> None:
    assert _lcs_length(_words("a", "b", "c", "d"), _words("a", "x", "c", "d")) == 3
    assert _lcs_length(_words("a", "b"), _words("c", "d")) == 0
    assert _lcs_length([], _words("a")) == 0


def test_segment_lcs_respects_max_gap() -> None:
    big = _words(*[str(i) for i in range(10)])
    assert _segment_lcs_match(big, big, max_gap=5) == 0  # over the cap -> unalignable
    assert _segment_lcs_match(big, big, max_gap=100) == len(big)


# ── anchors ────────────────────────────────────────────────────────────────────────────────
def test_unique_shared_anchors_monotone() -> None:
    # Identical streams: every 3-gram that is unique is an anchor, in order.
    gt = _words("the", "cat", "sat", "on", "a", "mat", "near", "the", "old", "door")
    cand = list(gt)
    anchors = unique_shared_anchors(gt, cand, n=3)
    assert anchors, "expected anchors on identical streams"
    # strictly increasing in both coordinates
    for prev, nxt in zip(anchors, anchors[1:], strict=False):
        assert nxt.gt_pos > prev.gt_pos
        assert nxt.cand_pos > prev.cand_pos


def test_no_anchors_when_disjoint() -> None:
    gt = _words("alpha", "beta", "gamma", "delta", "epsilon")
    cand = _words("one", "two", "three", "four", "five")
    assert unique_shared_anchors(gt, cand, n=3) == []


def test_crossed_unique_blocks_keep_only_a_monotone_anchor_chain() -> None:
    first = _words("a0", "a1", "a2", "a3", "a4")
    second = _words("b0", "b1", "b2", "b3", "b4")
    anchors = unique_shared_anchors([*first, *second], [*second, *first], n=5)
    assert len(anchors) == 1
    assert anchors[0].ngram in {tuple(first), tuple(second)}


def test_ngram_repeated_on_either_side_is_not_an_anchor() -> None:
    shared = _words("a", "b", "c", "d", "e")
    assert unique_shared_anchors(shared, [*shared, "x", *shared], n=5) == []
    assert unique_shared_anchors([*shared, "x", *shared], shared, n=5) == []


# ── coverage + verdict ────────────────────────────────────────────────────────────────────
def test_identical_streams_full_coverage_accept() -> None:
    toks = _words(*[f"w{i}" for i in range(50)])
    r = align_tokens(toks, list(toks), n=5)
    assert r.coverage == 1.0
    assert r.accepted is True
    assert r.matched_gt_tokens == r.gt_tokens


def test_disjoint_streams_zero_coverage_reject() -> None:
    gt = _words(*[f"a{i}" for i in range(40)])
    cand = _words(*[f"b{i}" for i in range(40)])
    r = align_tokens(gt, cand, n=5)
    assert r.coverage == 0.0
    assert r.accepted is False


def test_coverage_never_double_counts() -> None:
    # Dense DISTINCT stream: the raw 5-gram candidates overlap heavily. The
    # canonical chain must retain only candidate-disjoint anchors, so coverage is
    # an injective token match rather than a value clamped after over-crediting.
    toks = _words(*[f"w{i}" for i in range(210)])
    r = align_tokens(toks, list(toks), n=5)
    assert r.n_anchors == 42
    assert r.coverage == 1.0
    assert r.matched_gt_tokens == r.gt_tokens
    assert r.detail["anchor_token_fraction"] == 1.0
    assert r.detail["gap_token_fraction"] == 0.0


def test_overlapping_candidate_anchors_cannot_reuse_tokens() -> None:
    """Eleven overlapping candidate windows cannot explain eleven disjoint GT runs."""
    cand = _words(*[f"w{i}" for i in range(15)])
    gt: list[str] = []
    for start in range(11):
        gt.extend(cand[start : start + 5])
        if start < 10:
            gt.append(f"gap{start}")

    r = align_tokens(gt, cand)

    assert r.matched_gt_tokens <= _lcs_length(gt, cand) == 15
    assert r.accepted is False


def test_small_alignments_never_exceed_global_lcs() -> None:
    streams = [list(items) for size in range(5) for items in product(("a", "b"), repeat=size)]
    for gt in streams:
        for candidate in streams:
            result = align_tokens(gt, candidate, n=2, max_gap=10)
            assert result.matched_gt_tokens <= _lcs_length(gt, candidate)


def test_anchorless_match_is_not_an_accepted_anchor_alignment() -> None:
    r = align_tokens(["title"], ["title"])
    assert r.coverage == 1.0
    assert r.n_anchors == 0
    assert r.accepted is False
    assert r.detail["reason_no_anchors"] == 1.0


def test_partial_match_intermediate_coverage() -> None:
    # First half identical, second half disjoint -> coverage near 0.5, below default.
    shared = _words(*[f"s{i}" for i in range(40)])
    gt = shared + _words(*[f"g{i}" for i in range(40)])
    cand = list(shared) + _words(*[f"c{i}" for i in range(40)])
    r = align_tokens(gt, cand, n=5)
    assert 0.3 < r.coverage < 0.7
    assert r.accepted is (r.coverage >= ACCEPT_THRESHOLD)


def test_sparse_anchors_large_gap_not_credited() -> None:
    # Regression: two mostly-disjoint streams that happen to share a couple of
    # unique anchors far apart must NOT have the whole inter-anchor gap counted as
    # covered. Only the shared anchor n-grams (and any LCS within the gap) count.
    # Build GT and CAND that share two distinct 5-grams but are otherwise disjoint,
    # with a gap larger than MAX_GAP so the gap LCS is skipped entirely.
    shared_a = _words("aa", "bb", "cc", "dd", "ee")
    shared_b = _words("vv", "ww", "xx", "yy", "zz")
    filler_gt = _words(*[f"g{i}" for i in range(5000)])
    filler_cand = _words(*[f"c{i}" for i in range(5000)])
    gt = shared_a + filler_gt + shared_b
    cand = shared_a + filler_cand + shared_b
    r = align_tokens(gt, cand, n=5)
    # Only the two 5-gram anchors (10 tokens) are genuinely shared; the 5000-token
    # gap exceeds MAX_GAP and is disjoint, so coverage must be tiny, not ~1.0.
    assert r.matched_gt_tokens <= 20
    assert r.coverage < 0.05
    assert r.accepted is False


def test_empty_gt_rejects() -> None:
    r = align_tokens([], _words("a", "b", "c"), n=5)
    assert r.coverage == 0.0
    assert r.accepted is False
    assert r.gt_tokens == 0


def test_threshold_boundary_is_inclusive() -> None:
    toks = _words(*[f"w{i}" for i in range(10)])
    r = align_tokens(toks, list(toks), n=5, threshold=1.0)
    assert r.coverage == 1.0
    assert r.accepted is True  # coverage == threshold -> accept (inclusive)


def test_calibrated_defaults_and_default_threshold_boundary() -> None:
    assert ANCHOR_N == 5
    assert MAX_GAP == 4000
    assert ACCEPT_THRESHOLD == 0.60

    gt = _words(*[f"w{i}" for i in range(10)])
    at_boundary = align_tokens(gt, gt[:6])
    below_boundary = align_tokens(gt, gt[:5])
    assert at_boundary.coverage == 0.60
    assert at_boundary.accepted is True
    assert below_boundary.coverage == 0.50
    assert below_boundary.accepted is False


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"n": 0}, "n must be"),
        ({"max_gap": -1}, "max_gap must be"),
        ({"threshold": -0.01}, "threshold must be"),
        ({"threshold": 1.01}, "threshold must be"),
        ({"threshold": math.nan}, "threshold must be"),
    ],
)
def test_invalid_alignment_parameters_are_rejected(kwargs: dict[str, float], match: str) -> None:
    with pytest.raises(ValueError, match=match):
        align_tokens(["a"], ["a"], **kwargs)  # type: ignore[arg-type]


def test_candidate_side_diagnostics_expose_excess_material() -> None:
    gt = _words(*[f"g{i}" for i in range(100)])
    candidate = [*gt, *[f"junk{i}" for i in range(1000)]]
    r = align_tokens(gt, candidate)
    assert r.coverage == 1.0
    assert r.detail["candidate_coverage"] == pytest.approx(100 / 1100)
    assert r.detail["candidate_to_gt_length_ratio"] == 11.0


def test_align_text_entrypoint_normalizes() -> None:
    # Punctuation/case differences are normalized away by eval.checkers._normalize.
    gt = "The Cat Sat On A Mat, near the old door, beside the river bank today."
    cand = "the cat sat on a mat near the OLD door beside the river bank today"
    r = align(gt, cand, n=3)
    assert r.coverage > 0.8
    assert r.accepted is True


def test_determinism_repeated_runs() -> None:
    toks = _words(*[f"w{i % 13}" for i in range(200)])
    cand = _words(*[f"w{i % 13}" for i in range(200)])
    r1 = align_tokens(toks, cand, n=5)
    r2 = align_tokens(toks, cand, n=5)
    assert r1 == r2
