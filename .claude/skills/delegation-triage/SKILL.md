---
name: delegation-triage
description: Triage + trace every delegated subtask — pick the cheapest sufficient model tier, log the decision to delegation-log.jsonl BEFORE launching, disposition the output, and close the loop at review gates. Use whenever spawning a subagent/workflow, receiving its output, or reviewing a delegated artifact.
---

# Delegation triage

Authority: `docs/delegation-triage.md` (this skill is the operational checklist; if
they disagree, the doc wins and the skill has a bug). Enforcement: CI runs
`.github/scripts/validate_delegation_log.py` on every push — an unjustified ≥2-step
tier overshoot or a malformed event fails the build.

## Before launching ANY subagent or workflow

1. **Classify**: `mechanical-search` · `deep-exploration` · `web-research` ·
   `build-implement` · `synthesis-design` · `adversarial-review` ·
   `verdict-adjudication`.
2. **Size**: predict tokens. >140k → split. <~10k (a couple of reads) → do it inline,
   don't delegate. Group related subtasks into one delegation within 100–140k.
3. **Tier** (cheapest sufficient, ≤1 step overfit; **fable deprecated 2026-06-12** —
   main agent is opus, all mappings opus-based; ladder: model haiku<sonnet<opus,
   effort low<medium<high<xhigh<max):
   - mechanical-search → sonnet
   - deep-exploration / web-research → **opus high** (research never drops below opus)
   - build-implement → sonnet (fully-spec mechanical) / **opus xhigh** (integration judgment)
   - synthesis-design → opus xhigh (or the main agent)
   - adversarial-review / verdict-adjudication → **opus xhigh** (max for constitutional
     or synthesis-heavy artifacts) — Logan's directive 2026-06-12
4. **≥2 steps above default?** Write a `justification`, or the record must carry
   `overkill_suspect: true`. CI rejects silent overshoot.
5. **Append the `delegation` event to `delegation-log.jsonl` BEFORE the agent runs.**
   An untraced delegation is itself a process defect. Template:

```json
{"event": "delegation", "id": "D-NNN", "ts": "YYYY-MM-DD", "session": "...", "delegator": "fable@main", "task": "one line", "task_class": "...", "inputs": ["..."], "tier_chosen": {"model": "...", "effort": "..."}, "tier_rubric_default": {"model": "...", "effort": "..."}, "overfit_steps": 0, "justification": null, "overkill_suspect": false, "predicted": {"tokens": 0, "one_tier_lower_sufficient": "yes|no|unsure", "risk_notes": "..."}, "artifact": ["expected output paths"]}
```

## On receiving the output

Spot-check before building on it (subagent output is *Reported, not verified*), then
append:

```json
{"event": "disposition", "ref": "D-NNN", "ts": "...", "actual_tokens": 0, "disposition": "accepted|accepted-with-edits|rework|rejected|cancelled", "spot_check": "what you independently verified", "immediate_defects": []}
```

`cancelled` = delegation logged but never launched (or superseded before output);
say why and name the superseding D-NNN in `spot_check`.

## At review gates (T2–T5) touching a delegated artifact

Append a `review-verdict`: gate = *symptom* (where it surfaced), per-finding
`fault_layer` + `etclovg` = *cause*, and `retrospectively_sufficient_tier` (the
counterfactual that calibrates the rubric). Vocabulary + mapping table:
`docs/delegation-triage.md` §3. Findings caused by an *upstream* delegated artifact
get re-assigned to that artifact's D-NNN, not the immediate producer's.

## Interventions & audits

- Process change in response to a diagnosis → `intervention` event with
  pre-registered `predicted_signal` (metric, margin, review-by) + `rivals` +
  `distinguishing_observation`. Close it later with a ledger-vocabulary verdict.
- Phase gate → run `python3 .github/scripts/validate_delegation_log.py
  delegation-log.jsonl --audit`, review the draft stats, append the `meta-audit`
  event manually (never auto-append).

## Never

- Edit a past log line (append-only; correct by appending).
- Launch before logging.
- Route research/exploration below opus.
- Let a "quick" untraced delegation slide — that's how the log becomes ceremony.
