"""Structural-contract checker: the page must be *referentially* well-formed.

The suite consumes both sides as plain dicts and tolerates malformed input
(:mod:`eval.checkers.pagegt` module docstring). "Tolerate" means *never KeyError
mid-check* — it does **not** mean malformed input scores clean. Before this checker
existed it did (review finding H4 / D-237): a candidate that appended a second
region with an existing ``id`` collapsed through last-wins dictionaries and still
passed all four checkers, and a candidate could pad its ``reading_order`` with ids
that referenced no region of its own. Both are direct reward exploits.

Round 3 found the first version too narrow in two ways, both closed here.

**It validated the filtered view, not the input.** ``PageView`` silently drops a
non-object entry in ``regions`` and treats a mistyped ``reading_order`` (a string, a
dict, an int) as absent, so the checker saw nothing wrong; a null region entry and a
string-valued ``reading_order`` each reproduced a clean exit 0. This checker now walks
the **raw** page dict.

**A present order was not required to be a complete order.** Reversing
``reading_order_index`` on every region and declaring ``"reading_order": ["head-1"]``
reproduced exit 0 at tau 1.0, because one resolving entry suppressed the index signal
(review finding L1-1). A declared ``reading_order`` must now be a list of strings
naming every top-level region exactly once and agreeing with whatever
``reading_order_index`` values the page declares. Truncated, mistyped,
non-string-bearing, duplicated and index-contradicting orders are all hard violations.

Design call (the RC-3 "your call" clause): this is a **dedicated checker in the
default suite**, not per-checker guards feeding ``CheckResult.crashed``. Two reasons.
(1) ``crashed`` is reserved, by an earlier review finding (D-008), for "the checker
is broken" as opposed to "the candidate is bad" — a candidate with duplicate ids is
squarely the latter, so routing it to ``crashed`` would destroy exactly the
distinction that finding installed. (2) A single checker gives the violation one
stable id, one detail string, and one place to extend, instead of guards spread over
five checkers that could drift apart.

It runs **first** in the default suite so its verdict reads as the precondition for
the others: when it fails, the remaining scores are computed over a page whose ids do
not uniquely denote regions, or whose order signal is broken, and should be read
accordingly.

Both sides are validated. A malformed *candidate* is a reward exploit; a malformed
*ground truth* is a corpus bug that would otherwise silently shrink what the other
checkers demand — neither should score clean.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any

from .base import Checker, CheckResult, PageLike
from .pagegt import MAX_REGION_DEPTH, PageView, block_ids, declared_order_is_canonical

# Violation kinds, in report order, with the phrase used in the detail string.
_KINDS: dict[str, str] = {
    "non_object_regions": "non-object entr(ies) in regions",
    "regions_without_id": "region(s) with no usable string id",
    "duplicate_region_ids": "duplicate region id(s)",
    "regions_below_depth_cap": (
        f"region(s) nesting children deeper than the depth cap ({MAX_REGION_DEPTH})"
    ),
    "non_integer_reading_order_index": "region(s) whose reading_order_index is not an int",
    "reading_order_not_a_list": "reading_order is present but is not a list",
    "non_string_order_entries": "non-string reading_order entr(ies)",
    "duplicate_order_entries": "repeated reading_order entr(ies)",
    "order_refs_no_region": "reading_order entr(ies) referencing no region",
    "order_omits_regions": "region(s) absent from reading_order",
    "order_breaks_block_structure": "reading_order does not order whole parent+descendant blocks",
    "order_contradicts_indices": "region(s) whose reading_order_index contradicts reading_order",
}


def _walk(raw_regions: Any, depth: int, acc: dict[str, list[str]], ids: list[str]) -> None:
    """Recursively collect raw-region defects; append every usable id to ``ids``."""
    if raw_regions is None:
        return
    if not isinstance(raw_regions, Sequence) or isinstance(raw_regions, str):
        acc["non_object_regions"].append(f"depth {depth}: regions is {type(raw_regions).__name__}")
        return
    for position, entry in enumerate(raw_regions):
        if not isinstance(entry, Mapping):
            acc["non_object_regions"].append(
                f"depth {depth} index {position}: {type(entry).__name__}"
            )
            continue
        region_id = entry.get("id")
        if isinstance(region_id, str) and region_id:
            ids.append(region_id)
        else:
            # NOTE: an id-less region that has id-bearing descendants is reported
            # twice — here, and again as order_breaks_block_structure, because its
            # block cannot be named in a declared order. Redundant, not false: both
            # statements are true of the page and both name the same root cause.
            acc["regions_without_id"].append(f"depth {depth} index {position}")
        children = entry.get("children")
        if children is None:
            continue
        if depth + 1 > MAX_REGION_DEPTH:
            # The flattener stops here, so those regions are invisible to every
            # checker. That must be a reported violation, never a silent truncation
            # of ground truth (review finding L2-5).
            acc["regions_below_depth_cap"].append(str(region_id))
            continue
        _walk(children, depth + 1, acc, ids)


def _all_region_ids(page: PageLike) -> list[str]:
    """Every usable region id at every depth, in depth-first (block) order.

    Depth-uniform since round 4 (probe P3): the completeness rule below used to look
    only at the top level, which left the "flattering declared order" exploit open one
    level down — a candidate could nest a child under the wrong parent and declare an
    order naming all three ids to hide it.
    """
    return [rid for region in PageView(page).top_level_regions for rid in block_ids(region)]


def _declared_indices(raw_regions: Any, defects: list[str]) -> dict[str, int]:
    """``{region_id: index}`` for TOP-LEVEL regions; type-checked at every depth.

    Two different scopes, deliberately.

    **Typing is depth-uniform.** A ``reading_order_index`` that is not an ``int`` — a
    float, a string, a bool — is a mistyped signal, not an absent one, wherever it
    appears. It used to be silently ignored by both ``PageView`` and this checker, so
    float indices contradicting the declared order scored clean (round-4 MINOR-1,
    probe P8b).

    **The index-vs-declared comparison is top-level only** (round-5 adjudication). A
    nested region's index is never consumed: a child's position comes from its
    parent's ``children`` array on every signal path, so comparing nested indices
    against the declared order enforced a constraint on a field the suite does not
    read — and it false-failed the natural sibling-scoped numbering convention (a
    parent at index 0 whose own child is also at index 0) on the GT and candidate
    sides alike. Which depth convention ``reading_order_index`` follows is unspecified
    in the schema; recorded as E1 open question 3 rather than adjudicated here.
    """
    out: dict[str, int] = {}

    def walk(entries: Any, depth: int) -> None:
        if not isinstance(entries, Sequence) or isinstance(entries, str):
            return
        for entry in entries:
            if not isinstance(entry, Mapping):
                continue
            region_id = entry.get("id")
            if isinstance(region_id, str) and region_id and "reading_order_index" in entry:
                index = entry["reading_order_index"]
                # bool is an int subclass; a boolean is not a reading-order index.
                if isinstance(index, int) and not isinstance(index, bool):
                    if depth == 0:
                        out[region_id] = index
                else:
                    defects.append(f"{region_id}: {type(index).__name__}")
            if depth + 1 <= MAX_REGION_DEPTH:
                walk(entry.get("children"), depth + 1)

    walk(raw_regions, 0)
    return out


def _order_index_contradictions(named: list[str], indices: dict[str, int]) -> list[str]:
    """Ids where the declared order and the declared TOP-LEVEL indices disagree.

    The two signals must induce the same sequence over the top-level regions that
    carry both. Anything else is two contradictory orders, and the suite must not get
    to pick the flattering one (review finding L1-1). ``indices`` is already scoped to
    the top level by :func:`_declared_indices` — see its docstring for why.
    """
    rank = {rid: position for position, rid in enumerate(named)}
    both = [rid for rid in named if rid in indices]
    by_index = sorted(both, key=lambda rid: (indices[rid], rid))
    by_order = sorted(both, key=lambda rid: rank[rid])
    return [a for a, b in zip(by_index, by_order, strict=True) if a != b]


def _violations(page: PageLike) -> dict[str, list[str]]:
    """Referential defects of one raw page dict, as ``{kind: [offenders]}`` (sorted)."""
    acc: dict[str, list[str]] = {kind: [] for kind in _KINDS}
    raw_regions = page.get("regions")
    ids: list[str] = []
    _walk(raw_regions, 0, acc, ids)

    counts = Counter(ids)
    acc["duplicate_region_ids"] = [i for i, n in counts.items() if n > 1]

    index_defects: list[str] = []
    indices = _declared_indices(raw_regions, index_defects)
    acc["non_integer_reading_order_index"] = index_defects

    # `in`, not `is not None`: a JSON null reading_order is a *present* order of the
    # wrong type, and used to slip through the not-None gate and score clean
    # (round-4 codex MEDIUM).
    if "reading_order" in page:
        order = page["reading_order"]
        if not isinstance(order, Sequence) or isinstance(order, str):
            acc["reading_order_not_a_list"].append(type(order).__name__)
        else:
            entries = list(order)
            acc["non_string_order_entries"] = [
                f"index {position}: {type(entry).__name__}"
                for position, entry in enumerate(entries)
                if not isinstance(entry, str)
            ]
            named = [entry for entry in entries if isinstance(entry, str)]
            acc["duplicate_order_entries"] = [i for i, n in Counter(named).items() if n > 1]
            acc["order_refs_no_region"] = [rid for rid in named if rid not in counts]
            acc["order_omits_regions"] = [
                rid for rid in _all_region_ids(page) if rid not in set(named)
            ]
            if not declared_order_is_canonical(PageView(page).top_level_regions, named):
                # Narrow the report to the entries that are not block starts, so the
                # detail names the offender rather than the whole list.
                starts = {region.id for region in PageView(page).top_level_regions if region.id}
                acc["order_breaks_block_structure"] = [
                    rid for rid in named if rid in counts and rid not in starts
                ] or ["order is not a permutation of whole parent+descendant blocks"]
            acc["order_contradicts_indices"] = _order_index_contradictions(named, indices)

    return {kind: sorted(set(offenders)) for kind, offenders in acc.items()}


class StructuralContractChecker(Checker):
    """Ids are unique; a declared reading order is single, complete and consistent.

    Fails hard on any of: a non-object entry in ``regions``; a region with no usable
    string ``id``; a repeated region id; children nested past the depth cap; a
    ``reading_order`` that is not a list of strings; a ``reading_order`` entry that is
    repeated, references no region, or omits a top-level region; and a
    ``reading_order`` that contradicts the declared ``reading_order_index`` values.
    Reported as a failing :class:`CheckResult`, never as a raised exception — a
    malformed candidate is a bad candidate, not a broken checker.
    """

    id = "structural-contract"

    def check(self, candidate: PageLike, gt: PageLike) -> CheckResult:
        found = {"candidate": _violations(candidate), "gt": _violations(gt)}

        metrics: dict[str, int] = {}
        problems: list[str] = []
        for side, kinds in found.items():
            for kind, offenders in kinds.items():
                metrics[f"{side}_{kind}"] = len(offenders)
                if offenders:
                    problems.append(f"{side}: {len(offenders)} {_KINDS[kind]} {offenders}")

        passed = not problems
        detail = (
            "candidate and GT are referentially well-formed (every region a unique-id "
            "object within the depth cap; reading_order, where declared, names every "
            "top-level region exactly once and agrees with reading_order_index)"
            if passed
            else "; ".join(problems)
        )
        return self._result(passed=passed, detail=detail, metrics=metrics)
