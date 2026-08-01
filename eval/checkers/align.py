"""Deterministic alignment of candidate regions to ground-truth regions.

Structure-typing, footnote-anchor, text-fidelity and reading-order all need to know
*which* candidate region corresponds to a given GT region. Two regimes matter:

1. **Fixture-derived candidates (Phase 0).** The candidate reuses the GT region
   ids, so id-equality is an exact, trivially-deterministic alignment. This is the
   path the goal packet's end-to-end fixture run takes.
2. **Real pipeline output (later).** A pipeline invents its own ids, so we fall
   back to bounding-box overlap (IoU) over the still-unmatched regions.

The IoU fallback is an **exact optimal assignment**: it maximises the number of
matched regions first, then the total IoU. Two earlier designs were review findings.
A greedy descending-IoU scan (M6 / D-237) takes A-X at .905 and strands B, though
A-Y (.700) + B-X (.600) matches both — the spurious miss then false-fails
footnote-anchor and structure-typing on an honest candidate. Replacing greedy with
an exact search *above a size cap only* (M6-NOT-CLOSED, round 3) merely moved the
bug behind a threshold — a reproduced 17-node component matched 16 instead of 17 —
and the recursive search it capped blew the stack at ~1000 GT regions while the cap
counted only candidates (L2-4). There is now **one** path for every input size: the
Hungarian (Jonker-Volgenant) algorithm, iterative, O(n²m) on the smaller side, no
recursion, no size cap, no silently-degraded mode, no new dependency.

Determinism is load-bearing for the reward-signal use: a candidate that merely lists
the same regions in a different order is semantically identical, so it must produce
an identical alignment (and identical verdicts). Every ordering the algorithm sees is
derived from **intrinsic region ids** (sorted), never from array position — keying
tie-breaks on enumeration order would let a reordering of ``regions`` flip a hard
verdict (review finding D-008).

The function returns a mapping ``gt_id -> candidate_id | None``. ``None`` means the
GT region has no acceptable counterpart (a miss).
"""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Mapping
from typing import Any

from .pagegt import PageView, RegionView

_INF = float("inf")

# align_regions is called once per alignment-consuming checker — four times per page
# for the default suite — on the same two dicts, and the assignment is a pure
# function of them. This memo makes the repeat calls free.
#
# Keyed on object identity, which is sound *because* the cache holds a strong
# reference to each keyed dict: a cached dict can never be collected, so its id can
# never be recycled onto a different object while the entry lives. Hits additionally
# re-check identity. Bounded (FIFO) so a long-running process cannot grow without
# limit; 8 entries covers a page's four alignment consumers with room to spare.
_CACHE_MAXSIZE = 8
_cache: OrderedDict[
    tuple[int, int, float],
    tuple[Mapping[str, Any], Mapping[str, Any], dict[str, str | None]],
] = OrderedDict()


def _iou(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> float:
    """Intersection-over-union of two (x0, y0, x1, y1) boxes."""
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    ix0, iy0 = max(ax0, bx0), max(ay0, by0)
    ix1, iy1 = min(ax1, bx1), min(ay1, by1)
    iw, ih = max(0.0, ix1 - ix0), max(0.0, iy1 - iy0)
    inter = iw * ih
    if inter <= 0.0:
        return 0.0
    area_a = max(0.0, ax1 - ax0) * max(0.0, ay1 - ay0)
    area_b = max(0.0, bx1 - bx0) * max(0.0, by1 - by0)
    union = area_a + area_b - inter
    return inter / union if union > 0.0 else 0.0


def _hungarian(cost: list[list[float]], n: int, m: int) -> list[int]:
    """Minimum-cost assignment of ``n`` rows to ``m >= n`` columns (Jonker-Volgenant).

    ``cost`` is 1-indexed: ``cost[i][j]`` for ``i`` in 1..n, ``j`` in 1..m. Returns
    ``p``, where ``p[j]`` is the row assigned to column ``j`` (0 = unassigned).
    Iterative and O(n²m) — no recursion, so page size cannot exhaust the stack.

    Deterministic: every comparison that selects a column is strict (``<``), so the
    lowest column index wins a tie, and column indices are assigned from sorted
    region ids by the caller.
    """
    u = [0.0] * (n + 1)
    v = [0.0] * (m + 1)
    p = [0] * (m + 1)
    way = [0] * (m + 1)

    for i in range(1, n + 1):
        p[0] = i
        j0 = 0
        minv = [_INF] * (m + 1)
        used = [False] * (m + 1)
        while True:
            used[j0] = True
            i0 = p[j0]
            delta = _INF
            j1 = 0
            for j in range(1, m + 1):
                if used[j]:
                    continue
                cur = cost[i0][j] - u[i0] - v[j]
                if cur < minv[j]:
                    minv[j] = cur
                    way[j] = j0
                if minv[j] < delta:
                    delta = minv[j]
                    j1 = j
            for j in range(m + 1):
                if used[j]:
                    u[p[j]] += delta
                    v[j] -= delta
                else:
                    minv[j] -= delta
            j0 = j1
            if p[j0] == 0:
                break
        while j0:
            j1 = way[j0]
            p[j0] = p[j1]
            j0 = j1
    return p


def _assign(pairs: list[tuple[float, str, str]]) -> dict[str, str]:
    """Optimal (max-cardinality, then max-IoU) assignment over the viable pairs.

    ``pairs`` are ``(iou, gt_id, cand_id)`` with ``iou >= min_iou``. Cardinality
    dominates weight: every viable pair gets a profit of ``BIG + iou`` with ``BIG``
    larger than any achievable total IoU, so one extra match is always worth more
    than any redistribution of IoU among the rest. Non-viable cells have profit 0 and
    are dropped from the result.
    """
    if not pairs:
        return {}

    gt_ids = sorted({gt_id for _value, gt_id, _cand_id in pairs})
    cand_ids = sorted({cand_id for _value, _gt_id, cand_id in pairs})
    iou_by_pair = {(gt_id, cand_id): value for value, gt_id, cand_id in pairs}

    # Hungarian assigns every row, so rows must be the smaller side. This is also
    # what keeps a wildly asymmetric page cheap (1 candidate vs 1100 GT regions is
    # O(1·1·1100), not O(1100³)) — review finding L2-4, where the old cutoff looked
    # only at the candidate count and the recursion blew the stack.
    transposed = len(cand_ids) < len(gt_ids)
    rows, cols = (cand_ids, gt_ids) if transposed else (gt_ids, cand_ids)
    n, m = len(rows), len(cols)

    big = float(m + 1)  # > any achievable total IoU (each pair contributes <= 1.0)
    cost = [[0.0] * (m + 1) for _ in range(n + 1)]
    for i, row_id in enumerate(rows, start=1):
        for j, col_id in enumerate(cols, start=1):
            key = (col_id, row_id) if transposed else (row_id, col_id)
            value = iou_by_pair.get(key)
            # Minimising cost == maximising profit.
            cost[i][j] = -(big + value) if value is not None else 0.0

    p = _hungarian(cost, n, m)

    out: dict[str, str] = {}
    for j in range(1, m + 1):
        i = p[j]
        if not i:
            continue
        row_id, col_id = rows[i - 1], cols[j - 1]
        gt_id, cand_id = (col_id, row_id) if transposed else (row_id, col_id)
        if (gt_id, cand_id) in iou_by_pair:  # drop the padding (profit-0) cells
            out[gt_id] = cand_id
    return out


def align_regions(
    gt: PageView,
    candidate: PageView,
    *,
    min_iou: float = 0.5,
) -> dict[str, str | None]:
    """Map each GT region id to a candidate region id (or None).

    Pass 1 matches by id-equality. Pass 2 matches the still-unmatched GT regions to
    still-unmatched candidate regions by an optimal assignment over the viable
    (IoU >= ``min_iou``) pairs. Deterministic for fixed inputs; memoised per page
    pair.
    """
    key = (id(gt.raw), id(candidate.raw), min_iou)
    cached = _cache.get(key)
    if cached is not None and cached[0] is gt.raw and cached[1] is candidate.raw:
        return dict(cached[2])

    mapping = _align_uncached(gt, candidate, min_iou=min_iou)

    _cache[key] = (gt.raw, candidate.raw, dict(mapping))
    while len(_cache) > _CACHE_MAXSIZE:
        _cache.popitem(last=False)
    return mapping


def _align_uncached(
    gt: PageView, candidate: PageView, *, min_iou: float
) -> dict[str, str | None]:
    mapping: dict[str, str | None] = {}
    used_candidate_ids: set[str] = set()

    gt_regions = [r for r in gt.regions if r.id]

    # Pass 1: exact id match.
    unmatched_gt: list[RegionView] = []
    for region in gt_regions:
        cand = candidate.region(region.id)
        if cand is not None:
            mapping[region.id] = region.id
            used_candidate_ids.add(region.id)
        else:
            unmatched_gt.append(region)

    # Pass 2: optimal bbox-IoU assignment for whatever is left.
    candidate_pool = [
        c for c in candidate.regions if c.id and c.id not in used_candidate_ids and c.bbox
    ]
    pairs: list[tuple[float, str, str]] = []
    for region in unmatched_gt:
        if region.bbox is None:
            continue
        for cand in candidate_pool:
            assert cand.bbox is not None  # filtered above
            iou = _iou(region.bbox, cand.bbox)
            if iou >= min_iou:
                pairs.append((iou, region.id, cand.id))

    for gt_id, cand_id in _assign(pairs).items():
        mapping[gt_id] = cand_id
        used_candidate_ids.add(cand_id)

    # Any GT region still unmatched is a miss.
    for region in unmatched_gt:
        mapping.setdefault(region.id, None)

    return mapping
