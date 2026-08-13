"""GT-B aligner (PLAN §5 GT-B; PLAN.md:139).

Anchor-based scan-PDF <-> born-digital-EPUB text aligner with a *mechanical*
alignment-coverage statistic. The original packet intended that statistic to
decide pair accept/reject with no human judgment; W2 review showed the GT-recall
direction alone cannot certify edition identity. The aligner generalizes the smoke
(``.local/eval/og_smoke.py``): instead of a single document-level n-gram
containment number, it (1) extracts unique-shared, monotone, span-disjoint n-grams
as alignment anchors, (2) DP-fills the token streams between consecutive anchors,
and (3) reports a GT-recall statistic plus a provisional threshold flag. The flag
separates recorded candidates from unrelated controls; it is not yet sufficient
evidence of edition identity (see ``goal/evidence/gtb-aligner.md``).

Public surface:

- :func:`eval.gtb.extract.extract_epub_text`, :func:`extract_pdf_text` — text
  extraction (EPUB spine / poppler ``pdftotext``).
- :func:`eval.gtb.align.align` — the aligner; returns an :class:`AlignmentResult`.
- :data:`eval.gtb.align.ACCEPT_THRESHOLD` — the recorded recall threshold.
- :func:`eval.gtb.page_keys.page_keys` — per-PDF-page answer keys (GT token spans)
  sliced out of one whole-book alignment.
"""

from __future__ import annotations

from eval.gtb.align import (
    ACCEPT_THRESHOLD,
    ANCHOR_N,
    AlignmentResult,
    Anchor,
    align,
    align_tokens,
    unique_shared_anchors,
)
from eval.gtb.extract import (
    extract_epub_text,
    extract_pdf_page_texts,
    extract_pdf_text,
    split_pdf_pages,
)
from eval.gtb.page_keys import (
    MIN_PAGE_ANCHORS,
    MIN_PAGE_COVERAGE,
    PageKey,
    PageSpan,
    TokenizationMismatch,
    key_text,
    page_keys,
    page_token_ranges,
)

__all__ = [
    "ACCEPT_THRESHOLD",
    "ANCHOR_N",
    "MIN_PAGE_ANCHORS",
    "MIN_PAGE_COVERAGE",
    "Anchor",
    "AlignmentResult",
    "PageKey",
    "PageSpan",
    "TokenizationMismatch",
    "align",
    "align_tokens",
    "extract_epub_text",
    "extract_pdf_page_texts",
    "extract_pdf_text",
    "key_text",
    "page_keys",
    "page_token_ranges",
    "split_pdf_pages",
    "unique_shared_anchors",
]
