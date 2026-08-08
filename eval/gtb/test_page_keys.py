"""Unit tests for the page-level answer-key slicer (synthetic tokens only; no corpus bytes).

Synthetic streams use distinct ``w<i>`` tokens so every 5-gram is unique in both
streams by construction — which is exactly the anchor condition, letting the
tests reason about expected spans exactly rather than statistically.
"""

from __future__ import annotations

import pytest

from eval.checkers._normalize import tokens
from eval.gtb.page_keys import (
    MIN_PAGE_ANCHORS,
    PageSpan,
    TokenizationMismatch,
    key_text,
    page_keys,
    page_token_ranges,
)


def words(start: int, stop: int) -> list[str]:
    """Distinct tokens ``w<start> .. w<stop-1>`` (every n-gram over them is unique)."""
    return [f"w{i}" for i in range(start, stop)]


def spans_of(page_lengths: list[int]) -> list[PageSpan]:
    """Contiguous :class:`PageSpan` list from consecutive page token counts."""
    out: list[PageSpan] = []
    pos = 0
    for i, n in enumerate(page_lengths, start=1):
        out.append(PageSpan(page_number=i, start=pos, end=pos + n))
        pos += n
    return out


# ── page_token_ranges: the token-identity check ───────────────────────────────────────────


def test_page_token_ranges_maps_pages_to_contiguous_candidate_ranges() -> None:
    page_texts = ["Alpha beta.", "Gamma delta epsilon!", "Zeta"]
    cand = tokens("\n".join(page_texts))
    spans = page_token_ranges(page_texts, cand)
    assert [(s.page_number, s.start, s.end) for s in spans] == [(1, 0, 2), (2, 2, 5), (3, 5, 6)]
    assert cand[spans[1].start : spans[1].end] == ["gamma", "delta", "epsilon"]


def test_page_token_ranges_keeps_interior_blank_pages() -> None:
    page_texts = ["alpha", "", "beta"]
    spans = page_token_ranges(page_texts, tokens("alpha beta"))
    assert [s.n_tokens for s in spans] == [1, 0, 1]
    assert spans[2].page_number == 3  # page numbering is not compacted


def test_page_token_ranges_raises_on_tokenization_mismatch() -> None:
    # A whole-document stream that the per-page texts cannot reconstruct.
    with pytest.raises(TokenizationMismatch):
        page_token_ranges(["alpha beta", "gamma"], tokens("alpha beta delta"))


def test_page_token_ranges_raises_when_document_has_extra_trailing_tokens() -> None:
    with pytest.raises(TokenizationMismatch):
        page_token_ranges(["alpha beta"], tokens("alpha beta gamma"))


# ── span slicing ──────────────────────────────────────────────────────────────────────────


def test_mid_book_page_slices_its_exact_gt_span() -> None:
    gt = words(0, 300)
    cand = list(gt)
    keys = page_keys(gt, cand, spans_of([100, 100, 100]))
    assert [k.gt_span for k in keys] == [(0, 100), (100, 200), (200, 300)]
    assert all(k.reliable for k in keys)
    assert all(k.page_coverage == pytest.approx(1.0) for k in keys)


def test_span_tracks_a_candidate_side_offset() -> None:
    """Extra scan-only text (running heads) shifts candidate indices, not GT spans."""
    gt = words(0, 200)
    cand = ["junk0", "junk1", "junk2", *gt]  # 3 scan-only tokens before page 1
    keys = page_keys(gt, cand, spans_of([103, 100]))
    assert keys[0].gt_span == (0, 100)
    assert keys[1].gt_span == (100, 200)


def test_page_boundary_tokens_are_included_at_both_edges() -> None:
    """The first and last candidate token of a page must appear in its key.

    This is the off-by-one guard: the outermost anchors sit *inside* the page, so
    the leading/trailing tokens are only present if the edges are extrapolated.
    """
    gt = words(0, 300)
    keys = page_keys(gt, list(gt), spans_of([100, 100, 100]))
    mid = keys[1]
    assert mid.gt_span is not None
    text = key_text(gt, mid).split()
    assert text[0] == "w100"  # first token of page 2
    assert text[-1] == "w199"  # last token of page 2
    assert "w99" not in text and "w200" not in text


def test_last_page_span_ends_at_the_end_of_gt() -> None:
    gt = words(0, 250)
    keys = page_keys(gt, list(gt), spans_of([100, 100, 50]))
    assert keys[-1].gt_span == (200, 250)
    assert key_text(gt, keys[-1]).split()[-1] == "w249"


def test_span_never_leaves_the_gt_stream() -> None:
    """A page longer than the GT tail must clamp instead of running past the end."""
    gt = words(0, 60)
    cand = [*gt, *(f"scan{i}" for i in range(40))]  # 40 scan-only tokens at the end
    keys = page_keys(gt, cand, spans_of([50, 50]))
    for k in keys:
        assert k.gt_span is not None
        assert 0 <= k.gt_span[0] <= k.gt_span[1] <= len(gt)


# ── weak / anchorless pages ───────────────────────────────────────────────────────────────


def test_anchorless_page_gets_no_key_and_is_unreliable() -> None:
    gt = words(0, 200)
    plate = [f"plate{i}" for i in range(30)]  # image page: nothing shared with GT
    cand = [*gt[:100], *plate, *gt[100:]]
    keys = page_keys(gt, cand, spans_of([100, 30, 100]))
    assert keys[1].gt_span is None
    assert keys[1].reliable is False
    assert keys[1].n_anchors == 0
    assert "no alignment anchor" in keys[1].reason
    assert key_text(gt, keys[1]) == ""
    assert keys[0].reliable and keys[2].reliable  # neighbours unaffected


def test_empty_page_is_unreliable_with_no_span() -> None:
    gt = words(0, 200)
    keys = page_keys(gt, list(gt), spans_of([100, 0, 100]))
    blank = keys[1]
    assert blank.gt_span is None
    assert blank.reliable is False
    assert blank.n_cand_tokens == 0
    assert "fewer than" in blank.reason


def test_thinly_anchored_page_is_unreliable_but_keeps_its_span() -> None:
    """One anchor is a span, not a warrant: the key is emitted, flagged unreliable."""
    gt = words(0, 200)
    noise = [f"noise{i}" for i in range(20)]
    # A 5-token page: exactly one 5-gram, hence exactly one anchor.
    cand = [*noise, *gt[100:105], *noise]
    keys = page_keys(gt, cand, spans_of([20, 5, 20]))
    thin = keys[1]
    assert thin.n_anchors == 1 < MIN_PAGE_ANCHORS
    assert thin.gt_span == (100, 105)
    assert thin.reliable is False
    assert "anchor(s) on this page" in thin.reason


def test_min_anchors_floor_is_a_parameter_and_admits_the_thin_page_when_relaxed() -> None:
    gt = words(0, 200)
    noise = [f"noise{i}" for i in range(20)]
    cand = [*noise, *gt[100:105], *noise]
    relaxed = page_keys(gt, cand, spans_of([20, 5, 20]), min_anchors=1)
    assert relaxed[1].reliable is True


def test_low_local_coverage_page_is_unreliable() -> None:
    """A page whose candidate text recovers little of its own span is flagged."""
    gt = words(0, 200)
    # Page 2's candidate side keeps only its first 5 GT tokens, then diverges; the
    # span is extrapolated over ~50 GT tokens, so local coverage is far below 0.60.
    cand = [*gt[:50], *gt[50:55], *(f"x{i}" for i in range(45)), *gt[100:]]
    keys = page_keys(gt, cand, spans_of([50, 50, 100]))
    assert keys[1].page_coverage < 0.60
    assert keys[1].reliable is False
    assert "local coverage" in keys[1].reason


def test_empty_gt_yields_no_spans() -> None:
    keys = page_keys([], words(0, 50), spans_of([25, 25]))
    assert all(k.gt_span is None and not k.reliable for k in keys)


# ── monotonicity & determinism ────────────────────────────────────────────────────────────


def test_spans_are_monotone_across_consecutive_pages() -> None:
    gt = words(0, 400)
    plate = [f"plate{i}" for i in range(15)]
    cand = [*gt[:100], *plate, *gt[100:250], *plate, *gt[250:]]
    keys = page_keys(gt, cand, spans_of([100, 15, 75, 75, 15, 150]))
    spans = [k.gt_span for k in keys if k.gt_span is not None]
    assert len(spans) == 4
    starts = [s[0] for s in spans]
    ends = [s[1] for s in spans]
    assert starts == sorted(starts)
    assert ends == sorted(ends)


def test_spans_are_monotone_even_when_pages_overlap_in_content() -> None:
    """Repeated candidate material must not make a later page's span move backwards."""
    gt = words(0, 300)
    cand = [*gt[:100], *gt[95:200], *gt[200:]]  # page 2 re-shows the tail of page 1
    keys = page_keys(gt, cand, spans_of([100, 105, 100]))
    spans = [k.gt_span for k in keys if k.gt_span is not None]
    for earlier, later in zip(spans, spans[1:], strict=False):
        assert later[0] >= earlier[0]
        assert later[1] >= earlier[1]


def test_page_keys_are_deterministic() -> None:
    gt = words(0, 300)
    plate = [f"plate{i}" for i in range(11)]
    cand = [*gt[:120], *plate, *gt[120:]]
    lengths = [60, 60, 11, 90, 90]
    first = page_keys(gt, cand, spans_of(lengths))
    second = page_keys(gt, cand, spans_of(lengths))
    assert first == second
    assert [key_text(gt, k) for k in first] == [key_text(gt, k) for k in second]
