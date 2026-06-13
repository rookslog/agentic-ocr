"""CLI for the checker suite.

    uv run python -m eval.checkers --gt <gt.json> --candidate <candidate.json>

Loads two PageGT-shaped JSON files, runs the default checker suite, prints the
scorecard, and exits non-zero when any hard check fails — so the same command is a
CI smoke assertion and (later) a reward gate. ``--json`` emits the machine-readable
scorecard instead of the table.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from . import build_default_suite
from .base import run_checkers


def _load(path: Path) -> dict[str, Any]:
    """Load a PageGT-shaped JSON file into a dict."""
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(
            f"{path}: expected a JSON object (PageGT-shaped), got {type(data).__name__}"
        )
    return data


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m eval.checkers",
        description="Score a candidate PageGT against a ground-truth PageGT (deterministic).",
    )
    parser.add_argument(
        "--gt", type=Path, required=True, help="path to the ground-truth PageGT JSON"
    )
    parser.add_argument(
        "--candidate", type=Path, required=True, help="path to the candidate PageGT JSON"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit the machine-readable scorecard instead of a table",
    )
    args = parser.parse_args(argv)

    gt = _load(args.gt)
    candidate = _load(args.candidate)

    scorecard = run_checkers(candidate, gt, build_default_suite())

    if args.json:
        print(json.dumps(scorecard.to_dict(), indent=2, ensure_ascii=False))
    else:
        title = f"Checker scorecard — candidate={args.candidate.name} gt={args.gt.name}"
        print(scorecard.render(title=title))

    return scorecard.exit_code()


if __name__ == "__main__":
    sys.exit(main())
