# Delegation triage & credit assignment

**Status:** adopted 2026-06-12 (Logan's directive, session eaa44f15). Applies to every
delegated subtask in this project — exploration, build packets, reviews. The experiment
preregs/verdicts themselves remain interactive (PLAN §11.4) and are out of scope here.

This is the predict→verdict discipline of `ledger.md` applied to *delegation decisions
themselves*: record the tier choice and its predicted sufficiency before launch, then let
later review gates settle whether the choice was right — so that responsibility can be
traced, interventions chosen deliberately, and the interventions themselves audited.

## 1. Triage rubric (at delegation time)

1. **Classify** the task:
   `mechanical-search` · `deep-exploration` · `web-research` · `build-implement` ·
   `synthesis-design` · `adversarial-review` · `verdict-adjudication`.
2. **Size it.** Predict token cost. If predicted > **140k**, split it. If trivially small
   (< ~10k and the answer is one or two reads), do it inline — delegation overhead isn't
   free either. Group related subtasks into one delegation while the total stays in the
   **100–140k** envelope.
3. **Pick the cheapest sufficient tier, plus at most one step of overfit.** Tier ladder
   (ascending cost; fable ≈ 2× opus per token, Logan's figure):

   | task class | rubric default | notes |
   |---|---|---|
   | mechanical-search | sonnet | glob/grep/enumerate; no judgment |
   | deep-exploration | opus high | local corpus, structured findings. **Never fable for research** (Logan's standing rule) |
   | web-research | opus high | crawling + claim-tagging contract |
   | build-implement | sonnet → opus | sonnet when spec is complete; opus when integration judgment needed |
   | synthesis-design | fable (main agent) or opus xhigh | designs, plans, schemas |
   | adversarial-review | opus xhigh / fable high | reviewer ≠ producer (PLAN §11.3) |
   | verdict-adjudication | fable high/xhigh | T3+ gates, experiment-adjacent calls |

4. **Overkill guardrail.** A choice ≥2 steps above the rubric default requires a written
   `justification` in the trace record. No justification ⇒ the record is written with
   `overkill_suspect: true`. (Self-enforced now; mechanically lintable once the log has
   volume. Undershoot is caught the other way — by rework/review findings, §3.)
5. **Record before launching.** Append the `delegation` event (§2) *before* the agent
   runs, including the prediction fields. A delegation with no prior trace row is itself
   a process defect.

## 2. The trace log: `delegation-log.jsonl`

Append-only JSONL at repo root (peer of `ledger.md`: the ledger is the low-volume human
narrative for pipeline changes; this is higher-volume operational telemetry, kept
machine-queryable for the meta-audit). Never edit a past line; correct by appending.
Five event types:

**`delegation`** — written by the delegator, before launch.
```json
{"event": "delegation", "id": "D-001", "ts": "...", "session": "...",
 "delegator": "fable@main", "task": "one line", "task_class": "deep-exploration",
 "inputs": ["paths/contracts handed over"],
 "tier_chosen": {"model": "opus", "effort": "high"},
 "tier_rubric_default": {"model": "opus", "effort": "high"},
 "overfit_steps": 0, "justification": null, "overkill_suspect": false,
 "predicted": {"tokens": 120000,
               "one_tier_lower_sufficient": "no|yes|unsure",
               "risk_notes": "..."},
 "artifact": ["paths the delegate is expected to produce"]}
```

**`disposition`** — written by the delegator on receiving the output.
```json
{"event": "disposition", "ref": "D-001", "ts": "...",
 "actual_tokens": 0, "disposition": "accepted|accepted-with-edits|rework|rejected",
 "spot_check": "what was independently verified (Reported → Corroborated)",
 "immediate_defects": []}
```

**`review-verdict`** — written at any later review gate (T2–T5) whose subject includes a
delegated artifact. This is the signal that closes the loop on triage quality.
```json
{"event": "review-verdict", "ref": "D-001", "ts": "...",
 "gate": "T3 PR#12 | T4 design review | T5 phase gate", "reviewer_tier": "fable high",
 "findings": [{"severity": "major|minor", "summary": "...",
               "fault_layer": "...", "etclovg": "E|T|C|L|O|V|G|substrate"}],
 "retrospectively_sufficient_tier": {"model": "...", "effort": "..."}}
```
The `gate` is the *symptom* axis (where the fault surfaced); `etclovg` is the *cause*
axis — the lab's dual-axis coding (lanes/OBSERVABILITY.md §3). The
`retrospectively_sufficient_tier` is the symmetric counterfactual: compared against
`tier_chosen` it makes over-provisioning and under-provisioning the same first-class
measurement (the prediction/verdict gap is the product, not an error).
```

**`intervention`** — written when a diagnosis leads to a process change.
```json
{"event": "intervention", "id": "I-001", "ts": "...", "refs": ["D-001", "..."],
 "diagnosis": {"fault_layer": "...", "evidence": "...",
               "rivals": ["other plausible diagnoses"],
               "distinguishing_observation": "what would tell this diagnosis from its rivals"},
 "action": "rubric change | contract template change | tier change | guardrail | context fix",
 "predicted_signal": {"metric": "e.g. rework rate for task_class=X",
                      "direction_and_margin": "Δ must exceed 0 by ...; Δ≤0 ⇒ cost without benefit (X-003 pattern)",
                      "review_by": "date"},
 "verdict": null}
```
The `verdict` is appended later as a new `intervention` line (same `id`, back-reference),
using the ledger vocabulary (`Corroborated` / `Underdetermined` / …). Interventions that
change committed process docs also get a `ledger.md` row.

**`meta-audit`** — written at each phase gate (T5), sweeping the whole log.
```json
{"event": "meta-audit", "ts": "...", "window": "phase 0",
 "stats": {"delegations": 0, "overshoot_rate": 0, "undershoot_rework_rate": 0,
           "token_prediction_calibration": "...", "review_linkage_fraction": 0,
           "intervention_success_rate": 0, "diagnosis_hit_rate": 0},
 "failed_interventions": [{"id": "I-001", "why": "wrong-layer diagnosis | right layer, wrong action | insufficient dosage | signal too noisy to read | regressed elsewhere", "next": "new I-NNN or drop"}]}
```

## 3. Credit assignment: the `fault_layer` vocabulary

When a review gate faults a delegated artifact, the finding must name *where* the fault
lives — otherwise the only available intervention is the blunt one ("use a bigger
model"), which is usually wrong:

- **`model-capacity`** — tier too weak; a stronger tier would likely not have erred.
  Intervention: raise the rubric default for this task class. *Only this layer justifies
  tier escalation.*
- **`contract`** — the delegation prompt was ambiguous/defective. Fault sits with the
  delegator. Intervention: fix the prompt-contract template, not the tier.
- **`context`** — required input was missing or stale. Intervention: fix the
  files-as-environment handoff (Read-first lists, STATE.md freshness).
- **`verification`** — the delegator's spot-check should have caught it on disposition.
  Intervention: strengthen the disposition checklist for this artifact type.
- **`taste`** — reviewer preference, not a defect. No intervention; tracked so noise
  doesn't drive tier inflation.
- **`upstream`** — inherited from an earlier artifact; chain the finding to that
  delegation's `D-NNN` and re-assign there.

`retrospectively_sufficient_tier` on every `review-verdict` is what calibrates the
rubric over time: sufficient < chosen on an overfit delegation is evidence the overfit
bought nothing (Δ ≤ 0 ⇒ cost without benefit, the X-003 rule applied to tier);
sufficient > chosen on a rubric-default delegation is evidence the default is too low.

`fault_layer` is this project's delegation-specific refinement of the lab's **ETCLOVG**
harness taxonomy (AgenticHarnessResearch `meta/glossary.md`: Execution environment ·
Tool interface · Context & memory · Lifecycle & orchestration · Observability ·
Verification & evaluation · Governance — "we tag frictions, interventions, and reading
by layer"). Mapping, recorded per finding in the `etclovg` field:

| fault_layer | etclovg cause | note |
|---|---|---|
| model-capacity | `substrate` | not a harness layer — the model itself |
| contract | `C` | the handoff is context the delegate sees |
| context | `C` | missing/stale inputs |
| verification | `V` | disposition spot-check too weak |
| taste | — | no cause; tracked to resist tier inflation |
| upstream | (chained) | re-assigned at the referenced D-NNN |
| *the triage choice itself* | `L` | orchestration picked the tier |

A triage miss thus *surfaces* at V (a gate caught it) but is *caused* at L — the
symptom/cause split is what keeps "wrong tier" distinguishable from "right tier, weak
gate". Full prior-art survey: `.local/research/observability-prior-art.md` (local-only).

## 4. Why interventions carry pre-registered signals

"Say the intervention doesn't work — why?" is only answerable if, at intervention time,
we wrote down (a) the diagnosis it rests on, (b) the metric that should move, (c) the
margin and the review-by date. Then a failed intervention decomposes mechanically:

1. Signal didn't move and diagnosis was wrong → **wrong-layer**: re-diagnose, new I-NNN.
2. Signal didn't move but diagnosis still holds → **right layer, wrong action** or
   **insufficient dosage**.
3. Signal unmeasurable → the *observability* is the defect; fix the log, not the process.
4. Signal moved but something else regressed → the meta-audit's sweep stats catch it.

Without the pre-registration, every failed intervention collapses into "try something
else," and the meta-system has nothing to audit. This is PLAN §8 item 4 applied to the
process layer. The `rivals` / `distinguishing_observation` fields make each diagnosis
individually falsifiable; the meta-audit's `diagnosis_hit_rate` aggregates how often our
attributions survive later evidence — the triage layer is itself a diagnosis engine, and
a layer that grades artifacts but never grades itself fails the meta-audit requirement.

## 5. Bootstrap

The log opens with the two delegations made while designing this layer (D-001 corpus
inventory, D-002 prior-art mining) — the system records itself from the first decision.
