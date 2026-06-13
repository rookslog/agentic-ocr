"""Milestone 1: the checker contract and runner.

A checker takes (candidate, GT) and returns CheckResult{id, passed, severity,
detail}; the runner aggregates to a Scorecard with an exit code. These tests pin
the contract via the trivial always-pass checker and a couple of synthetic
checkers, before any real checker is involved.
"""

from __future__ import annotations

from eval.checkers import (
    AlwaysPassChecker,
    Checker,
    CheckResult,
    Scorecard,
    build_default_suite,
    run_checkers,
)
from eval.checkers.base import PageLike


class _AlwaysFailHard(Checker):
    id = "always-fail-hard"
    default_severity = "hard"

    def check(self, candidate: PageLike, gt: PageLike) -> CheckResult:
        return self._result(passed=False, detail="deliberately fails")


class _AlwaysFailSoft(Checker):
    id = "always-fail-soft"
    default_severity = "soft"

    def check(self, candidate: PageLike, gt: PageLike) -> CheckResult:
        return self._result(passed=False, detail="soft failure")


class _Raises(Checker):
    id = "raiser"

    def check(self, candidate: PageLike, gt: PageLike) -> CheckResult:
        raise RuntimeError("boom")


def test_check_result_fields_and_severity():
    r = CheckResult(id="x", passed=False, severity="hard", detail="d")
    assert r.id == "x"
    assert r.passed is False
    assert r.severity == "hard"
    assert r.is_hard_failure is True
    assert r.to_dict()["metrics"] == {}


def test_always_pass_checker_is_info_and_passes():
    result = AlwaysPassChecker()({}, {})
    assert result.id == "always-pass"
    assert result.passed is True
    assert result.severity == "info"
    assert result.is_hard_failure is False


def test_runner_all_pass_exit_zero():
    card = run_checkers({}, {}, [AlwaysPassChecker()])
    assert isinstance(card, Scorecard)
    assert card.passed is True
    assert card.exit_code() == 0
    assert card.hard_failures == []


def test_runner_hard_failure_exit_nonzero():
    card = run_checkers({}, {}, [AlwaysPassChecker(), _AlwaysFailHard()])
    assert card.passed is False
    assert card.exit_code() == 1
    assert [r.id for r in card.hard_failures] == ["always-fail-hard"]


def test_runner_soft_failure_does_not_fail_exit():
    card = run_checkers({}, {}, [_AlwaysFailSoft()])
    assert card.passed is True
    assert card.exit_code() == 0
    assert [r.id for r in card.soft_failures] == ["always-fail-soft"]


def test_runner_captures_exceptions_as_hard_failures():
    card = run_checkers({}, {}, [_Raises()])
    assert card.exit_code() == 1
    assert card.results[0].id == "raiser"
    assert "boom" in card.results[0].detail


def test_crash_is_tagged_distinctly_from_legitimate_hard_failure():
    # Review finding D-008: a checker crash must be distinguishable from a candidate's
    # legitimate hard FAIL, so a checker bug can't silently train a reward policy.
    card = run_checkers({}, {}, [_AlwaysFailHard(), _Raises()])
    assert card.crashed == [card.results[1]]  # only the raiser crashed
    assert card.results[0] not in card.crashed  # a legitimate FAIL is not a crash
    assert card.to_dict()["summary"]["crashed"] == 1


def test_severity_override_per_instance():
    checker = _AlwaysFailHard(severity="soft")
    card = run_checkers({}, {}, [checker])
    assert card.exit_code() == 0  # downgraded to soft


def test_scorecard_order_is_preserved():
    checkers = [AlwaysPassChecker(), _AlwaysFailSoft(), _AlwaysFailHard()]
    card = run_checkers({}, {}, checkers)
    assert [r.id for r in card.results] == [
        "always-pass",
        "always-fail-soft",
        "always-fail-hard",
    ]


def test_scorecard_render_and_to_dict():
    card = run_checkers({}, {}, [AlwaysPassChecker(), _AlwaysFailHard()])
    rendered = card.render()
    assert "always-pass" in rendered
    assert "FAIL" in rendered
    assert "exit 1" in rendered
    d = card.to_dict()
    assert d["exit_code"] == 1
    assert d["summary"]["total"] == 2
    assert d["summary"]["hard_failures"] == 1


def test_default_suite_is_the_four_core_checkers():
    suite = build_default_suite()
    assert [c.id for c in suite] == [
        "text-fidelity",
        "reading-order",
        "footnote-anchor",
        "structure-typing",
    ]
    # All hard-gating by default.
    assert all(c.severity == "hard" for c in suite)
