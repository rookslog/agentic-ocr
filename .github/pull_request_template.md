<!--
Review tiers (PLAN.md §11.3). T1 (lint/types/tests/guards) is enforced by CI on
every PR. Pick the human-review tier below and complete its checklist.
-->

## What & why

<!-- One paragraph: what this changes and why. Link the STATE.md item / experiment. -->

## Review tier

- [ ] **T2 — standard PR review** (plumbing, scripts, runners, docs).
      *Touches only non-load-bearing paths. One light reviewer pass.*
- [ ] **T3 — load-bearing PR review** (auto-labeled `load-bearing`).
      *Touches `eval/**`, `experiments/**`, `runner/targets*`, or `.github/**` —
      anything that can silently invalidate experiments.*

> If the `load-bearing` label is on this PR, **T3 is required** regardless of what
> you ticked. T3 ⇒ deep review + **reviewer ≠ author** + Logan approves.

## T1 — deterministic self-checks (CI, blocking)

- [ ] `ruff`, `mypy`, `pytest` green.
- [ ] No `*.pdf` and no file > 1MB (no-corpus-blob guard).
- [ ] If this PR adds/changes `experiments/E*/results*`: the matching `prereg.md`
      is **already merged** (prereg-gate, PLAN §11.2).

## T3 — load-bearing checklist (complete if labeled `load-bearing`)

- [ ] **Reviewer ≠ author** (verifier ≠ producer applied to process).
- [ ] No change to a metric/checker definition that would shift past experiment
      results without a ledger entry + a re-run note.
- [ ] Experiment files: prereg fields intact (Hypothesis / Prediction /
      Pre-registered disconfirmer / Baseline / Decision rule incl. cost / Threats);
      `Results` edited append-only only.
- [ ] `STATE.md` / `ledger.md` updated if this changes what is true now or logs a
      predict→verdict.
- [ ] Logan's approval obtained.

## Provenance (if this records an eval result)

<!-- Pins: schema repo version, corpus-generator version, target hardware, cost. -->
