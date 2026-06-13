"""Read-only accessors over a PageGT-shaped mapping.

The checker suite scores *any* candidate pipeline output against a ground-truth
page. Both sides are consumed as plain ``PageGT``-shaped dicts (parsed JSON), not
as pydantic models: agentic-ocr deliberately does **not** pin the ``scholar-schema``
package in Phase 0 (STATE.md: "This repo does not yet pin scholar-schema/scriptorium
versions"), candidate output must be tolerated even when partially malformed, and
keeping everything at the dict layer keeps every checker deterministic — no import
side effects, no model-construction surprises.

The shape mirrors ``scholar-schema``'s ``PageGT``/``Region`` contract
(``scholargt/schema/{page,spatial,labels}.py``):

    {
      "page_index": 0,
      "reading_order": ["body-1", "note-1"],
      "regions": [
        {"id": "body-1", "label": "text_block", "bbox": {...},
         "text": "...", "text_anchors": ["¹"], "semantic_labels": ["note"],
         "reading_order_index": 0},
        ...
      ]
    }

This module exposes a thin ``PageView`` wrapper plus the spatial/semantic
classification helpers the checkers share. It reads; it never mutates.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

# ── Canonical block types (the structure-typing axis) ─────────────────────────
# We collapse the schema's 21 SpatialLabel values + 9 SemanticType values onto the
# coarse types the checker suite scores (PLAN §4 L2 "typed semantics": body /
# footnote / heading / ...). The mapping is intentionally small and explicit; an
# unrecognised label maps to "other" rather than raising, so a candidate emitting a
# novel label degrades gracefully instead of crashing the run.

# scholar-schema SpatialLabel values that mean "note" spatially.
_NOTE_SPATIAL_LABELS = frozenset(
    {"note_area", "note_continuation", "footnote_area", "endnote_area", "marginal_note"}
)
# scholar-schema SemanticType values that mean "note" semantically.
_NOTE_SEMANTIC_LABELS = frozenset({"note", "footnote", "endnote"})

_HEADING_LABELS = frozenset({"section_header", "title", "page_header"})
_BODY_LABELS = frozenset({"text_block", "block_quote", "abstract", "list_item"})


@dataclass(frozen=True)
class RegionView:
    """A read-only view of one PageGT region dict.

    Wraps the raw mapping and exposes the fields checkers need with safe
    defaults, so a missing key is an absent value (None / empty), never a
    KeyError mid-check.
    """

    raw: Mapping[str, Any]

    @property
    def id(self) -> str:
        """Region id; falls back to the empty string when absent."""
        rid = self.raw.get("id")
        return rid if isinstance(rid, str) else ""

    @property
    def label(self) -> str:
        """Spatial label (``SpatialLabel`` value), lower-cased; '' if absent."""
        label = self.raw.get("label")
        return label.lower() if isinstance(label, str) else ""

    @property
    def text(self) -> str:
        """Transcribed text content; '' if absent or null."""
        text = self.raw.get("text")
        return text if isinstance(text, str) else ""

    @property
    def semantic_labels(self) -> tuple[str, ...]:
        """Semantic labels (``SemanticType`` values), lower-cased."""
        raw = self.raw.get("semantic_labels")
        if not isinstance(raw, Sequence) or isinstance(raw, str):
            return ()
        return tuple(s.lower() for s in raw if isinstance(s, str))

    @property
    def text_anchors(self) -> tuple[str, ...]:
        """In-text anchor markers declared on this region (e.g. ['¹'])."""
        raw = self.raw.get("text_anchors")
        if not isinstance(raw, Sequence) or isinstance(raw, str):
            return ()
        return tuple(a for a in raw if isinstance(a, str))

    @property
    def reading_order_index(self) -> int | None:
        """Position in reading order, if declared on the region."""
        idx = self.raw.get("reading_order_index")
        return idx if isinstance(idx, int) else None

    @property
    def bbox(self) -> tuple[float, float, float, float] | None:
        """Normalized bbox as (x0, y0, x1, y1), if present and well-formed."""
        bb = self.raw.get("bbox")
        if not isinstance(bb, Mapping):
            return None
        try:
            return (
                float(bb["x0"]),
                float(bb["y0"]),
                float(bb["x1"]),
                float(bb["y1"]),
            )
        except (KeyError, TypeError, ValueError):
            return None

    @property
    def is_note(self) -> bool:
        """True if this region is a note either spatially or semantically.

        The schema's multi-dimensional-label principle means a region can be
        spatially ``text_block`` yet semantically ``note``; either signal counts.
        """
        if any(s in _NOTE_SEMANTIC_LABELS for s in self.semantic_labels):
            return True
        return self.label in _NOTE_SPATIAL_LABELS

    @property
    def block_type(self) -> str:
        """Coarse block type for structure-typing: body / footnote / heading / other.

        Semantic ``note`` wins over the spatial label (a footnote typeset as a
        text block is still a footnote); otherwise the spatial label decides.
        """
        if self.is_note:
            return "footnote"
        if self.label in _HEADING_LABELS:
            return "heading"
        if self.label in _BODY_LABELS:
            return "body"
        return "other"


class PageView:
    """A read-only view over a PageGT-shaped mapping.

    Provides ordered region access, id lookup, and the reading-order sequence the
    checkers consume. Construction never raises on a malformed page: missing or
    mistyped fields surface as empty collections so a checker can report the gap
    rather than crash.
    """

    def __init__(self, data: Mapping[str, Any]) -> None:
        self._data = data
        raw_regions = data.get("regions")
        regions: list[RegionView] = []
        if isinstance(raw_regions, Sequence) and not isinstance(raw_regions, str):
            regions = [RegionView(r) for r in raw_regions if isinstance(r, Mapping)]
        self._regions = regions
        self._by_id = {r.id: r for r in regions if r.id}

    @property
    def regions(self) -> list[RegionView]:
        """Regions in their declared (file) order."""
        return list(self._regions)

    def region(self, region_id: str) -> RegionView | None:
        """Look up a region by id; None if absent."""
        return self._by_id.get(region_id)

    @property
    def reading_order(self) -> list[str]:
        """The reading-order sequence of region ids.

        Primary source is the page's ``reading_order`` list. When absent, fall
        back to sorting regions by ``reading_order_index`` (regions lacking an
        index sort last, stably by file order); when neither exists, fall back to
        file order. This makes the reading-order checker robust to candidates that
        express order one way but not the other.
        """
        ro = self._data.get("reading_order")
        if isinstance(ro, Sequence) and not isinstance(ro, str):
            ids = [rid for rid in ro if isinstance(rid, str)]
            if ids:
                return ids
        indexed = [r for r in self._regions if r.reading_order_index is not None]
        if indexed:
            fallback = len(self._regions)  # regions without an index sort last

            def _order_key(region: RegionView) -> int:
                idx = region.reading_order_index
                return idx if idx is not None else fallback

            ordered = sorted(self._regions, key=_order_key)
            return [r.id for r in ordered if r.id]
        return [r.id for r in self._regions if r.id]

    def notes(self) -> list[RegionView]:
        """All regions classified as notes (spatial or semantic)."""
        return [r for r in self._regions if r.is_note]

    def full_text(self) -> str:
        """Concatenation of region texts in reading order (for reporting only).

        Checkers that need order-invariant comparison build per-region token sets
        instead; this is a convenience for human-readable detail strings.
        """
        order = self.reading_order
        ranked = {rid: i for i, rid in enumerate(order)}
        regions = sorted(
            self._regions,
            key=lambda r: ranked.get(r.id, len(order)),
        )
        return "\n".join(r.text for r in regions if r.text)
