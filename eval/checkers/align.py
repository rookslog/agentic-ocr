"""Deterministic alignment of candidate regions to ground-truth regions.

Structure-typing and footnote-anchor integrity both need to know *which* candidate
region corresponds to a given GT region. Two regimes matter:

1. **Fixture-derived candidates (Phase 0).** The candidate reuses the GT region
   ids, so id-equality is an exact, trivially-deterministic alignment. This is the
   path the goal packet's end-to-end fixture run takes.
2. **Real pipeline output (later).** A pipeline invents its own ids, so we fall
   back to maximum bounding-box overlap (IoU). The fallback is greedy by
   descending IoU, and IoU ties break on the *intrinsic* region ids
   (gt id, then candidate id) — never on array position. That last point is
   load-bearing for the reward-signal use: a candidate that merely lists the same
   regions in a different order is semantically identical, so it must produce an
   identical alignment (and identical verdicts). Keying tie-breaks on enumeration
   order would let a reordering of ``regions`` flip a hard verdict — a review
   finding (D-008) this design closes.

The function returns a mapping ``gt_id -> candidate_id | None``. ``None`` means the
GT region has no acceptable counterpart (a miss).
"""

from __future__ import annotations

from .pagegt import PageView, RegionView


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


def align_regions(
    gt: PageView,
    candidate: PageView,
    *,
    min_iou: float = 0.5,
) -> dict[str, str | None]:
    """Map each GT region id to a candidate region id (or None).

    Pass 1 matches by id-equality. Pass 2 matches the still-unmatched GT regions
    to still-unmatched candidate regions by descending bbox IoU (>= ``min_iou``),
    with deterministic tie-breaks. Deterministic for fixed inputs.
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

    # Pass 2: greedy bbox IoU for whatever is left.
    candidate_pool = [
        c for c in candidate.regions if c.id and c.id not in used_candidate_ids and c.bbox
    ]
    # Build all viable (iou, gt_id, cand_id) pairs, then assign greedily by
    # descending IoU. Ties break on the intrinsic ids (gt id, then candidate id),
    # NOT on enumeration/array order, so reordering the candidate's `regions` list
    # cannot change the alignment (review finding D-008: array-order tie-breaks
    # made a semantics-preserving permutation flip hard verdicts).
    scored: list[tuple[float, str, str]] = []
    for region in unmatched_gt:
        if region.bbox is None:
            continue
        for cand in candidate_pool:
            assert cand.bbox is not None  # filtered above
            iou = _iou(region.bbox, cand.bbox)
            if iou >= min_iou:
                # Negative iou as primary key so ascending sort == descending IoU.
                scored.append((-iou, region.id, cand.id))
    scored.sort()

    assigned_gt: set[str] = set()
    for _neg_iou, gt_id, cand_id in scored:
        if gt_id in assigned_gt or cand_id in used_candidate_ids:
            continue
        mapping[gt_id] = cand_id
        assigned_gt.add(gt_id)
        used_candidate_ids.add(cand_id)

    # Any GT region still unmatched is a miss.
    for region in unmatched_gt:
        mapping.setdefault(region.id, None)

    return mapping
