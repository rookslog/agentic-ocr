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
         "reading_order_index": 0,
         "children": [ ... nested Region dicts ... ]},
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

# Spatial labels that mean "note". The current v2.0.0 SpatialLabel members are
# note_area / note_continuation / marginal_note; "footnote_area" / "endnote_area"
# are RETIRED v1 values kept only for dict back-compat (they cannot appear in a
# v2.0.0 PageGT) — not current SpatialLabel members.
_NOTE_SPATIAL_LABELS = frozenset(
    {"note_area", "note_continuation", "marginal_note", "footnote_area", "endnote_area"}
)
# Semantic labels that mean "note". Current v2.0.0 SemanticType has only "note"
# (footnote/endnote were unified into it); "footnote"/"endnote" are retired v1
# values kept for back-compat, not current SemanticType members.
_NOTE_SEMANTIC_LABELS = frozenset({"note", "footnote", "endnote"})

# Section/document headings. page_header (a running header repeated atop every
# page) is deliberately NOT here: folding it into "heading" would let a page_header
# ↔ section_header swap score as a correct match and mask a real L2 typing error
# (review finding D-008). page_header therefore falls through to "other".
_HEADING_LABELS = frozenset({"section_header", "title"})
_BODY_LABELS = frozenset({"text_block", "block_quote", "abstract", "list_item"})

# Guard on how deep ``Region.children`` nesting is walked. JSON cannot express a
# cycle, so this only bounds pathological input (a hand-written page nested
# thousands deep would otherwise blow the recursion limit inside a checker and be
# captured as a *crash*, which the contract reserves for checker bugs).
MAX_REGION_DEPTH = 32


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
    def children(self) -> tuple[RegionView, ...]:
        """Nested child regions (``Region.children`` in the PageGT contract).

        scholar-schema's ``Region`` carries a ``children`` list (scholargt/schema/
        spatial.py), so a ``text_block`` may contain a nested ``block_quote`` whose
        text and type are part of the page's ground truth. Regions that declare no
        children yield an empty tuple.
        """
        raw = self.raw.get("children")
        if not isinstance(raw, Sequence) or isinstance(raw, str):
            return ()
        return tuple(RegionView(c) for c in raw if isinstance(c, Mapping))

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


def _flatten(regions: Sequence[RegionView], depth: int = 0) -> list[RegionView]:
    """Depth-first flattening of a region hierarchy: parent, then its descendants.

    WORKING CONVENTION — parent text is **exclusive** of its children's. A parent
    region's ``text`` is taken to hold only what is not inside a child region, so
    flattening concatenates without double-counting and per-region containment scores
    each block against its own share of the page.

    This is a *decision*, not a reading of the contract: scholar-schema's ``Region``
    documents ``text`` as optional and specifies nothing about whether a parent's text
    subsumes its children's (review finding L2-9, round 3). Inclusive text would
    double-count every nested block in the page-level n-gram multiset and would make a
    child's misplacement invisible to the per-region gate. No runtime detection is
    attempted — semantics that are sometimes one and sometimes the other are not
    semantics. The open question is recorded in the packet report as an E1
    schema-revision input; if the schema later specifies inclusive text, this
    docstring and :meth:`PageView.full_text` are the places that change.

    Regions deeper than ``MAX_REGION_DEPTH`` are not flattened; that truncation is a
    hard structural violation reported by
    :class:`~eval.checkers.contract.StructuralContractChecker` (review finding L2-5),
    never a silent loss of ground truth.
    """
    out: list[RegionView] = []
    for region in regions:
        out.append(region)
        if depth < MAX_REGION_DEPTH:
            out.extend(_flatten(region.children, depth + 1))
    return out


def block_ids(region: RegionView, depth: int = 0) -> list[str]:
    """A region's id followed by its descendants' ids, depth-first.

    This is the *block* a region occupies in reading order: the documented invariant
    is that a region is immediately followed by its descendants, so a declared
    reading order is well-formed only if it is a concatenation of whole blocks.
    """
    out = [region.id] if region.id else []
    if depth < MAX_REGION_DEPTH:
        for child in region.children:
            out.extend(block_ids(child, depth + 1))
    return out


def declared_order_is_canonical(
    top_level: Sequence[RegionView], declared: Sequence[str]
) -> bool:
    """True iff ``declared`` is a permutation of the top-level *blocks*, complete.

    Complete (names every region at every depth exactly once) **and** block-structured
    (each region immediately followed by its own descendants, in declared child
    order). Round-4 findings, both reproduced:

    - The completeness rule used to be top-level-only, so a candidate could nest a
      child under the wrong parent — a real structural error its own index/array
      signal exposed — and then declare a flattering order naming all three ids, and
      pass every checker (probe P3).
    - Emission did not actually honour the child-follows-parent invariant it
      documented: a declared ``["K", "P", "Q"]`` with ``K`` nested under ``P``
      produced exactly that order, child before parent (probe P8c).

    Both close the same way: a declared order that is not a whole-blocks permutation
    is not order information about *this* hierarchy. It is not honoured here, and it
    is a hard violation in
    :class:`~eval.checkers.contract.StructuralContractChecker`.
    """
    blocks = {region.id: block_ids(region) for region in top_level if region.id}
    position = 0
    seen: set[str] = set()
    entries = list(declared)
    while position < len(entries):
        block = blocks.get(entries[position])
        if block is None or entries[position] in seen:
            return False  # not a top-level region, or a block starting twice
        if entries[position : position + len(block)] != block:
            return False  # descendants do not immediately follow their parent
        seen.add(entries[position])
        position += len(block)
    return sum(len(b) for b in blocks.values()) == len(entries) and len(seen) == len(blocks)


class PageView:
    """A read-only view over a PageGT-shaped mapping.

    Provides ordered region access, id lookup, and the reading-order sequence the
    checkers consume. Construction never raises on a malformed page: missing or
    mistyped fields surface as empty collections so a checker can report the gap
    rather than crash.
    """

    def __init__(self, data: Mapping[str, Any]) -> None:
        self._data = data
        self.raw: Mapping[str, Any] = data
        raw_regions = data.get("regions")
        top_level: list[RegionView] = []
        if isinstance(raw_regions, Sequence) and not isinstance(raw_regions, str):
            top_level = [RegionView(r) for r in raw_regions if isinstance(r, Mapping)]
        self._top_level = top_level
        # Flattened, depth-first: a parent immediately followed by its descendants.
        # Nested regions are part of the GT (review finding M5 / D-237): traversing
        # only the top level made a deleted child region cost nothing.
        self._regions = _flatten(top_level)
        # NOTE: last-wins on duplicate ids. Duplicate ids are a *contract violation*
        # surfaced by StructuralContractChecker (review finding H4 / D-237); this
        # map deliberately stays total and non-raising so checkers never KeyError.
        self._by_id = {r.id: r for r in self._regions if r.id}

    @property
    def regions(self) -> list[RegionView]:
        """All regions, flattened depth-first (parent, then its descendants).

        Order is deterministic: declared order at each level, parents before their
        children.
        """
        return list(self._regions)

    @property
    def top_level_regions(self) -> list[RegionView]:
        """Only the regions declared at the page's top level, in file order."""
        return list(self._top_level)

    def region(self, region_id: str) -> RegionView | None:
        """Look up a region by id; None if absent."""
        return self._by_id.get(region_id)

    def declared_reading_order(self) -> list[str]:
        """The raw ``reading_order`` id list as declared, unresolved and un-deduped.

        Kept separate from :attr:`reading_order` so the structural-contract checker
        can see entries that reference no region, and repeated entries, instead of
        having them silently resolved away.
        """
        ro = self._data.get("reading_order")
        if not isinstance(ro, Sequence) or isinstance(ro, str):
            return []
        return [rid for rid in ro if isinstance(rid, str)]

    @property
    def order_signal(self) -> str:
        """Which of the three signals actually orders this page.

        ``"declared"`` (a canonical ``reading_order`` list), ``"indices"``
        (``reading_order_index`` on at least one top-level region), or ``"array"``
        (nothing declared — file order, the last resort). Surfaced as a metric so a
        consumer of the scorecard can see which evidence a page was scored on rather
        than having to infer it (round-4 finding MAJOR-2).
        """
        declared = self.declared_reading_order()
        if declared and declared_order_is_canonical(self._top_level, declared):
            return "declared"
        if any(r.reading_order_index is not None for r in self._top_level):
            return "indices"
        return "array"

    @property
    def reading_order(self) -> list[str]:
        """The reading-order sequence of region ids *that this page actually has*.

        There is exactly **one** signal, chosen by a condition the candidate cannot
        game (review finding L1-1, round 3 — the previous rule had two
        "choose your flattering signal" switches):

        - The declared ``reading_order`` list is honoured **only when it is canonical**
          — see :func:`declared_order_is_canonical`: it must name every region at
          every depth exactly once, with each region's descendants immediately
          following it. A partial list is not a cheaper order, it is a broken one:
          with the old "any entry that resolves wins" rule, a candidate could reverse
          ``reading_order_index`` on every region, declare
          ``"reading_order": ["head-1"]``, and have the index evidence suppressed
          entirely — reproduced as exit 0 at tau 1.0. The completeness half was
          top-level-only until round 4, which left the same exploit open one level
          down (probe P3).
        - Otherwise the order comes from ``reading_order_index`` over the top-level
          regions (regions lacking an index sort last, stably by file order), and
          when no index is declared either, from **array order**.

        Array order is therefore the last-resort signal, and on a page that declares
        neither a ``reading_order`` nor any ``reading_order_index`` it is
        **load-bearing**: permuting such a page's ``regions`` list genuinely changes
        its reading order, and the scorecard changes with it. That is not a violation
        of the permutation-invariance property (D-008) — that property says a
        *semantics-preserving* permutation must not flip a verdict, and when array
        order is the only order signal a permutation is not semantics-preserving.
        Consumers can see which signal scored a page: :attr:`order_signal`, surfaced
        as a metric by the reading-order checker.

        There is no fourth, tail-filling pass: the old one appended whatever the
        earlier signals missed in raw array order *in addition to* them, which is what
        let a page mix two signals. Any page for which the declared list is
        non-canonical, mistyped, duplicated, or contradicts the declared indices is a
        hard structural violation reported by
        :class:`~eval.checkers.contract.StructuralContractChecker` — not silently
        resolved here.

        Each emitted region is immediately followed by its descendants (depth-first),
        on every path, so a nested child is always ordered at its parent's position.
        """
        seq: list[str] = []
        seen: set[str] = set()

        def emit(region: RegionView, depth: int = 0) -> None:
            if region.id and region.id not in seen:
                seen.add(region.id)
                seq.append(region.id)
            if depth >= MAX_REGION_DEPTH:
                return
            for child in region.children:
                emit(child, depth + 1)

        declared = self.declared_reading_order()
        if declared and declared_order_is_canonical(self._top_level, declared):
            for rid in declared:
                if rid in self._by_id:
                    emit(self._by_id[rid])
            return seq

        roots = self._top_level
        if any(r.reading_order_index is not None for r in roots):
            fallback = len(roots)  # regions without an index sort last

            def _order_key(region: RegionView) -> int:
                idx = region.reading_order_index
                return idx if idx is not None else fallback

            roots = sorted(roots, key=_order_key)
        for region in roots:
            emit(region)
        return seq

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
