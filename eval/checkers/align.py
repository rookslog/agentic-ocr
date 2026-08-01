"""Deterministic alignment of candidate regions to ground-truth regions.

Structure-typing and footnote-anchor integrity both need to know *which* candidate
region corresponds to a given GT region. Two regimes matter:

1. **Fixture-derived candidates (Phase 0).** The candidate reuses the GT region
   ids, so id-equality is an exact, trivially-deterministic alignment. This is the
   path the goal packet's end-to-end fixture run takes.
2. **Real pipeline output (later).** A pipeline invents its own ids, so we fall
   back to bounding-box overlap (IoU). The fallback is an **optimal** assignment
   over the viable-pair graph — maximise the number of matched GT regions first,
   then total IoU — not a greedy descending-IoU scan. Greedy was a review finding
   (M6 / D-237): with viable IoUs A-X=.905, A-Y=.700, B-X=.600 it takes A-X and
   leaves B unmatched, though A-Y + B-X matches both; the spurious miss then
   false-fails footnote-anchor and structure-typing on an honest candidate.
   IoU ties break on the *intrinsic* region ids (gt id, then candidate id) — never
   on array position. That last point is load-bearing for the reward-signal use: a
   candidate that merely lists the same regions in a different order is semantically
   identical, so it must produce an identical alignment (and identical verdicts).
   Keying tie-breaks on enumeration order would let a reordering of ``regions`` flip
   a hard verdict — a review finding (D-008) this design closes.

The function returns a mapping ``gt_id -> candidate_id | None``. ``None`` means the
GT region has no acceptable counterpart (a miss).
"""

from __future__ import annotations

from .pagegt import PageView, RegionView

# Exact assignment is exponential in the size of a connected component of the
# viable-pair graph. Page-scale components are tiny (a handful of mutually
# overlapping regions), but a pathological page — hundreds of near-identical
# boxes — must not hang a suite whose contract is "deterministic and cheap". Above
# this many candidate nodes in one component we fall back to the greedy rule: a
# strictly worse assignment, still deterministic, never slow. No component in the
# committed fixtures comes near it.
_MAX_EXACT_COMPONENT_CANDIDATES = 16


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


def _components(
    pairs: list[tuple[float, str, str]],
) -> list[tuple[list[str], list[str]]]:
    """Split the viable-pair graph into connected components.

    Returns ``[(gt_ids, cand_ids), ...]``, each id list sorted, and the component
    list sorted by its first GT id — all order determined by intrinsic ids, never
    by array position.
    """
    parent: dict[str, str] = {}

    def find(node: str) -> str:
        parent.setdefault(node, node)
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)

    for _iou, gt_id, cand_id in pairs:
        union(f"g:{gt_id}", f"c:{cand_id}")

    groups: dict[str, tuple[set[str], set[str]]] = {}
    for node in sorted(parent):
        root = find(node)
        gts, cands = groups.setdefault(root, (set(), set()))
        (gts if node.startswith("g:") else cands).add(node[2:])
    return [
        (sorted(gts), sorted(cands))
        for _root, (gts, cands) in sorted(groups.items(), key=lambda kv: sorted(kv[1][0]))
    ]


def _greedy(
    pairs: list[tuple[float, str, str]], gt_ids: list[str], cand_ids: list[str]
) -> dict[str, str]:
    """Descending-IoU greedy assignment (the >_MAX_EXACT_COMPONENT_CANDIDATES path)."""
    allowed_gt, allowed_cand = set(gt_ids), set(cand_ids)
    scored = sorted(
        (-iou, g, c) for iou, g, c in pairs if g in allowed_gt and c in allowed_cand
    )
    out: dict[str, str] = {}
    used: set[str] = set()
    for _neg_iou, gt_id, cand_id in scored:
        if gt_id in out or cand_id in used:
            continue
        out[gt_id] = cand_id
        used.add(cand_id)
    return out


def _exact(
    pairs: list[tuple[float, str, str]], gt_ids: list[str], cand_ids: list[str]
) -> dict[str, str]:
    """Maximise (matched-pair count, total IoU) over one component, exactly.

    Deterministic: GT nodes are visited in sorted-id order, each GT node's options
    are tried in ``(-iou, cand_id)`` order, and an option only displaces the
    incumbent on a *strict* improvement — so ties resolve to the highest-IoU,
    lowest-id option at the earliest GT id. No enumeration order enters the result.
    """
    options: dict[str, list[tuple[float, str]]] = {g: [] for g in gt_ids}
    allowed_cand = set(cand_ids)
    for iou, gt_id, cand_id in pairs:
        if gt_id in options and cand_id in allowed_cand:
            options[gt_id].append((iou, cand_id))
    for gt_id in options:
        options[gt_id].sort(key=lambda t: (-t[0], t[1]))

    bit_of = {cand_id: 1 << i for i, cand_id in enumerate(cand_ids)}
    n = len(gt_ids)
    memo: dict[tuple[int, int], tuple[int, float, tuple[tuple[str, str], ...]]] = {}

    def best(i: int, mask: int) -> tuple[int, float, tuple[tuple[str, str], ...]]:
        if i == n:
            return (0, 0.0, ())
        key = (i, mask)
        cached = memo.get(key)
        if cached is not None:
            return cached
        incumbent = best(i + 1, mask)  # option: leave this GT region unmatched
        for iou, cand_id in options[gt_ids[i]]:
            bit = bit_of[cand_id]
            if mask & bit:
                continue
            count, weight, choice = best(i + 1, mask | bit)
            challenger = (count + 1, weight + iou, ((gt_ids[i], cand_id), *choice))
            if (challenger[0], challenger[1]) > (incumbent[0], incumbent[1]):
                incumbent = challenger
        memo[key] = incumbent
        return incumbent

    return dict(best(0, 0)[2])


def align_regions(
    gt: PageView,
    candidate: PageView,
    *,
    min_iou: float = 0.5,
) -> dict[str, str | None]:
    """Map each GT region id to a candidate region id (or None).

    Pass 1 matches by id-equality. Pass 2 matches the still-unmatched GT regions
    to still-unmatched candidate regions by an *optimal* assignment over the viable
    (IoU >= ``min_iou``) pairs, with deterministic tie-breaks. Deterministic for
    fixed inputs.
    """
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
    # Build all viable (iou, gt_id, cand_id) pairs. Ties break on the intrinsic ids
    # (gt id, then candidate id), NOT on enumeration/array order, so reordering the
    # candidate's `regions` list cannot change the alignment (review finding D-008:
    # array-order tie-breaks made a semantics-preserving permutation flip hard
    # verdicts).
    pairs: list[tuple[float, str, str]] = []
    for region in unmatched_gt:
        if region.bbox is None:
            continue
        for cand in candidate_pool:
            assert cand.bbox is not None  # filtered above
            iou = _iou(region.bbox, cand.bbox)
            if iou >= min_iou:
                pairs.append((iou, region.id, cand.id))

    for gt_ids, cand_ids in _components(pairs):
        if len(cand_ids) > _MAX_EXACT_COMPONENT_CANDIDATES:
            chosen = _greedy(pairs, gt_ids, cand_ids)
        else:
            chosen = _exact(pairs, gt_ids, cand_ids)
        for gt_id, cand_id in chosen.items():
            mapping[gt_id] = cand_id
            used_candidate_ids.add(cand_id)

    # Any GT region still unmatched is a miss.
    for region in unmatched_gt:
        mapping.setdefault(region.id, None)

    return mapping
