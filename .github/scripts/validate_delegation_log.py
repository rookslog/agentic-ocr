#!/usr/bin/env python3
"""Validate delegation-log.jsonl against the schema in docs/delegation-triage.md.

Usage:
    python3 .github/scripts/validate_delegation_log.py delegation-log.jsonl [--audit]

Exit codes: 0 = valid (warnings allowed), 1 = violations found, 2 = usage error.

The log is append-only JSONL; five event types (delegation, disposition,
review-verdict, intervention, meta-audit). This validator is the mechanical
enforcement of the doc's rules — if the two disagree, the doc is authority and
this script has a bug. --audit additionally prints a draft meta-audit event
computed from the log (to be reviewed and appended manually, never auto-written).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

TASK_CLASSES = {
    "mechanical-search",
    "deep-exploration",
    "web-research",
    "build-implement",
    "synthesis-design",
    "adversarial-review",
    "verdict-adjudication",
}
# `fable` retained as a valid historical value — past log rows (D-001..D-004) were
# written when the main agent ran on fable; it was deprecated 2026-06-12. New rows are
# opus-based (docs/delegation-triage.md §1.3), but the log is append-only so the
# vocabulary must keep accepting what was already written.
MODELS = {"haiku", "sonnet", "opus", "fable"}
KNOWN_EFFORTS = {"low", "medium", "default", "high", "xhigh", "max"}
DISPOSITIONS = {"accepted", "accepted-with-edits", "rework", "rejected", "cancelled"}
SUFFICIENCY = {"yes", "no", "unsure"}
SEVERITIES = {"major", "minor"}
FAULT_LAYERS = {"model-capacity", "contract", "context", "verification", "taste", "upstream"}
ETCLOVG = {"E", "T", "C", "L", "O", "V", "G", "substrate"}
LEDGER_VERDICTS = {
    "Corroborated", "Reported", "Resolved", "Concordant", "Survived current tests",
    "Partially supported", "Proxy support", "Underdetermined", "Not tested",
    "Normative judgment",
}
META_AUDIT_STATS = {
    "delegations", "overshoot_rate", "undershoot_rework_rate",
    "token_prediction_calibration", "review_linkage_fraction",
    "intervention_success_rate", "diagnosis_hit_rate",
}

MODEL_RANK = {"haiku": 0, "sonnet": 1, "opus": 2, "fable": 3}
EFFORT_RANK = {"low": 0, "default": 1, "medium": 1, "high": 2, "xhigh": 3, "max": 4}


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, line_no: int, msg: str) -> None:
        self.errors.append(f"line {line_no}: ERROR: {msg}")

    def warn(self, line_no: int, msg: str) -> None:
        self.warnings.append(f"line {line_no}: WARNING: {msg}")


def _require(ev: dict[str, Any], fields: list[str], line_no: int, rep: Report) -> bool:
    missing = [f for f in fields if f not in ev]
    if missing:
        rep.error(line_no, f"{ev.get('event', '?')} event missing fields: {missing}")
        return False
    return True


def _check_tier(tier: Any, where: str, line_no: int, rep: Report) -> None:
    if not isinstance(tier, dict):
        rep.error(line_no, f"{where} must be an object {{model, effort}}, got {tier!r}")
        return
    model = tier.get("model")
    if model not in MODELS:
        rep.error(line_no, f"{where}.model {model!r} not in {sorted(MODELS)}")
    effort = tier.get("effort")
    if not isinstance(effort, str) or not effort:
        rep.error(line_no, f"{where}.effort must be a non-empty string, got {effort!r}")
    elif effort.split("-")[0] not in KNOWN_EFFORTS:
        rep.warn(line_no, f"{where}.effort {effort!r} not a known effort {sorted(KNOWN_EFFORTS)}")


def _check_delegation(ev: dict[str, Any], line_no: int, rep: Report) -> None:
    ok = _require(
        ev,
        ["id", "ts", "task", "task_class", "tier_chosen", "tier_rubric_default",
         "overfit_steps", "justification", "overkill_suspect", "predicted", "artifact"],
        line_no, rep,
    )
    if not ok:
        return
    if ev.get("task_class") not in TASK_CLASSES:
        rep.error(line_no, f"task_class {ev.get('task_class')!r} not in {sorted(TASK_CLASSES)}")
    _check_tier(ev.get("tier_chosen"), "tier_chosen", line_no, rep)
    _check_tier(ev.get("tier_rubric_default"), "tier_rubric_default", line_no, rep)
    overfit = ev.get("overfit_steps")
    if not isinstance(overfit, int):
        rep.error(line_no, f"overfit_steps must be an integer, got {overfit!r}")
    elif overfit >= 2:
        justified = isinstance(ev.get("justification"), str) and ev["justification"].strip()
        if not justified and ev.get("overkill_suspect") is not True:
            rep.error(
                line_no,
                f"{ev['id']}: overfit_steps={overfit} (>=2) requires a written justification "
                "or overkill_suspect: true (docs/delegation-triage.md §1.4)",
            )
    pred = ev.get("predicted")
    if not isinstance(pred, dict):
        rep.error(line_no, f"predicted must be an object, got {pred!r}")
    else:
        if not isinstance(pred.get("tokens"), int):
            rep.error(line_no, f"predicted.tokens must be an integer, got {pred.get('tokens')!r}")
        if pred.get("one_tier_lower_sufficient") not in SUFFICIENCY:
            rep.error(
                line_no,
                f"predicted.one_tier_lower_sufficient {pred.get('one_tier_lower_sufficient')!r} "
                f"not in {sorted(SUFFICIENCY)}",
            )
    if not isinstance(ev.get("artifact"), list):
        rep.error(line_no, f"artifact must be a list, got {ev.get('artifact')!r}")


def _check_disposition(ev: dict[str, Any], line_no: int, rep: Report) -> None:
    if not _require(ev, ["ref", "ts", "disposition", "spot_check"], line_no, rep):
        return
    if ev.get("disposition") not in DISPOSITIONS:
        rep.error(line_no, f"disposition {ev.get('disposition')!r} not in {sorted(DISPOSITIONS)}")
    if ev.get("disposition") != "cancelled" and not isinstance(ev.get("actual_tokens"), int):
        rep.warn(line_no, f"{ev.get('ref')}: disposition has no integer actual_tokens")


def _check_review_verdict(ev: dict[str, Any], line_no: int, rep: Report) -> None:
    ok = _require(
        ev, ["ref", "ts", "gate", "reviewer_tier", "findings",
             "retrospectively_sufficient_tier"],
        line_no, rep,
    )
    if not ok:
        return
    findings = ev.get("findings")
    if not isinstance(findings, list):
        rep.error(line_no, f"findings must be a list, got {findings!r}")
    else:
        for i, f in enumerate(findings):
            if not isinstance(f, dict):
                rep.error(line_no, f"findings[{i}] must be an object")
                continue
            if f.get("severity") not in SEVERITIES:
                rep.error(line_no, f"findings[{i}].severity {f.get('severity')!r} "
                                   f"not in {sorted(SEVERITIES)}")
            if f.get("fault_layer") not in FAULT_LAYERS:
                rep.error(line_no, f"findings[{i}].fault_layer {f.get('fault_layer')!r} "
                                   f"not in {sorted(FAULT_LAYERS)}")
            etclovg = f.get("etclovg")
            if etclovg is not None and etclovg not in ETCLOVG:
                rep.error(line_no, f"findings[{i}].etclovg {etclovg!r} "
                                   f"not in {sorted(ETCLOVG)} or null")
    rst = ev.get("retrospectively_sufficient_tier")
    if rst != "unsure":
        _check_tier(rst, "retrospectively_sufficient_tier", line_no, rep)


def _check_intervention(
    ev: dict[str, Any], line_no: int, rep: Report, open_interventions: set[str]
) -> None:
    if not _require(ev, ["id", "ts", "refs", "verdict"], line_no, rep):
        return
    if not isinstance(ev.get("refs"), list):
        rep.error(line_no, f"refs must be a list, got {ev.get('refs')!r}")
    verdict = ev.get("verdict")
    if verdict is None:
        # Opening record: diagnosis + action + pre-registered signal are mandatory.
        if not _require(ev, ["diagnosis", "action", "predicted_signal"], line_no, rep):
            return
        diag = ev.get("diagnosis")
        if not isinstance(diag, dict):
            rep.error(line_no, f"diagnosis must be an object, got {diag!r}")
        else:
            for field in ("fault_layer", "evidence", "rivals", "distinguishing_observation"):
                if field not in diag:
                    rep.error(line_no, f"{ev['id']}: diagnosis missing {field!r}")
            if diag.get("fault_layer") not in FAULT_LAYERS:
                rep.error(line_no, f"diagnosis.fault_layer {diag.get('fault_layer')!r} "
                                   f"not in {sorted(FAULT_LAYERS)}")
        sig = ev.get("predicted_signal")
        if not isinstance(sig, dict):
            rep.error(line_no, f"predicted_signal must be an object, got {sig!r}")
        else:
            for field in ("metric", "direction_and_margin", "review_by"):
                if field not in sig:
                    rep.error(line_no, f"{ev['id']}: predicted_signal missing {field!r}")
        open_interventions.add(str(ev["id"]))
    else:
        # Closing record: verdict from the ledger vocabulary, must close an opening.
        if verdict not in LEDGER_VERDICTS:
            rep.error(line_no, f"verdict {verdict!r} not in ledger vocabulary "
                               f"{sorted(LEDGER_VERDICTS)}")
        if str(ev.get("id")) not in open_interventions:
            rep.error(line_no, f"{ev.get('id')}: closing verdict with no earlier opening record")


def _check_meta_audit(ev: dict[str, Any], line_no: int, rep: Report) -> None:
    if not _require(ev, ["ts", "window", "stats", "failed_interventions"], line_no, rep):
        return
    stats = ev.get("stats")
    if not isinstance(stats, dict):
        rep.error(line_no, f"stats must be an object, got {stats!r}")
    else:
        missing = META_AUDIT_STATS - set(stats)
        if missing:
            rep.error(line_no, f"meta-audit stats missing keys: {sorted(missing)}")
    if not isinstance(ev.get("failed_interventions"), list):
        rep.error(line_no, "failed_interventions must be a list")


def validate(path: Path) -> tuple[Report, list[dict[str, Any]]]:
    rep = Report()
    events: list[dict[str, Any]] = []
    delegation_ids: set[str] = set()
    open_interventions: set[str] = set()

    try:
        lines = path.read_text().splitlines()
    except OSError as exc:
        rep.errors.append(f"cannot read {path}: {exc}")
        return rep, events

    for line_no, raw in enumerate(lines, start=1):
        if not raw.strip():
            continue
        try:
            ev = json.loads(raw)
        except json.JSONDecodeError as exc:
            rep.error(line_no, f"not valid JSON ({exc})")
            continue
        if not isinstance(ev, dict):
            rep.error(line_no, f"each line must be a JSON object, got {type(ev).__name__}")
            continue
        events.append(ev)

        kind = ev.get("event")
        if kind == "delegation":
            _check_delegation(ev, line_no, rep)
            dle_id = ev.get("id")
            if isinstance(dle_id, str):
                if not dle_id.startswith("D-"):
                    rep.error(line_no, f"delegation id {dle_id!r} must match D-NNN")
                if dle_id in delegation_ids:
                    rep.error(line_no, f"duplicate delegation id {dle_id!r} (append-only: "
                                       "correct with a new event, never a second delegation)")
                delegation_ids.add(dle_id)
        elif kind in ("disposition", "review-verdict"):
            if kind == "disposition":
                _check_disposition(ev, line_no, rep)
            else:
                _check_review_verdict(ev, line_no, rep)
            ref = ev.get("ref")
            if isinstance(ref, str) and ref not in delegation_ids:
                rep.error(line_no, f"{kind} ref {ref!r} does not match any earlier delegation "
                                   "(definitions must precede references in an append-only log)")
        elif kind == "intervention":
            _check_intervention(ev, line_no, rep, open_interventions)
            ivn_id = ev.get("id")
            if isinstance(ivn_id, str) and not ivn_id.startswith("I-"):
                rep.error(line_no, f"intervention id {ivn_id!r} must match I-NNN")
            for ref in ev.get("refs") or []:
                if isinstance(ref, str) and ref.startswith("D-") and ref not in delegation_ids:
                    rep.error(line_no, f"intervention ref {ref!r} does not match any "
                                       "earlier delegation")
        elif kind == "meta-audit":
            _check_meta_audit(ev, line_no, rep)
        else:
            rep.error(line_no, f"unknown event type {kind!r}")

    return rep, events


def _tier_key(tier: Any) -> tuple[int, int] | None:
    if not isinstance(tier, dict):
        return None
    m = MODEL_RANK.get(str(tier.get("model")))
    e = EFFORT_RANK.get(str(tier.get("effort", "")).split("-")[0])
    if m is None or e is None:
        return None
    return (m, e)


def audit(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute draft meta-audit stats. Tier comparison orders by (model, effort)
    lexicographically — a heuristic, since the cross-model/effort grid has no
    total order; treat overshoot/undershoot rates as indicative, not exact."""
    delegations = {e["id"]: e for e in events
                   if e.get("event") == "delegation" and isinstance(e.get("id"), str)}
    dispositions = [e for e in events if e.get("event") == "disposition"]
    verdicts = [e for e in events if e.get("event") == "review-verdict"]
    interventions = [e for e in events if e.get("event") == "intervention"]

    n = len(delegations)
    overshoot = sum(1 for d in delegations.values()
                    if isinstance(d.get("overfit_steps"), int) and d["overfit_steps"] > 0)
    for v in verdicts:
        d = delegations.get(str(v.get("ref")))
        chosen = _tier_key(d.get("tier_chosen")) if d else None
        sufficient = _tier_key(v.get("retrospectively_sufficient_tier"))
        if chosen and sufficient and sufficient < chosen:
            overshoot += 1

    rework = sum(1 for d in dispositions if d.get("disposition") in ("rework", "rejected"))

    ratios = []
    for d in dispositions:
        dle = delegations.get(str(d.get("ref")))
        if dle and isinstance(d.get("actual_tokens"), int):
            predicted = (dle.get("predicted") or {}).get("tokens")
            if isinstance(predicted, int) and predicted > 0:
                ratios.append(d["actual_tokens"] / predicted)
    calibration = (f"mean actual/predicted = {sum(ratios) / len(ratios):.2f} "
                   f"over {len(ratios)} delegations") if ratios else "no data"

    reviewed = {str(v.get("ref")) for v in verdicts}
    linkage = len(reviewed & set(delegations)) / n if n else 0.0

    closed = [i for i in interventions if i.get("verdict")]
    succeeded = sum(1 for i in closed if i.get("verdict") == "Corroborated")
    success_rate = succeeded / len(closed) if closed else None

    return {
        "event": "meta-audit",
        "ts": "FILL-ME",
        "window": "FILL-ME",
        "stats": {
            "delegations": n,
            "overshoot_rate": round(overshoot / n, 3) if n else 0.0,
            "undershoot_rework_rate": round(rework / n, 3) if n else 0.0,
            "token_prediction_calibration": calibration,
            "review_linkage_fraction": round(linkage, 3),
            "intervention_success_rate": success_rate,
            "diagnosis_hit_rate": None,
        },
        "failed_interventions": [
            {"id": i.get("id"), "why": "FILL-ME", "next": "FILL-ME"}
            for i in closed if i.get("verdict") not in ("Corroborated", "Resolved")
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path, help="path to delegation-log.jsonl")
    parser.add_argument("--audit", action="store_true",
                        help="print a draft meta-audit event computed from the log")
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        return 2

    rep, events = validate(args.log)
    for w in rep.warnings:
        print(w)
    for e in rep.errors:
        print(e)

    n_delegations = sum(1 for e in events if e.get("event") == "delegation")
    dispositioned = {str(e.get("ref")) for e in events if e.get("event") == "disposition"}
    open_count = sum(1 for e in events if e.get("event") == "delegation"
                     and str(e.get("id")) not in dispositioned)
    if open_count:
        print(f"note: {open_count} delegation(s) without a disposition yet (OK mid-stream).")

    if rep.errors:
        print(f"delegation-log: FAILED — {len(rep.errors)} violation(s), "
              f"{len(rep.warnings)} warning(s).")
        return 1

    print(f"delegation-log: PASSED — {n_delegations} delegation(s), "
          f"{len(events)} event(s), {len(rep.warnings)} warning(s).")
    if args.audit:
        print(json.dumps(audit(events), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
