"""Deterministic mutators for the negative-control tests.

Each mutator takes a PageGT-shaped dict and returns a *new* mutated copy (the input
is never modified). Every mutation is deterministic — no RNG — because the suite it
exercises is itself required to be deterministic: a flaky negative control would be
worthless. Character corruption picks a fixed stride rather than random positions.

The mutators are designed for *isolation*: each is meant to trip exactly one checker
while leaving the others' verdicts unchanged. The negative-control tests assert both
halves of that (target fails AND the rest still pass). One documented limit:
:func:`drop_anchor` is isolated for markers normalization treats as *markup*
(``¹``, ``*``, ``†`` — every committed fixture); an *alphabetic* marker is a content
token after normalization, so removing it necessarily costs text-fidelity one token.

The ``D-237 reward-exploit mutators`` block at the bottom is a different kind: those
reproduce cross-vendor review findings and are expected to fail the suite outright.
"""

from __future__ import annotations

import copy
from typing import Any

PageDict = dict[str, Any]

# Regions treated as prose for character corruption: text-bearing, not notes.
_BODY_LABELS = {"text_block", "block_quote", "abstract", "list_item"}


def _regions(page: PageDict) -> list[dict[str, Any]]:
    """The page's top-level region dicts (mutable references into ``page``)."""
    regions = page.get("regions")
    return regions if isinstance(regions, list) else []


def _all_regions(page: PageDict) -> list[dict[str, Any]]:
    """Every region dict, flattened depth-first through ``children``.

    A mutator that means "every region" must use this, not :func:`_regions`: once
    ``PageView`` began flattening nested regions, a top-level-only mutator silently
    stopped exercising the nested path (round-3 finding on :func:`drop_anchor`).
    """
    out: list[dict[str, Any]] = []

    def walk(regions: list[Any]) -> None:
        for region in regions:
            if not isinstance(region, dict):
                continue
            out.append(region)
            children = region.get("children")
            if isinstance(children, list):
                walk(children)

    walk(_regions(page))
    return out


def strip_standalone(text: str, marker: str) -> str:
    """Remove occurrences of ``marker`` that are not embedded inside a word.

    An occurrence counts as a marker only when neither of its immediate neighbours
    is alphanumeric — ``goddess.¹`` yes, the ``a`` in ``and`` no. Plain
    ``str.replace`` was a review finding (M7 / D-237): for an allowed *alphabetic*
    marker such as ``"a"`` it stripped every ``a`` from the region's prose, so the
    mutation tripped text-fidelity as well as footnote-anchor and the control's
    "exactly one checker" claim was false.
    """
    if not marker:
        return text
    out: list[str] = []
    i = 0
    while i < len(text):
        if text.startswith(marker, i):
            before = text[i - 1] if i else ""
            after = text[i + len(marker)] if i + len(marker) < len(text) else ""
            if not before.isalnum() and not after.isalnum():
                i += len(marker)
                continue
        out.append(text[i])
        i += 1
    return "".join(out)


def drop_anchor(page: PageDict) -> PageDict:
    """Remove every declared in-text anchor marker (text + ``text_anchors``).

    Targets footnote-anchor integrity: the note regions stay, the markers vanish.
    Only *standalone* marker occurrences are removed (see :func:`strip_standalone`),
    so prose survives even when the marker is an ordinary letter. Normalization
    strips markers, so text-fidelity is unaffected; labels and order are untouched,
    so the structural checkers are unaffected.

    Traverses nested children as well as top-level regions, so an anchor declared on
    a nested block is mutated too (round-3 finding: this walked only the top level,
    leaving the nested negative-control path ineffective).
    """
    out = copy.deepcopy(page)
    for region in _all_regions(out):
        markers = region.get("text_anchors") or []
        if not markers:
            continue
        text = region.get("text", "")
        for marker in markers:
            text = strip_standalone(text, marker)
        region["text"] = text
        region["text_anchors"] = []
    return out


def swap_blocks(page: PageDict, id_a: str, id_b: str) -> PageDict:
    """Swap two region ids in the reading order (and their reading_order_index).

    Targets reading-order: produces an inversion. Region texts, labels, and anchors
    are untouched, so the other checkers are unaffected.
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


# ── D-237 reward-exploit mutators ─────────────────────────────────────────────
# These are not isolation controls: each reproduces one exploit from the
# cross-vendor review of PR #3, where a mutation that a scoring gate *must* punish
# was passing the whole suite (or, for `rename_region_ids`, an honest candidate was
# being punished). They are ported from the delegator's reproduction harness so the
# exploits stay closed under regression.


def smear_page_text(page: PageDict, source: PageDict | None = None) -> PageDict:
    """Set every region's text to the whole page's text.

    Round-3 finding: every GT region is then perfectly *contained* in its aligned
    counterpart, so a containment-only per-region gate passed the lot. Caught by the
    misplacement half of the gate, not the retention half.
    """
    out = copy.deepcopy(page)
    whole = " ".join(r.get("text", "") for r in _all_regions(source or page))
    for region in _all_regions(out):
        region["text"] = whole
    return out


def truncate_reading_order(page: PageDict, keep: int = 1) -> PageDict:
    """Keep only the first ``keep`` reading_order entries and reverse the real indices.

    Round-3 finding L1-1: one resolving entry used to suppress the
    ``reading_order_index`` signal entirely, so this reproduced exit 0 at tau 1.0.
    """
    out = copy.deepcopy(page)
    order = out.get("reading_order")
    if isinstance(order, list):
        out["reading_order"] = order[:keep]
    regions = _regions(out)
    for position, region in enumerate(regions):
        region["reading_order_index"] = len(regions) - 1 - position
    return out


def contradict_reading_order_indices(page: PageDict) -> PageDict:
    """Keep the full reading_order but reverse every ``reading_order_index``."""
    out = copy.deepcopy(page)
    regions = _regions(out)
    for position, region in enumerate(regions):
        region["reading_order_index"] = len(regions) - 1 - position
    return out


def mistype_reading_order(page: PageDict, value: Any = "head-1") -> PageDict:
    """Replace ``reading_order`` with a non-list value (or a list with non-strings).

    Round-3 finding: ``PageView`` treated a mistyped order as absent, and the
    contract checker validated that filtered view, so a string-valued
    ``reading_order`` reproduced a clean exit 0.
    """
    out = copy.deepcopy(page)
    out["reading_order"] = value
    return out


def append_non_object_region(page: PageDict, entry: Any = None) -> PageDict:
    """Append a non-object entry (default ``null``) to ``regions``."""
    out = copy.deepcopy(page)
    _regions(out).append(entry)
    return out


def append_region_without_id(page: PageDict) -> PageDict:
    """Append a region object carrying no usable ``id``."""
    out = copy.deepcopy(page)
    _regions(out).append({"label": "text_block", "text": "an unnamed block of prose"})
    return out


def nest_beyond_depth_cap(page: PageDict, depth: int) -> PageDict:
    """Bury a text-bearing region ``depth`` levels of ``children`` deep.

    Beyond the flattener's cap those regions are invisible to every checker; the
    contract checker must report the truncation rather than let the GT shrink
    silently (round-3 finding L2-5).
    """
    out = copy.deepcopy(page)
    regions = _regions(out)
    if not regions:
        return out
    node = regions[0]
    for level in range(depth):
        child = {
            "id": f"nested-{level}",
            "label": "block_quote",
            "text": f"nested level {level} of the buried quotation",
        }
        node["children"] = [child]
        node = child
    return out


def single_char_error(page: PageDict, region_id: str, old: str, new: str) -> PageDict:
    """Replace the first ``old`` with ``new`` in one region — one OCR confusion."""
    out = copy.deepcopy(page)
    for region in _all_regions(out):
        if region.get("id") == region_id:
            region["text"] = region.get("text", "").replace(old, new, 1)
    return out


def swap_region_texts(page: PageDict, id_a: str, id_b: str) -> PageDict:
    """Swap two regions' complete ``text``, leaving ids/labels/bboxes/order intact.

    Review finding H2: page-pooled n-grams are identical after the swap, so content
    attached to the wrong ordered block scored a clean page-level containment of 1.0.
    """
    out = copy.deepcopy(page)
    by_id = {r.get("id"): r for r in _regions(out)}
    a, b = by_id.get(id_a), by_id.get(id_b)
    if a is not None and b is not None:
        a["text"], b["text"] = b.get("text", ""), a.get("text", "")
    return out


def blank_region_text(page: PageDict, region_id: str) -> PageDict:
    """Delete one region's text entirely, keeping the region itself.

    Review finding H3: with page-global n-gram backoff, a one- or two-token region
    (a heading, label, caption, marker) contributed zero evidence, so blanking it
    left containment at 1.0.
    """
    out = copy.deepcopy(page)
    for region in _regions(out):
        if region.get("id") == region_id:
            region["text"] = ""
    return out


def duplicate_region(page: PageDict, region_id: str) -> PageDict:
    """Append a second copy of a region, id included.

    Review finding H4: duplicate ids collapsed through last-wins dictionaries, so
    the extra region was invisible to every checker.
    """
    out = copy.deepcopy(page)
    for region in list(_regions(out)):
        if region.get("id") == region_id:
            out["regions"].append(copy.deepcopy(region))
            break
    return out


def rename_region_ids(page: PageDict, prefix: str = "m-") -> PageDict:
    """Give every region a model-generated id, updating ``reading_order`` to match.

    Not a defect: this is an **honest** candidate that simply did not guess the GT's
    ids. Review finding H1 (first half) — it used to false-FAIL reading-order with
    coverage 0, because order was compared over raw id strings.
    """
    out = copy.deepcopy(page)
    renamed = {r.get("id"): f"{prefix}{i}" for i, r in enumerate(_regions(out))}
    for region in _regions(out):
        region["id"] = renamed[region["id"]]
    order = out.get("reading_order")
    if isinstance(order, list):
        out["reading_order"] = [renamed.get(rid, rid) for rid in order]
    return out


def phantom_reading_order(page: PageDict, order: list[str]) -> PageDict:
    """Declare ``order`` as ``reading_order`` and reverse the regions' real indices.

    Review finding H1 (second half): supplying the GT's id list as a phantom reading
    order made the checker score ids that referenced none of the candidate's own
    regions, so a candidate whose actual ``reading_order_index`` values were reversed
    passed. The declared entries are now a structural-contract violation, and order is
    derived from the candidate's own regions.
    """
    out = copy.deepcopy(page)
    out["reading_order"] = list(order)
    regions = _regions(out)
    for i, region in enumerate(regions):
        region["reading_order_index"] = len(regions) - 1 - i
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
