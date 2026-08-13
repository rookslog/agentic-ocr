"""Deterministic, unit-test-style checker suite (PLAN §5 / Phase-0 gate item 5).

A *checker* scores a candidate pipeline output against a ground-truth page and
returns a :class:`CheckResult`; the :func:`run_checkers` runner aggregates verdicts
into a :class:`Scorecard` whose exit code is a CI assertion today and a reward
signal later (olmOCR-2 "unit-test rewards" pattern). Every checker is a pure,
deterministic function of ``(candidate, gt)`` — no model, no clock, no randomness.

Public surface:

- Contract: :class:`CheckResult`, :class:`Checker`, :class:`Scorecard`,
  :func:`run_checkers`, :class:`AlwaysPassChecker`.
- Core checkers: :class:`StructuralContractChecker`, :class:`TextFidelityChecker`,
  :class:`ReadingOrderChecker`, :class:`FootnoteAnchorChecker`,
  :class:`StructureTypingChecker`.
- :func:`build_default_suite` — the canonical hard-gating checker list used by the
  CLI and CI smoke run.

CLI entry point: ``uv run python -m eval.checkers --gt <gt.json> --candidate <cand.json>``.
"""

from __future__ import annotations

from .base import (
    AlwaysPassChecker,
    Checker,
    CheckResult,
    PageLike,
    Scorecard,
    Severity,
    run_checkers,
)
from .contract import StructuralContractChecker
from .footnote_anchor import FootnoteAnchorChecker
from .reading_order import ReadingOrderChecker
from .structure_typing import StructureTypingChecker
from .text_fidelity import TextFidelityChecker


def build_default_suite() -> list[Checker]:
    """The canonical checker list: structural contract + the four core checkers.

    All hard-gating. The structural-contract checker runs first: it is the
    precondition the other four assume (unique region ids, reading-order entries
    that name real regions — review finding H4 / D-237), so its verdict should be
    read before theirs.

    Returned fresh each call (checkers are cheap, stateless instances) so callers
    can reconfigure without mutating shared state. Order is stable, so the
    scorecard it produces is byte-stable for fixed inputs.
    """
    return [
        StructuralContractChecker(),
        TextFidelityChecker(),
        ReadingOrderChecker(),
        FootnoteAnchorChecker(),
        StructureTypingChecker(),
    ]


__all__ = [
    # contract
    "CheckResult",
    "Checker",
    "Scorecard",
    "Severity",
    "PageLike",
    "run_checkers",
    "AlwaysPassChecker",
    # core checkers
    "StructuralContractChecker",
    "TextFidelityChecker",
    "ReadingOrderChecker",
    "FootnoteAnchorChecker",
    "StructureTypingChecker",
    # suite
    "build_default_suite",
]
