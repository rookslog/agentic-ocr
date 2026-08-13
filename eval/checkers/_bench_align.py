"""Committed recipe for the KNOWN-OPEN-3 alignment timing table.

    uv run python -m eval.checkers._bench_align

Not a checker and not imported by one — it exists so the timing numbers quoted in
``goal/evidence/checker-suite.md`` can be reproduced rather than taken on trust, and
so a later reader can tell *which shape* was measured. Underscore-prefixed to keep it
out of the package's public surface.

Two shapes, because they cost very different amounts and quoting one number without
naming the shape is how a timing claim becomes misleading:

- ``chain`` — each candidate box overlaps its own GT counterpart and its immediate
  neighbours only. The viable-pair graph is SPARSE (O(n) edges). This is the realistic
  page shape and what the suite's regression tests use.
- ``dense`` — every candidate box overlaps every GT box above the IoU floor, so the
  pair graph is complete (O(n²) edges). This is the worst case the O(n³) assignment
  is unguarded against, and the shape KNOWN-OPEN-3 is actually about.
"""

from __future__ import annotations

import time

from .align import align_regions, reset_cache
from .pagegt import PageView


def chain(n: int) -> tuple[dict, dict]:
    """Sparse: candidate i overlaps GT i strongly and its neighbours weakly."""
    gt = [
        {
            "id": f"g{i:05d}",
            "label": "text_block",
            "text": f"region {i} prose here now",
            "bbox": {"x0": 0.1, "y0": i * 0.5, "x1": 0.9, "y1": i * 0.5 + 1.0},
        }
        for i in range(n)
    ]
    cand = [
        {
            "id": f"c{i:05d}",
            "label": "text_block",
            "text": f"region {i} prose here now",
            "bbox": {"x0": 0.1, "y0": i * 0.5 + 0.02, "x1": 0.9, "y1": i * 0.5 + 1.02},
        }
        for i in range(n)
    ]
    return {"regions": gt}, {"regions": cand}


def dense(n: int) -> tuple[dict, dict]:
    """Complete pair graph: every box overlaps every other well above the floor."""
    box = {"x0": 0.1, "y0": 0.1, "x1": 0.9, "y1": 0.9}
    gt = [
        {"id": f"g{i:05d}", "label": "text_block", "text": "a b c", "bbox": dict(box)}
        for i in range(n)
    ]
    cand = [
        {"id": f"c{i:05d}", "label": "text_block", "text": "a b c", "bbox": dict(box)}
        for i in range(n)
    ]
    return {"regions": gt}, {"regions": cand}


def main() -> None:
    for name, build, sizes in (
        ("chain (sparse)", chain, (100, 200, 400, 600)),
        ("dense (complete graph)", dense, (100, 200, 400, 600)),
    ):
        print(f"{name}:")
        for n in sizes:
            reset_cache()
            gt, cand = build(n)
            gt_view, cand_view = PageView(gt), PageView(cand)
            started = time.perf_counter()
            align_regions(gt_view, cand_view)
            print(f"  n={n:4d}  {time.perf_counter() - started:7.3f}s")


if __name__ == "__main__":
    main()
