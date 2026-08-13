"""Anchor-based GT-B aligner + mechanical alignment-coverage statistic.

Implements PLAN.md:139 ("Anchor-based alignment (unique shared n-grams as
anchors, dynamic-programming fill between) ... Edition mismatch is detected
mechanically by alignment-coverage statistics — low coverage => pair rejected,
no human judgment needed"). Three stages, all deterministic:

W2 review established that the statistic is mechanically computable but GT
recall alone is not sufficient pair certification; the limitation is explicit
in stage 3 and the evidence document.

1. **Anchor extraction** (:func:`unique_shared_anchors`) — word n-grams that occur
   *exactly once* in BOTH token streams are candidate anchors; their (gt_pos,
   cand_pos) coordinates are made strictly monotonic with a longest-increasing-
   subsequence (LIS) filter, then made span-disjoint in both streams. The latter
   constraint prevents overlapping candidate windows from being reused to explain
   disjoint GT spans.

2. **DP fill** (:func:`_segment_lcs_match`) — between two consecutive anchors the
   GT and candidate sub-segments are aligned by an LCS dynamic program over
   tokens; the LCS length is the count of GT tokens recovered in that gap. Anchor
   tokens themselves count as matched. Segments larger than ``max_gap`` tokens are
   treated as unalignable (0 matched) so a single runaway gap (edition divergence)
   cannot blow up the DP cost while still (correctly) depressing coverage.

3. **Coverage statistic + provisional recall gate** (:func:`align`) —
   ``coverage = matched_gt_tokens / total_gt_tokens`` in [0, 1]. The legacy
   ``accepted`` flag is true iff there is anchor evidence and
   ``coverage >= ACCEPT_THRESHOLD``. The recorded smoke
   brackets the threshold with three high-recall candidates and two unrelated
   controls. It does not establish that recall alone certifies edition identity:
   compound or substantially reordered candidates remain an open contract decision
   documented in ``goal/evidence/gtb-aligner.md``.

Coverage schema (decision, not invention): the denominator is the *GT* (EPUB)
token count — the born-digital edition is the reference we want to recover from
the scan, so "what fraction of the trusted text did the scan-side stream let us
align" is the meaningful quantity (it is the recall direction the OG smoke's
0.904 measured, made anchor-local instead of bag-of-n-grams). It is bounded and 0
for disjoint texts. The hard ``MAX_GAP`` runtime cap makes it a conservative lower
bound with a discontinuity at the cap, not a globally monotone quality metric.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from eval.checkers._normalize import ngrams, tokens

# ── Recorded operating parameters (see limits in goal/evidence/gtb-aligner.md) ────────────
ANCHOR_N = 5
"""N-gram order for anchors. Long enough that a unique 5-gram is near-certainly a
true textual correspondence, not a coincidence; short enough that real shared
prose yields thousands of them. (Calibration probed n in {3,4,5}; see evidence.)"""

MAX_GAP = 4000
"""Max GT (or candidate) sub-segment length, in tokens, that the LCS DP will fill
between two consecutive anchors. Bounds the DP at O(max_gap^2) per gap so the
overall run stays linear-ish in anchor count. Gaps above this are scored as
0 matched (their GT tokens still count in the denominator)."""

ACCEPT_THRESHOLD = 0.60
"""Recall threshold separating the recorded candidates from unrelated controls.

It is not calibrated against near-boundary same-work, compound, abridged, or
reordered hard negatives. See ``goal/evidence/gtb-aligner.md``.
"""


@dataclass(frozen=True)
class Anchor:
    """One monotone alignment anchor: a unique-shared n-gram and its token positions."""

    gt_pos: int
    cand_pos: int
    ngram: tuple[str, ...]


@dataclass(frozen=True)
class AlignmentResult:
    """Outcome of aligning a GT token stream to a candidate token stream."""

    coverage: float
    accepted: bool
    threshold: float
    gt_tokens: int
    cand_tokens: int
    matched_gt_tokens: int
    n_anchors: int
    anchor_n: int
    detail: dict[str, float] = field(default_factory=dict)


def _unique_positions(grams: list[tuple[str, ...]]) -> dict[tuple[str, ...], int]:
    """Map each n-gram that occurs *exactly once* to its (token) start index."""
    first: dict[tuple[str, ...], int] = {}
    seen_multiple: set[tuple[str, ...]] = set()
    for i, g in enumerate(grams):
        if g in seen_multiple:
            continue
        if g in first:
            del first[g]
            seen_multiple.add(g)
        else:
            first[g] = i
    return first


def _lis_indices(seq: list[int]) -> list[int]:
    """Indices of a longest strictly-increasing subsequence of ``seq`` (patience sort).

    Deterministic: ties resolved by leftmost binary-search insertion, giving a
    canonical LIS. Used to keep only a monotonically-consistent set of anchors.
    """
    import bisect

    tails: list[int] = []  # tails[k] = seq value ending an increasing subseq of len k+1
    tails_idx: list[int] = []  # index in seq of that tail value
    prev: list[int] = [-1] * len(seq)
    for i, x in enumerate(seq):
        pos = bisect.bisect_left(tails, x)
        if pos == len(tails):
            tails.append(x)
            tails_idx.append(i)
        else:
            tails[pos] = x
            tails_idx[pos] = i
        prev[i] = tails_idx[pos - 1] if pos > 0 else -1
    if not tails_idx:
        return []
    result: list[int] = []
    k = tails_idx[-1]
    while k != -1:
        result.append(k)
        k = prev[k]
    result.reverse()
    return result


def unique_shared_anchors(
    gt_tokens: list[str], cand_tokens: list[str], n: int = ANCHOR_N
) -> list[Anchor]:
    """Unique-shared n-gram anchors, filtered to a strictly-monotone chain.

    A candidate anchor is an n-gram occurring exactly once in *both* token
    streams. Candidates are sorted by GT position; an LIS on their candidate
    positions drops any that would require a non-monotone (crossed) alignment.
    Sliding n-grams overlap, so a final greedy pass retains a deterministic chain
    whose spans are non-overlapping on *both* sides. Without that interval
    constraint, the same candidate tokens can explain multiple disjoint GT spans.
    """
    if type(n) is not int or n < 1:
        raise ValueError("n must be a positive integer")
    gt_grams = ngrams(gt_tokens, n)
    cand_grams = ngrams(cand_tokens, n)
    gt_unique = _unique_positions(gt_grams)
    cand_unique = _unique_positions(cand_grams)

    shared = [
        (gt_pos, cand_unique[g], g)
        for g, gt_pos in gt_unique.items()
        if g in cand_unique
    ]
    shared.sort(key=lambda t: (t[0], t[1]))
    if not shared:
        return []

    cand_positions = [c for _, c, _ in shared]
    keep = _lis_indices(cand_positions)
    monotone = [
        Anchor(gt_pos=shared[i][0], cand_pos=shared[i][1], ngram=shared[i][2])
        for i in keep
    ]
    non_overlapping: list[Anchor] = []
    for anchor in monotone:
        if not non_overlapping:
            non_overlapping.append(anchor)
            continue
        previous = non_overlapping[-1]
        if anchor.gt_pos >= previous.gt_pos + n and anchor.cand_pos >= previous.cand_pos + n:
            non_overlapping.append(anchor)
    return non_overlapping


def _lcs_length(a: list[str], b: list[str]) -> int:
    """Length of a longest common subsequence of token lists ``a`` and ``b``.

    Hirschberg-free, O(len(a)*len(b)) time and O(min) space. Callers bound the
    inputs via ``MAX_GAP`` so this stays cheap per gap.
    """
    if not a or not b:
        return 0
    if len(a) < len(b):
        a, b = b, a
    prev = [0] * (len(b) + 1)
    for x in a:
        upper_left = 0
        row = prev
        new = [0] * (len(b) + 1)
        for j, y in enumerate(b, start=1):
            if x == y:
                new[j] = upper_left + 1
            else:
                new[j] = row[j] if row[j] >= new[j - 1] else new[j - 1]
            upper_left = row[j]
        prev = new
    return prev[len(b)]


def _segment_lcs_match(gt_seg: list[str], cand_seg: list[str], max_gap: int) -> int:
    """GT tokens recovered in one inter-anchor gap, via bounded LCS.

    Returns 0 when either segment exceeds ``max_gap`` (treated as unalignable so a
    single divergent gap cannot dominate runtime), else the LCS length.
    """
    if not gt_seg:
        return 0
    if len(gt_seg) > max_gap or len(cand_seg) > max_gap:
        return 0
    return _lcs_length(gt_seg, cand_seg)


def align_tokens(
    gt_tokens: list[str],
    cand_tokens: list[str],
    *,
    n: int = ANCHOR_N,
    max_gap: int = MAX_GAP,
    threshold: float = ACCEPT_THRESHOLD,
) -> AlignmentResult:
    """Align two *token streams* and compute coverage + verdict.

    Pipeline: unique-shared, monotone, span-disjoint n-gram anchors -> bounded LCS
    DP fill in each inter-anchor gap -> coverage = matched_gt_tokens /
    total_gt_tokens. Anchor tokens count as matched. A non-empty anchor chain and
    ``coverage >= threshold`` set the legacy ``accepted`` recall-gate flag; see the
    module-level contract limitation before treating that flag as pair certification.
    """
    if type(n) is not int or n < 1:
        raise ValueError("n must be a positive integer")
    if type(max_gap) is not int or max_gap < 0:
        raise ValueError("max_gap must be a non-negative integer")
    if not math.isfinite(threshold) or not 0.0 < threshold <= 1.0:
        raise ValueError("threshold must be finite and in (0, 1]")

    total_gt = len(gt_tokens)
    if total_gt == 0:
        return AlignmentResult(
            coverage=0.0,
            accepted=False,
            threshold=threshold,
            gt_tokens=0,
            cand_tokens=len(cand_tokens),
            matched_gt_tokens=0,
            n_anchors=0,
            anchor_n=n,
            detail={"reason_empty_gt": 1.0},
        )

    anchors = unique_shared_anchors(gt_tokens, cand_tokens, n)

    # Coverage counts *distinct* GT token indices explained, never double-counting.
    # Anchor n-gram spans [gt_pos, gt_pos+n) are covered by construction; the GT
    # region strictly *after* the previous covered end and *before* the next anchor
    # is LCS-filled against the matching candidate region. Anchors are monotone and
    # span-disjoint in both coordinates, so the concatenated anchor and gap matches
    # form an injective common subsequence rather than reusing candidate tokens.
    anchor_tokens = 0
    gap_tokens = 0
    prev_gt_end = 0  # exclusive end of last covered GT region
    prev_cand_end = 0
    for a in anchors:
        # LCS-fill the GT region strictly before this anchor.
        if a.gt_pos > prev_gt_end:
            gt_seg = gt_tokens[prev_gt_end : a.gt_pos]
            cand_seg = (
                cand_tokens[prev_cand_end : a.cand_pos] if a.cand_pos > prev_cand_end else []
            )
            gap_tokens += _segment_lcs_match(gt_seg, cand_seg, max_gap)
        # Anchor span is exactly [a.gt_pos, a.gt_pos + n). We do NOT credit the gap
        # region [prev_gt_end, a.gt_pos) here — that region is only ever credited by
        # the LCS fill above, so a large unmatched gap stays uncovered.
        span_start = max(prev_gt_end, a.gt_pos)
        new_end = a.gt_pos + n
        if new_end > span_start:
            anchor_tokens += new_end - span_start
        prev_gt_end = max(prev_gt_end, new_end)
        prev_cand_end = max(prev_cand_end, a.cand_pos + n)

    # Tail gap after the last anchor.
    if total_gt > prev_gt_end:
        tail_gt = gt_tokens[prev_gt_end:]
        tail_cand = cand_tokens[prev_cand_end:]
        gap_tokens += _segment_lcs_match(tail_gt, tail_cand, max_gap)

    matched = anchor_tokens + gap_tokens
    matched = min(matched, total_gt)  # numerical guard against any residual overlap
    coverage = matched / total_gt
    detail = {
        "anchor_token_fraction": anchor_tokens / total_gt,
        "gap_token_fraction": gap_tokens / total_gt,
        "candidate_coverage": matched / len(cand_tokens) if cand_tokens else 0.0,
        "candidate_to_gt_length_ratio": len(cand_tokens) / total_gt,
    }
    if not anchors:
        detail["reason_no_anchors"] = 1.0
    return AlignmentResult(
        coverage=coverage,
        # This is an anchor-based alignment. An anchorless LCS score is useful as
        # a diagnostic but is not evidence that a whole-book pair was placed.
        accepted=bool(anchors) and coverage >= threshold,
        threshold=threshold,
        gt_tokens=total_gt,
        cand_tokens=len(cand_tokens),
        matched_gt_tokens=matched,
        n_anchors=len(anchors),
        anchor_n=n,
        detail=detail,
    )


def align(
    gt_text: str,
    cand_text: str,
    *,
    n: int = ANCHOR_N,
    max_gap: int = MAX_GAP,
    threshold: float = ACCEPT_THRESHOLD,
) -> AlignmentResult:
    """Align GT (EPUB) text against candidate (PDF) text; compute coverage + verdict.

    Normalizes/tokenizes both sides with ``eval.checkers._normalize.tokens`` (the
    same primitive the checker suite and OG smoke use), then delegates to
    :func:`align_tokens`.
    """
    return align_tokens(
        tokens(gt_text),
        tokens(cand_text),
        n=n,
        max_gap=max_gap,
        threshold=threshold,
    )
