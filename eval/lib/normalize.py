"""Normalize ground truth and predicted documents to a common comparison format.

This module provides:
1. NormalizedElement - Common dataclass for both ground truth and predicted elements
2. load_ground_truth_elements() - Load and normalize ground truth YAML

NOTE (ported from scholardoc ground_truth/lib): scholar_doc_to_elements() below
converts a pipeline document object into NormalizedElements. The agentic-ocr
pipeline does not yet exist (PLAN.md: `pipeline/` empty in Phase 0), so that
function imports its document type lazily and is DEFERRED / untested until the
pipeline lands. Everything above it (NormalizedElement, the YAML loader, and the
matching/metrics/reports modules that build on them) is live and tested.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class NormalizedElement:
    """Common format for ground truth and predicted elements.

    This dataclass represents any extractable element (footnote, citation, etc.)
    in a normalized format suitable for comparison.
    """

    element_type: str  # "footnote", "citation", "marginal_ref", "page_number", "sous_rature"
    element_id: str  # Unique identifier
    pages: list[int]  # Pages where element appears (supports multi-page)
    text: str  # Full text content (concatenated for multi-page)
    marker_text: str | None = None  # For footnotes: the marker ("1", "*", etc.)
    marker_page: int | None = None  # Page where marker appears
    char_offset: int | None = None  # Character offset in source text
    char_length: int | None = None  # Length of element text
    bbox: tuple[float, float, float, float] | None = None  # Normalized [x0, y0, x1, y1]
    attributes: dict[str, Any] = field(default_factory=dict)  # Type-specific fields
    tags: list[str] = field(default_factory=list)  # Tags for filtering

    @property
    def primary_page(self) -> int:
        """Return the primary page (first page for multi-page elements)."""
        return self.pages[0] if self.pages else -1


def load_ground_truth_elements(yaml_path: Path) -> list[NormalizedElement]:
    """Load ground truth YAML and convert to normalized elements.

    Args:
        yaml_path: Path to ground truth YAML file

    Returns:
        List of NormalizedElement for all annotated elements

    Raises:
        FileNotFoundError: If YAML file doesn't exist
        yaml.YAMLError: If YAML is malformed
    """
    with open(yaml_path) as f:
        gt = yaml.safe_load(f)

    elements: list[NormalizedElement] = []

    gt_elements = gt.get("elements", {})

    # Footnotes
    for fn in gt_elements.get("footnotes", []):
        elements.append(_normalize_footnote(fn))

    # Citations
    for cite in gt_elements.get("citations", []):
        elements.append(_normalize_citation(cite))

    # Marginal references
    for ref in gt_elements.get("marginal_refs", []):
        elements.append(_normalize_marginal_ref(ref))

    # Page numbers
    for pn in gt_elements.get("page_numbers", []):
        elements.append(_normalize_page_number(pn))

    # Sous rature
    for sr in gt_elements.get("sous_rature", []):
        elements.append(_normalize_sous_rature(sr))

    return elements


def _normalize_footnote(fn: dict[str, Any]) -> NormalizedElement:
    """Convert ground truth footnote to NormalizedElement."""
    # Concatenate text from all content parts
    text_parts = []
    for content in fn.get("content", []):
        text_parts.append(content.get("text", ""))
    full_text = " ".join(text_parts).strip()

    marker = fn.get("marker", {})

    return NormalizedElement(
        element_type="footnote",
        element_id=fn.get("id", "unknown"),
        pages=fn.get("pages", []),
        text=full_text,
        marker_text=marker.get("text"),
        marker_page=marker.get("page"),
        char_offset=marker.get("char_offset"),
        char_length=len(marker.get("text", "")),
        bbox=None,  # Could extract from region if needed
        attributes={
            "note_type": fn.get("note_type", "author"),
            "is_multi_page": len(fn.get("pages", [])) > 1,
            "region_id": marker.get("region_id"),
        },
        tags=fn.get("tags", []),
    )


def _normalize_citation(cite: dict[str, Any]) -> NormalizedElement:
    """Convert ground truth citation to NormalizedElement."""
    raw = cite.get("raw", "")
    parsed = cite.get("parsed", {})

    return NormalizedElement(
        element_type="citation",
        element_id=cite.get("id", "unknown"),
        pages=[cite.get("page", -1)],
        text=raw,
        marker_text=None,
        marker_page=None,
        char_offset=cite.get("char_offset"),
        char_length=len(raw),
        bbox=None,
        attributes={
            "style": parsed.get("style", "unknown"),
            "authors": parsed.get("authors", []),
            "year": parsed.get("year"),
            "pages": parsed.get("pages"),
            "region_id": cite.get("region_id"),
            "bib_entry_id": cite.get("bib_entry_id"),
        },
        tags=cite.get("tags", []),
    )


def _normalize_marginal_ref(ref: dict[str, Any]) -> NormalizedElement:
    """Convert ground truth marginal reference to NormalizedElement."""
    markers = ref.get("markers", [])
    marker_texts = [m.get("text", "") for m in markers]
    marker_pages = [m.get("page") for m in markers if m.get("page") is not None]

    return NormalizedElement(
        element_type="marginal_ref",
        element_id=ref.get("id", "unknown"),
        pages=marker_pages or [-1],
        text=" ".join(marker_texts),
        marker_text=marker_texts[0] if marker_texts else None,
        marker_page=marker_pages[0] if marker_pages else None,
        char_offset=None,
        char_length=None,
        bbox=None,
        attributes={
            "system": ref.get("system", "custom"),
        },
        tags=ref.get("tags", []),
    )


def _normalize_page_number(pn: dict[str, Any]) -> NormalizedElement:
    """Convert ground truth page number to NormalizedElement."""
    return NormalizedElement(
        element_type="page_number",
        element_id=f"pn_{pn.get('page', -1)}",
        pages=[pn.get("page", -1)],
        text=str(pn.get("displayed", "")),
        marker_text=None,
        marker_page=None,
        char_offset=None,
        char_length=None,
        bbox=None,
        attributes={
            "normalized": pn.get("normalized"),
            "format": pn.get("format", "arabic"),
            "position": pn.get("position", "footer"),
        },
        tags=[],
    )


def _normalize_sous_rature(sr: dict[str, Any]) -> NormalizedElement:
    """Convert ground truth sous rature to NormalizedElement."""
    return NormalizedElement(
        element_type="sous_rature",
        element_id=sr.get("id", "unknown"),
        pages=[sr.get("page", -1)],
        text=sr.get("text", ""),
        marker_text=None,
        marker_page=None,
        char_offset=sr.get("char_offset"),
        char_length=sr.get("char_length"),
        bbox=None,
        attributes={
            "display_form": sr.get("display_form"),
            "context": sr.get("context"),
            "region_id": sr.get("region_id"),
        },
        tags=sr.get("tags", []),
    )


def scholar_doc_to_elements(doc: Any) -> list[NormalizedElement]:  # pragma: no cover
    """Convert a pipeline document object into normalized elements.

    DEFERRED (Phase 0): the agentic-ocr pipeline does not yet emit a document
    type, so the import below resolves nothing and this function is not exercised
    by the test suite. Carried over from scholardoc as the contract the future
    pipeline adapter must satisfy; rewrite the import to the real document type
    when `pipeline/` lands.

    Args:
        doc: a pipeline document instance with .notes / .footnote_refs / .citations

    Returns:
        List of NormalizedElement for all extracted elements
    """
    # Import here to avoid a hard dependency on the (not-yet-existing) pipeline.
    from scholardoc.models import ScholarDocument  # type: ignore[import-not-found]

    if not isinstance(doc, ScholarDocument):
        raise TypeError(f"Expected ScholarDocument, got {type(doc)}")

    elements: list[NormalizedElement] = []

    # Footnotes (footnote_refs + notes)
    note_map = {note.label: note for note in doc.notes}
    for fn_ref in doc.footnote_refs:
        note = note_map.get(fn_ref.label)
        page = _position_to_page(doc, fn_ref.position)

        elements.append(
            NormalizedElement(
                element_type="footnote",
                element_id=f"fn_{fn_ref.label}",
                pages=[page] if page >= 0 else [],
                text=note.content if note else "",
                marker_text=fn_ref.label,
                marker_page=page,
                char_offset=fn_ref.position,
                char_length=len(fn_ref.label),
                bbox=None,
                attributes={
                    "note_type": note.note_type.value if note else "author",
                    "is_multi_page": False,  # ScholarDocument doesn't track this yet
                },
                tags=[],
            )
        )

    # Citations
    for cite in doc.citations:
        page = _position_to_page(doc, cite.position)

        parsed_attrs = {}
        if cite.parsed:
            parsed_attrs = {
                "style": cite.parsed.style if hasattr(cite.parsed, "style") else "unknown",
                "authors": cite.parsed.authors if hasattr(cite.parsed, "authors") else [],
                "year": cite.parsed.year if hasattr(cite.parsed, "year") else None,
            }

        elements.append(
            NormalizedElement(
                element_type="citation",
                element_id=f"cite_{cite.position}",
                pages=[page] if page >= 0 else [],
                text=cite.raw,
                marker_text=None,
                marker_page=None,
                char_offset=cite.position,
                char_length=len(cite.raw),
                bbox=None,
                attributes=parsed_attrs,
                tags=[],
            )
        )

    return elements


def _position_to_page(doc: Any, position: int) -> int:  # pragma: no cover
    """Convert character position to page number (helper for the deferred adapter)."""
    try:
        page_span = doc.page_for_position(position)
        if page_span:
            # page_for_position returns PageSpan with page_index
            return page_span.page_index if hasattr(page_span, "page_index") else -1
    except (AttributeError, IndexError):
        pass
    return -1
