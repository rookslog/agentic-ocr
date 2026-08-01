"""Structural-contract checker: the page must be *referentially* well-formed.

The suite consumes both sides as plain dicts and tolerates malformed input
(:mod:`eval.checkers.pagegt` module docstring). "Tolerate" means *never KeyError
mid-check* — it does **not** mean malformed input scores clean. Before this checker
existed it did (review finding H4 / D-237): a candidate that appended a second
region with an existing ``id`` collapsed through last-wins dictionaries and still
passed all four checkers, and a candidate could pad its ``reading_order`` with ids
that referenced no region of its own. Both are direct reward exploits.

Design call (the RC-3 "your call" clause): this is a **dedicated checker in the
default suite**, not per-checker guards feeding ``CheckResult.crashed``. Two reasons.
(1) ``crashed`` is reserved, by an earlier review finding (D-008), for "the checker
is broken" as opposed to "the candidate is bad" — a candidate with duplicate ids is
squarely the latter, so routing it to ``crashed`` would destroy exactly the
distinction that finding installed. (2) A single checker gives the violation one
stable id, one detail string, and one place to extend, instead of four
near-duplicate guards that could drift apart.

It runs **first** in the default suite so its verdict reads as the precondition for
the others: when it fails, the remaining scores are computed over a page whose ids
do not uniquely denote regions, and should be read accordingly.

Both sides are validated. A malformed *candidate* is a reward exploit; a malformed
*ground truth* is a corpus bug that would otherwise silently shrink what the other
checkers demand — neither should score clean.
"""

from __future__ import annotations

from collections import Counter

from .base import Checker, CheckResult, PageLike
from .pagegt import PageView


def _violations(page: PageLike) -> dict[str, list[str]]:
    """Referential defects of one page, as ``{kind: [offending ids]}`` (sorted)."""
    view = PageView(page)
    # PageView.regions is the *flattened* region list, so a duplicate id introduced
    # by a nested child counts too.
    id_counts = Counter(r.id for r in view.regions if r.id)
    declared = view.declared_reading_order()
    order_counts = Counter(declared)
    known = set(id_counts)
    return {
        "duplicate_region_ids": sorted(i for i, n in id_counts.items() if n > 1),
        "order_refs_no_region": sorted({rid for rid in declared if rid not in known}),
        "duplicate_order_entries": sorted(i for i, n in order_counts.items() if n > 1),
    }


class StructuralContractChecker(Checker):
    """Region ids are unique and every reading-order entry names one, exactly once.

    Fails hard on any of: a repeated region ``id``; a ``reading_order`` entry that
    references no region of that same page; a ``reading_order`` entry that appears
    more than once. Reported as a failing :class:`CheckResult`, never as a raised
    exception — a malformed candidate is a bad candidate, not a broken checker.
    """

    id = "structural-contract"

    _LABELS = {
        "duplicate_region_ids": "duplicate region id(s)",
        "order_refs_no_region": "reading_order entr(ies) referencing no region",
        "duplicate_order_entries": "repeated reading_order entr(ies)",
    }

    def check(self, candidate: PageLike, gt: PageLike) -> CheckResult:
        found = {"candidate": _violations(candidate), "gt": _violations(gt)}

        metrics: dict[str, int] = {}
        problems: list[str] = []
        for side, kinds in found.items():
            for kind, offenders in kinds.items():
                metrics[f"{side}_{kind}"] = len(offenders)
                if offenders:
                    problems.append(f"{side}: {len(offenders)} {self._LABELS[kind]} {offenders}")

        passed = not problems
        detail = (
            "candidate and GT are referentially well-formed "
            "(unique region ids; every reading_order entry names one region, once)"
            if passed
            else "; ".join(problems)
        )
        return self._result(passed=passed, detail=detail, metrics=metrics)
