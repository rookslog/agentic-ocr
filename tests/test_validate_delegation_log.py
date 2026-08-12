"""Tests for .github/scripts/validate_delegation_log.py.

The validator is a stdlib-only CLI; we exercise it via subprocess so exit codes
and output (what CI actually sees) are what's under test.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / ".github" / "scripts" / "validate_delegation_log.py"
REAL_LOG = REPO_ROOT / "delegation-log.jsonl"


def run(log_path: Path, *flags: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(log_path), *flags],
        capture_output=True, text=True, check=False,
    )


def delegation(id_: str = "D-001", **overrides: object) -> dict[str, object]:
    ev: dict[str, object] = {
        "event": "delegation", "id": id_, "ts": "2026-06-12", "session": "test",
        "delegator": "fable@main", "task": "test task", "task_class": "deep-exploration",
        "inputs": [], "tier_chosen": {"model": "opus", "effort": "high"},
        "tier_rubric_default": {"model": "opus", "effort": "high"},
        "overfit_steps": 0, "justification": None, "overkill_suspect": False,
        "predicted": {"tokens": 50000, "one_tier_lower_sufficient": "no",
                      "risk_notes": "test"},
        "artifact": ["out.md"],
    }
    ev.update(overrides)
    return ev


def disposition(ref: str = "D-001", **overrides: object) -> dict[str, object]:
    ev: dict[str, object] = {
        "event": "disposition", "ref": ref, "ts": "2026-06-12",
        "actual_tokens": 40000, "disposition": "accepted",
        "spot_check": "verified output", "immediate_defects": [],
    }
    ev.update(overrides)
    return ev


def intervention_open(id_: str = "I-001", ref: str = "D-001") -> dict[str, object]:
    return {
        "event": "intervention", "id": id_, "ts": "2026-06-12", "refs": [ref],
        "verdict": None, "action": "fix template",
        "diagnosis": {"fault_layer": "contract", "evidence": "e", "rivals": [],
                      "distinguishing_observation": "o"},
        "predicted_signal": {"metric": "m", "direction_and_margin": "d",
                             "review_by": "2026-07-01"},
    }


def write_log(tmp_path: Path, *events: dict[str, object]) -> Path:
    log = tmp_path / "log.jsonl"
    log.write_text("".join(json.dumps(e) + "\n" for e in events))
    return log


def test_real_repo_log_is_valid() -> None:
    result = run(REAL_LOG)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "PASSED" in result.stdout


def test_minimal_valid_log_passes(tmp_path: Path) -> None:
    log = write_log(tmp_path, delegation(), disposition())
    result = run(log)
    assert result.returncode == 0, result.stdout
    assert "1 delegation(s)" in result.stdout


def test_overfit_two_steps_without_justification_fails(tmp_path: Path) -> None:
    log = write_log(tmp_path, delegation(overfit_steps=2))
    result = run(log)
    assert result.returncode == 1
    assert "requires a written justification" in result.stdout


def test_overfit_two_steps_with_justification_passes(tmp_path: Path) -> None:
    log = write_log(tmp_path, delegation(overfit_steps=2, justification="load-bearing artifact"))
    assert run(log).returncode == 0


def test_overfit_two_steps_self_flagged_passes(tmp_path: Path) -> None:
    log = write_log(tmp_path, delegation(overfit_steps=2, overkill_suspect=True))
    assert run(log).returncode == 0


def test_dangling_ref_fails(tmp_path: Path) -> None:
    log = write_log(tmp_path, delegation(), disposition(ref="D-999"))
    result = run(log)
    assert result.returncode == 1
    assert "does not match any earlier delegation" in result.stdout


def test_reference_before_definition_fails(tmp_path: Path) -> None:
    log = write_log(tmp_path, disposition(), delegation())
    assert run(log).returncode == 1


def test_duplicate_delegation_id_fails(tmp_path: Path) -> None:
    log = write_log(tmp_path, delegation(), delegation())
    result = run(log)
    assert result.returncode == 1
    assert "duplicate delegation id" in result.stdout


def test_invalid_json_line_fails(tmp_path: Path) -> None:
    log = tmp_path / "log.jsonl"
    log.write_text(json.dumps(delegation()) + "\n{not json\n")
    result = run(log)
    assert result.returncode == 1
    assert "not valid JSON" in result.stdout


def test_unknown_event_type_fails(tmp_path: Path) -> None:
    log = write_log(tmp_path, {"event": "mystery", "id": "X-1"})
    result = run(log)
    assert result.returncode == 1
    assert "unknown event type" in result.stdout


def test_bad_task_class_fails(tmp_path: Path) -> None:
    log = write_log(tmp_path, delegation(task_class="vibes"))
    assert run(log).returncode == 1


def test_bad_model_fails(tmp_path: Path) -> None:
    log = write_log(tmp_path, delegation(tier_chosen={"model": "gpt", "effort": "high"}))
    assert run(log).returncode == 1


def test_cross_vendor_model_accepted(tmp_path: Path) -> None:
    # gpt-5.6-sol joined MODELS 2026-08-12 (D-250 drive handoff); it is unranked, so
    # the computed-overfit guard must fall back to self-reported steps, not crash.
    log = write_log(tmp_path, delegation(
        tier_chosen={"model": "gpt-5.6-sol", "effort": "ultra"}))
    result = run(log)
    assert result.returncode == 0
    assert "WARNING" not in result.stdout


def test_max_effort_is_accepted_without_warning(tmp_path: Path) -> None:
    # `max` is a known effort value — no unknown-effort warning. Both tiers max so this
    # isolates the vocabulary check from the overfit guardrail.
    log = write_log(tmp_path, delegation(
        tier_chosen={"model": "opus", "effort": "max"},
        tier_rubric_default={"model": "opus", "effort": "max"}))
    result = run(log)
    assert result.returncode == 0
    assert "WARNING" not in result.stdout


def test_cancelled_disposition_needs_no_tokens(tmp_path: Path) -> None:
    log = write_log(
        tmp_path, delegation(),
        {"event": "disposition", "ref": "D-001", "ts": "2026-06-12",
         "disposition": "cancelled", "spot_check": "never launched; superseded by D-002"},
    )
    result = run(log)
    assert result.returncode == 0
    assert "WARNING" not in result.stdout


def test_review_verdict_with_bad_fault_layer_fails(tmp_path: Path) -> None:
    log = write_log(
        tmp_path, delegation(),
        {"event": "review-verdict", "ref": "D-001", "ts": "2026-06-12",
         "gate": "T3 PR#2", "reviewer_tier": "fable high",
         "findings": [{"severity": "major", "summary": "x", "fault_layer": "gremlins"}],
         "retrospectively_sufficient_tier": "unsure"},
    )
    result = run(log)
    assert result.returncode == 1
    assert "fault_layer" in result.stdout


def test_intervention_opening_requires_signal(tmp_path: Path) -> None:
    log = write_log(
        tmp_path, delegation(),
        {"event": "intervention", "id": "I-001", "ts": "2026-06-12",
         "refs": ["D-001"], "verdict": None,
         "diagnosis": {"fault_layer": "contract", "evidence": "e",
                       "rivals": [], "distinguishing_observation": "o"},
         "action": "fix template"},
    )
    result = run(log)
    assert result.returncode == 1
    assert "predicted_signal" in result.stdout


def test_intervention_closing_without_opening_fails(tmp_path: Path) -> None:
    log = write_log(
        tmp_path,
        {"event": "intervention", "id": "I-001", "ts": "2026-06-12",
         "refs": [], "verdict": "Corroborated"},
    )
    result = run(log)
    assert result.returncode == 1
    assert "no earlier opening" in result.stdout


def test_intervention_bad_verdict_vocabulary_fails(tmp_path: Path) -> None:
    log = write_log(
        tmp_path,
        {"event": "intervention", "id": "I-001", "ts": "2026-06-12", "refs": [],
         "verdict": None, "action": "a",
         "diagnosis": {"fault_layer": "contract", "evidence": "e", "rivals": [],
                       "distinguishing_observation": "o"},
         "predicted_signal": {"metric": "m", "direction_and_margin": "d",
                              "review_by": "2026-07-01"}},
        {"event": "intervention", "id": "I-001", "ts": "2026-07-01", "refs": [],
         "verdict": "It Worked Great"},
    )
    result = run(log)
    assert result.returncode == 1
    assert "ledger vocabulary" in result.stdout


def test_understated_overfit_steps_fails(tmp_path: Path) -> None:
    # opus-max chosen against a sonnet-low default is 5 rungs; declaring 1 dodges the guard.
    log = write_log(tmp_path, delegation(
        tier_chosen={"model": "opus", "effort": "max"},
        tier_rubric_default={"model": "sonnet", "effort": "low"},
        overfit_steps=1, justification="x"))
    result = run(log)
    assert result.returncode == 1
    assert "understates the tier gap" in result.stdout


def test_computed_guardrail_trips_without_justification(tmp_path: Path) -> None:
    # honestly declared big overfit, but no justification → guardrail error on computed gap.
    log = write_log(tmp_path, delegation(
        tier_chosen={"model": "opus", "effort": "max"},
        tier_rubric_default={"model": "sonnet", "effort": "low"},
        overfit_steps=5))
    result = run(log)
    assert result.returncode == 1
    assert "requires a written justification" in result.stdout


def test_computed_guardrail_passes_with_justification(tmp_path: Path) -> None:
    log = write_log(tmp_path, delegation(
        tier_chosen={"model": "opus", "effort": "max"},
        tier_rubric_default={"model": "sonnet", "effort": "low"},
        overfit_steps=5, justification="constitutional artifact"))
    assert run(log).returncode == 0


def test_closing_intervention_without_diagnosis_outcome_warns(tmp_path: Path) -> None:
    log = write_log(
        tmp_path, delegation(), intervention_open(),
        {"event": "intervention", "id": "I-001", "ts": "2026-07-01", "refs": [],
         "verdict": "Corroborated"},
    )
    result = run(log)
    assert result.returncode == 0  # warning, not error
    assert "no diagnosis_outcome" in result.stdout


def test_bad_diagnosis_outcome_fails(tmp_path: Path) -> None:
    log = write_log(
        tmp_path, delegation(), intervention_open(),
        {"event": "intervention", "id": "I-001", "ts": "2026-07-01", "refs": [],
         "verdict": "Corroborated", "diagnosis_outcome": "maybe"},
    )
    result = run(log)
    assert result.returncode == 1
    assert "diagnosis_outcome" in result.stdout


def test_diagnosis_hit_rate_and_renamed_stats(tmp_path: Path) -> None:
    log = write_log(
        tmp_path, delegation(), intervention_open(),
        {"event": "intervention", "id": "I-001", "ts": "2026-07-01", "refs": [],
         "verdict": "Corroborated", "diagnosis_outcome": "confirmed"},
    )
    result = run(log, "--audit")
    assert result.returncode == 0
    draft = json.loads(result.stdout[result.stdout.index("{"):])
    assert draft["stats"]["diagnosis_hit_rate"] == 1.0
    assert "rework_rate" in draft["stats"]
    assert "undershoot_rate" in draft["stats"]
    assert "undershoot_rework_rate" not in draft["stats"]


def test_audit_mode_emits_draft_meta_audit(tmp_path: Path) -> None:
    log = write_log(tmp_path, delegation(), disposition())
    result = run(log, "--audit")
    assert result.returncode == 0
    # The draft event is the JSON block after the PASSED line.
    json_start = result.stdout.index("{")
    draft = json.loads(result.stdout[json_start:])
    assert draft["event"] == "meta-audit"
    assert draft["stats"]["delegations"] == 1
    assert draft["stats"]["review_linkage_fraction"] == 0.0
    assert "0.80" in draft["stats"]["token_prediction_calibration"]


def test_audit_on_real_log_runs(tmp_path: Path) -> None:
    result = run(REAL_LOG, "--audit")
    assert result.returncode == 0
    assert '"event": "meta-audit"' in result.stdout
