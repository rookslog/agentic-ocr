"""Page-level answer keys: slice the whole-book GT-B alignment into per-PDF-page GT spans.

The GT-B aligner (:mod:`eval.gtb.align`) aligns *whole books*: the born-digital
EPUB token stream (trusted GT) against the scan-PDF text-layer token stream
(candidate). Scoring a vision model's transcription of a **single page image**
needs a smaller object: the span of GT tokens that page is supposed to contain.
That is what this module produces.

Method (pure logic; no I/O — extraction lives in :mod:`eval.gtb.extract`):

1. **Per-page candidate ranges** (:func:`page_token_ranges`). ``pdftotext``
   terminates each page with a form feed, so one whole-document pass split on
   that separator yields per-page texts. Because the form feed is neither a
   letter nor a decimal digit, ``eval.checkers._normalize`` already treats it as
   a token separator, so splitting there can neither merge nor split a token.
   The function *verifies* this rather than assuming it: it raises
   :class:`TokenizationMismatch` unless the concatenation of the per-page token
   lists is byte-identical to the whole-document token list the aligner sees.
   Token identity between the per-page and whole-book passes is the thing the
   whole design rests on, so it is checked at run time, not asserted in prose.

2. **One whole-book alignment** — the anchor chain from
   :func:`eval.gtb.align.unique_shared_anchors` (unique-shared 5-grams filtered
   to a strictly-monotone chain by LIS). This is *reused*, not reimplemented: the
   anchor semantics, ``ANCHOR_N`` and the LIS filter are the aligner's.

3. **Span slicing** (:func:`page_keys`). Each page's key is delimited by the
   anchors whose candidate span falls inside that page's candidate token range.
   The anchors pin the interior; the two edges (candidate tokens before the first
   in-page anchor and after the last) are carried across by the local 1:1 token
   offset at that anchor — without that, every key would be truncated by however
   much text precedes/follows the outermost anchor on the page. The extrapolated
   edges are then clamped so spans never leave the GT stream, never lose their
   own anchors, and are monotone non-decreasing across consecutive pages.

4. **Per-page statistics** — ``page_coverage`` is computed by running the
   *existing* aligner (:func:`eval.gtb.align.align_tokens`) on the local
   sub-problem (this page's GT span vs this page's candidate tokens), so the
   per-page number is the same statistic, computed by the same code, as the
   whole-book one: matched GT tokens in the span / span length.

**Reliability.** A page whose alignment support is weak — front matter, plates,
blank pages, running heads only — gets ``reliable=False`` and (when it has no
in-page anchor at all) no span, rather than a forced key. The floor is two named
constants, :data:`MIN_PAGE_ANCHORS` and :data:`MIN_PAGE_COVERAGE`, chosen from
the observed distribution across the owned books (see
``goal/evidence/gtb-aligner.md`` and the ``.local`` smoke).

The key text itself is *normalized tokens* joined by single spaces
(:func:`key_text`) — the same normalization a transcription must be put through
before scoring, so the key is directly comparable and carries no layout,
punctuation or casing claims it cannot support.
"""

from __future__ import annotations

import bisect
from dataclasses import dataclass

from eval.checkers._normalize import tokens
from eval.gtb.align import ANCHOR_N, MAX_GAP, Anchor, align_tokens, unique_shared_anchors

# ── Reliability floor (empirical; see the per-book distribution in the .local smoke) ───────
MIN_PAGE_ANCHORS = 3
"""Minimum number of whole-book anchors landing inside a page's candidate token
range for that page's key to be called reliable. Below this the span's endpoints
rest on one or two coincidences and its extrapolated edges are unconstrained."""

MIN_PAGE_COVERAGE = 0.60
"""Minimum local coverage (matched GT tokens in the span / span length) for a
page key to be called reliable. Deliberately the same value as
``align.ACCEPT_THRESHOLD``: a page key is a miniature GT-B pair, and a span the
page's own text cannot recover 60% of is not an answer key."""

MIN_PAGE_TOKENS = 5
"""Pages with fewer candidate tokens than this (blank pages, plates, pages whose
text layer holds only a folio number) are unreliable by construction: there is
not enough text to place them, and no anchor can even be contained in them."""


class TokenizationMismatch(RuntimeError):
    """Per-page tokenization does not reconstruct the whole-document token stream.

    Raised (never silently repaired) when the concatenation of per-page token
    lists differs from the whole-document token list. Any occurrence means the
    per-page path and the aligner disagree about token identity, which would make
    every candidate index — and therefore every key — meaningless.
    """


@dataclass(frozen=True)
class PageSpan:
    """One PDF page's half-open range ``[start, end)`` in the candidate token stream."""

    page_number: int  # 1-based PDF page number
    start: int
    end: int

    @property
    def n_tokens(self) -> int:
        return self.end - self.start


@dataclass(frozen=True)
class PageKey:
    """The answer key for one PDF page: a GT token span plus its support statistics."""

    page_number: int
    cand_start: int
    cand_end: int
    n_cand_tokens: int
    n_anchors: int
    gt_span: tuple[int, int] | None  # half-open [start, end) in GT token indices
    n_gt_span_tokens: int
    page_coverage: float
    reliable: bool
    reason: str  # "" when reliable; else why the key is not trustworthy


def page_token_ranges(page_texts: list[str], cand_tokens: list[str]) -> list[PageSpan]:
    """Candidate-token ranges for each PDF page, verified against the whole-book stream.

    ``page_texts`` is the output of :func:`eval.gtb.extract.split_pdf_pages` and
    ``cand_tokens`` the whole-document token list the aligner uses. Raises
    :class:`TokenizationMismatch` if the two do not reconstruct each other
    exactly — the token-identity check the design depends on.
    """
    spans: list[PageSpan] = []
    pos = 0
    for i, text in enumerate(page_texts, start=1):
        page_tokens = tokens(text)
        end = pos + len(page_tokens)
        if cand_tokens[pos:end] != page_tokens:
            raise TokenizationMismatch(
                f"page {i}: per-page tokens differ from the whole-document token "
                f"stream at candidate index {pos} "
                f"({len(page_tokens)} page tokens vs slice of {end - pos})"
            )
        spans.append(PageSpan(page_number=i, start=pos, end=end))
        pos = end
    if pos != len(cand_tokens):
        raise TokenizationMismatch(
            f"per-page tokens total {pos} but the whole document has "
            f"{len(cand_tokens)} tokens"
        )
    return spans


def _anchors_in_range(
    anchors: list[Anchor], cand_positions: list[int], start: int, end: int, n: int
) -> list[Anchor]:
    """Anchors whose full candidate span ``[cand_pos, cand_pos + n)`` lies in ``[start, end)``.

    ``cand_positions`` is the (sorted, by anchor monotonicity) list of anchor
    candidate positions, so the lookup is a pair of binary searches.
    """
    lo = bisect.bisect_left(cand_positions, start)
    hi = bisect.bisect_right(cand_positions, end - n)
    return anchors[lo:hi]


def page_keys(
    gt_tokens: list[str],
    cand_tokens: list[str],
    page_spans: list[PageSpan],
    *,
    n: int = ANCHOR_N,
    max_gap: int = MAX_GAP,
    min_anchors: int = MIN_PAGE_ANCHORS,
    min_coverage: float = MIN_PAGE_COVERAGE,
    anchors: list[Anchor] | None = None,
) -> list[PageKey]:
    """Derive one :class:`PageKey` per PDF page from a single whole-book alignment.

    ``anchors`` may be supplied to reuse a chain already computed for the same
    pair (the whole-book alignment is the expensive step); when omitted it is
    computed here with :func:`eval.gtb.align.unique_shared_anchors`.
    """
    if anchors is None:
        anchors = unique_shared_anchors(gt_tokens, cand_tokens, n)
    cand_positions = [a.cand_pos for a in anchors]
    total_gt = len(gt_tokens)

    # ── Pass 1: candidate span -> raw GT span, by anchors + local 1:1 edge offset ──────
    raw: list[tuple[PageSpan, list[Anchor], tuple[int, int] | None]] = []
    for span in page_spans:
        in_page = _anchors_in_range(anchors, cand_positions, span.start, span.end, n)
        if not in_page or total_gt == 0:
            raw.append((span, in_page, None))
            continue
        first, last = in_page[0], in_page[-1]
        # Carry the page's leading/trailing candidate tokens across at the local
        # offset of the outermost anchors (1:1 token correspondence at the edge).
        start = first.gt_pos - (first.cand_pos - span.start)
        end = (last.gt_pos + n) + (span.end - (last.cand_pos + n))
        # Never leave the GT stream, and never drop the anchors that define the span.
        start = max(0, min(start, first.gt_pos))
        end = min(total_gt, max(end, last.gt_pos + n))
        raw.append((span, in_page, (start, end)))

    # ── Pass 2: enforce monotone non-decreasing spans across consecutive pages ─────────
    keys: list[PageKey] = []
    prev_start = 0
    prev_end = 0
    for span, in_page, gt_span in raw:
        if gt_span is None:
            reason = (
                f"page has fewer than {MIN_PAGE_TOKENS} candidate tokens"
                if span.n_tokens < MIN_PAGE_TOKENS
                else "no alignment anchor lands on this page"
            )
            keys.append(
                PageKey(
                    page_number=span.page_number,
                    cand_start=span.start,
                    cand_end=span.end,
                    n_cand_tokens=span.n_tokens,
                    n_anchors=0,
                    gt_span=None,
                    n_gt_span_tokens=0,
                    page_coverage=0.0,
                    reliable=False,
                    reason=reason,
                )
            )
            continue

        start, end = gt_span
        # Monotone clamp: never start before the previous page started, but never
        # past this page's own first anchor either (which would orphan it).
        start = min(max(start, prev_start), in_page[0].gt_pos)
        end = max(end, prev_end, start + 1)
        end = min(end, total_gt)
        prev_start, prev_end = start, end

        local = align_tokens(
            gt_tokens[start:end],
            cand_tokens[span.start : span.end],
            n=n,
            max_gap=max_gap,
        )
        reasons: list[str] = []
        if span.n_tokens < MIN_PAGE_TOKENS:
            reasons.append(f"page has fewer than {MIN_PAGE_TOKENS} candidate tokens")
        if len(in_page) < min_anchors:
            reasons.append(f"only {len(in_page)} anchor(s) on this page (floor {min_anchors})")
        if local.coverage < min_coverage:
            reasons.append(
                f"local coverage {local.coverage:.4f} below floor {min_coverage:.2f}"
            )
        keys.append(
            PageKey(
                page_number=span.page_number,
                cand_start=span.start,
                cand_end=span.end,
                n_cand_tokens=span.n_tokens,
                n_anchors=len(in_page),
                gt_span=(start, end),
                n_gt_span_tokens=end - start,
                page_coverage=local.coverage,
                reliable=not reasons,
                reason="; ".join(reasons),
            )
        )
    return keys


def key_text(gt_tokens: list[str], key: PageKey) -> str:
    """The answer-key text for ``key``: its GT tokens, normalized, space-joined.

    Empty when the key has no span. The text is normalized tokens rather than raw
    GT prose because that is the form a transcription is scored in; emitting
    original-cased, punctuated prose would imply a layout/punctuation claim the
    alignment does not warrant.
    """
    if key.gt_span is None:
        return ""
    start, end = key.gt_span
    return " ".join(gt_tokens[start:end])
