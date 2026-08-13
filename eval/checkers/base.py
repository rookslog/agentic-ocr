"""The checker contract: CheckResult, Checker, and the Scorecard runner.

This is the olmOCR-2 "unit-test rewards" pattern (PLAN §5), made into a small,
deterministic interface:

- A **checker** takes a candidate pipeline output and a ground-truth page (both
  ``PageGT``-shaped mappings) and returns exactly one :class:`CheckResult`.
- A **runner** (:func:`run_checkers`) applies a sequence of checkers and
  aggregates the verdicts into a :class:`Scorecard` whose exit code is usable as a
  CI assertion today and as a reward signal later.

Determinism is the load-bearing property (goal packet: *same inputs, same
verdicts*). Every checker here is a pure function of its two inputs — no clock, no
randomness, no model call, no I/O. The runner sorts nothing it is given and
preserves checker order, so a fixed checker list yields a byte-stable scorecard.

Severity drives the exit code:

- ``"hard"`` — a failure that must fail the build / zero the reward. Any failing
  hard check makes :meth:`Scorecard.exit_code` non-zero.
- ``"soft"`` — a failure worth reporting that does not, on its own, fail the run.
- ``"info"`` — diagnostic only; never affects the exit code.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, ClassVar, Literal

from tabulate import tabulate

# A PageGT-shaped mapping (parsed JSON). See eval/checkers/pagegt.py for accessors.
PageLike = Mapping[str, Any]

Severity = Literal["hard", "soft", "info"]

# Values a checker may put in CheckResult.metrics — kept JSON-serialisable so the
# scorecard can be emitted as machine-readable reward telemetry.
MetricValue = float | int | str | bool


@dataclass(frozen=True)
class CheckResult:
    """The verdict of a single checker over (candidate, ground-truth).

    Attributes:
        id: Stable checker identifier (e.g. ``"text-fidelity"``). Stable across
            runs so downstream tooling can key on it.
        passed: Whether the check succeeded.
        severity: ``"hard"`` | ``"soft"`` | ``"info"`` — governs the exit code.
        detail: Human-readable, single-paragraph explanation of the verdict.
        metrics: Optional structured numbers/strings backing the verdict, for the
            (later) reward signal and for debugging. JSON-serialisable.
    """

    id: str
    passed: bool
    severity: Severity
    detail: str
    metrics: Mapping[str, MetricValue] = field(default_factory=dict)

    @property
    def is_hard_failure(self) -> bool:
        """A failing check whose severity makes the whole run fail."""
        return self.severity == "hard" and not self.passed

    def to_dict(self) -> dict[str, Any]:
        """JSON-serialisable form (for ``--json`` output and evidence)."""
        return {
            "id": self.id,
            "passed": self.passed,
            "severity": self.severity,
            "detail": self.detail,
            "metrics": dict(self.metrics),
        }


class Checker(ABC):
    """Base class for a deterministic checker.

    A concrete checker sets the class variable :attr:`id` and implements
    :meth:`check`. Severity defaults to :attr:`default_severity` but can be
    overridden per instance (so the same checker can gate hard in CI and report
    soft in an exploratory run). Instances are callable.

    Implementations MUST be pure functions of ``(candidate, gt)``: no clock, no
    randomness, no model, no I/O. A checker that needs any of those does not
    belong in this suite (goal packet: escalate to the experiments track).
    """

    id: ClassVar[str]
    default_severity: ClassVar[Severity] = "hard"

    def __init__(self, *, severity: Severity | None = None) -> None:
        self.severity: Severity = severity if severity is not None else self.default_severity

    @abstractmethod
    def check(self, candidate: PageLike, gt: PageLike) -> CheckResult:
        """Score ``candidate`` against ground-truth ``gt``; return one verdict."""

    def __call__(self, candidate: PageLike, gt: PageLike) -> CheckResult:
        return self.check(candidate, gt)

    def _result(
        self,
        *,
        passed: bool,
        detail: str,
        metrics: Mapping[str, MetricValue] | None = None,
    ) -> CheckResult:
        """Build a CheckResult carrying this checker's id and severity."""
        return CheckResult(
            id=self.id,
            passed=passed,
            severity=self.severity,
            detail=detail,
            metrics=dict(metrics) if metrics else {},
        )


class AlwaysPassChecker(Checker):
    """Trivial checker that always passes — wires the contract end-to-end.

    Exists so the contract (checker → CheckResult → runner → Scorecard → exit
    code) can be exercised under pytest before any real checker is written
    (goal packet Milestone 1). Severity defaults to ``"info"`` so it never
    influences an exit code.
    """

    id = "always-pass"
    default_severity = "info"

    def check(self, candidate: PageLike, gt: PageLike) -> CheckResult:
        return self._result(passed=True, detail="trivial always-pass checker")


@dataclass(frozen=True)
class Scorecard:
    """Aggregated verdicts from a checker run.

    Order of :attr:`results` mirrors the order checkers were supplied to
    :func:`run_checkers`, so a fixed checker list yields a stable scorecard.
    """

    results: Sequence[CheckResult]

    @property
    def hard_failures(self) -> list[CheckResult]:
        """Failing checks whose severity is ``"hard"``."""
        return [r for r in self.results if r.is_hard_failure]

    @property
    def soft_failures(self) -> list[CheckResult]:
        """Failing checks whose severity is ``"soft"``."""
        return [r for r in self.results if r.severity == "soft" and not r.passed]

    @property
    def crashed(self) -> list[CheckResult]:
        """Results produced by a checker that raised (runner-captured crashes).

        Distinct from a legitimate hard FAIL: a non-empty list means a checker is
        *broken*, not that the candidate is bad. CI asserts this is empty on a
        clean fixture run.
        """
        return [r for r in self.results if r.metrics.get("crashed") is True]

    @property
    def passed(self) -> bool:
        """True iff there are no hard failures (the CI / reward gate)."""
        return not self.hard_failures

    def exit_code(self) -> int:
        """0 when all hard checks pass, 1 otherwise — usable as a CI assertion."""
        return 0 if self.passed else 1

    def to_dict(self) -> dict[str, Any]:
        """JSON-serialisable scorecard (for ``--json`` and evidence files)."""
        return {
            "passed": self.passed,
            "exit_code": self.exit_code(),
            "summary": {
                "total": len(self.results),
                "passed": sum(1 for r in self.results if r.passed),
                "hard_failures": len(self.hard_failures),
                "soft_failures": len(self.soft_failures),
                "crashed": len(self.crashed),
            },
            "results": [r.to_dict() for r in self.results],
        }

    def render(self, title: str = "Checker scorecard") -> str:
        """Render a terminal-friendly table plus a one-line summary."""
        rows = []
        for r in self.results:
            verdict = "PASS" if r.passed else "FAIL"
            rows.append([r.id, r.severity, verdict, r.detail])
        table = tabulate(
            rows,
            headers=["checker", "severity", "verdict", "detail"],
            tablefmt="simple",
        )
        n_pass = sum(1 for r in self.results if r.passed)
        summary = (
            f"{n_pass}/{len(self.results)} passed · "
            f"{len(self.hard_failures)} hard failure(s) · "
            f"{len(self.soft_failures)} soft failure(s) · "
            f"exit {self.exit_code()}"
        )
        return f"{title}\n{'=' * len(title)}\n{table}\n\n{summary}"


def run_checkers(
    candidate: PageLike,
    gt: PageLike,
    checkers: Sequence[Checker],
) -> Scorecard:
    """Apply ``checkers`` to ``(candidate, gt)`` and aggregate into a Scorecard.

    A checker that raises is not allowed to abort the whole run: the exception is
    captured as a *failing hard* :class:`CheckResult` (a crashing checker is a
    failed assertion, never a green build). This keeps the runner robust to a
    malformed candidate that trips an individual checker. Checker order is
    preserved.

    A captured crash is tagged ``metrics["crashed"] = True`` to keep it distinct
    from a checker's *legitimate* hard FAIL (review finding D-008): when these exit
    codes feed a reward signal, "the checker is broken" and "the candidate is bad"
    must be distinguishable, so CI can assert that a clean fixture run produces zero
    crashed results rather than letting a checker bug train the policy as ordinary
    reward. Use :meth:`Scorecard.crashed` to detect them.
    """
    results: list[CheckResult] = []
    for checker in checkers:
        try:
            results.append(checker(candidate, gt))
        except Exception as exc:  # noqa: BLE001 — a crashing checker is a hard failure
            results.append(
                CheckResult(
                    id=getattr(checker, "id", checker.__class__.__name__),
                    passed=False,
                    severity="hard",
                    detail=f"checker raised {type(exc).__name__}: {exc}",
                    metrics={"crashed": True, "error": type(exc).__name__},
                )
            )
    return Scorecard(results=results)
