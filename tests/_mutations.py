"""Deterministic mutators for the negative-control tests.

Each mutator takes a PageGT-shaped dict and returns a *new* mutated copy (the input
is never modified). Every mutation is deterministic — no RNG — because the suite it
exercises is itself required to be deterministic: a flaky negative control would be
worthless. Character corruption picks a fixed stride rather than random positions.

The mutators are designed for *isolation*: each is meant to trip exactly one checker
while leaving the others' verdicts unchanged. The negative-control tests assert both
halves of that (target fails AND the rest still pass).
"""

from __future__ import annotations

import copy
from typing import Any

PageDict = dict[str, Any]

# Regions treated as prose for character corruption: text-bearing, not notes.
_BODY_LABELS = {"text_block", "block_quote", "abstract", "list_item"}


def _regions(page: PageDict) -> list[dict[str, Any]]:
    regions = page.get("regions")
    return regions if isinstance(regions, list) else []


def drop_anchor(page: PageDict) -> PageDict:
    """Remove every declared in-text anchor marker (text + ``text_anchors``).

    Targets footnote-anchor integrity: the note regions stay, the markers vanish.
    Normalization strips markers, so text-fidelity is unaffected; labels and order
    are untouched, so structure-typing and reading-order are unaffected.
    """
    out = copy.deepcopy(page)
    for region in _regions(out):
        markers = region.get("text_anchors") or []
        if not markers:
            continue
        text = region.get("text", "")
        for marker in markers:
            text = text.replace(marker, "")
        region["text"] = text
        region["text_anchors"] = []
    return out


def swap_blocks(page: PageDict, id_a: str, id_b: str) -> PageDict:
    """Swap two region ids in the reading order (and their reading_order_index).

    Targets reading-order: produces an inversion. Region texts, labels, and anchors
    are untouched, so the other three checkers are unaffected.
    """
    out = copy.deepcopy(page)
    order = out.get("reading_order")
    if isinstance(order, list) and id_a in order and id_b in order:
        ia, ib = order.index(id_a), order.index(id_b)
        order[ia], order[ib] = order[ib], order[ia]
    # Keep reading_order_index consistent with the swapped list.
    idx = {}
    for region in _regions(out):
        if region.get("id") in (id_a, id_b) and isinstance(region.get("reading_order_index"), int):
            idx[region["id"]] = region["reading_order_index"]
    if id_a in idx and id_b in idx:
        for region in _regions(out):
            if region.get("id") == id_a:
                region["reading_order_index"] = idx[id_b]
            elif region.get("id") == id_b:
                region["reading_order_index"] = idx[id_a]
    return out


def corrupt_chars(page: PageDict, rate: float = 0.05) -> PageDict:
    """Corrupt ~``rate`` of the alphabetic characters in body (prose) regions.

    Deterministic: every ``round(1/rate)``-th alphabetic character (across the
    concatenated prose, so short regions still contribute) is replaced with a
    different letter. Anchor markers (non-alphabetic, e.g. ``¹``) and note regions
    are left intact, isolating the failure to text-fidelity.
    """
    out = copy.deepcopy(page)
    stride = max(1, round(1 / rate))
    alpha_seen = 0
    for region in _regions(out):
        label = (region.get("label") or "").lower()
        semantic = [s.lower() for s in (region.get("semantic_labels") or [])]
        is_note = label in {"note_area", "note_continuation", "marginal_note"} or "note" in semantic
        if is_note or label not in _BODY_LABELS:
            continue
        text = region.get("text", "")
        chars = list(text)
        for i, ch in enumerate(chars):
            if ch.isalpha():
                alpha_seen += 1
                if alpha_seen % stride == 0:
                    chars[i] = "x" if ch.casefold() != "x" else "q"
        region["text"] = "".join(chars)
    return out


def mislabel(page: PageDict, region_id: str, new_label: str) -> PageDict:
    """Change one region's spatial ``label`` to ``new_label``.

    Targets structure-typing. The default callers relabel a heading as body (or
    body as heading) — never to/from a note — so notes, anchors, text, and order
    are untouched.
    """
    out = copy.deepcopy(page)
    for region in _regions(out):
        if region.get("id") == region_id:
            region["label"] = new_label
    return out
