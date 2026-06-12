# Experiments

Pre-registered experiments E1–E7 (PLAN.md §9). Order matters: the eval instrument
(E1) is validated *before* it is used to select anything.

Each `E?/` directory holds:

- `README.md` — the one-line hypothesis + disconfirmer (derived from PLAN §9).
- `prereg.md` — the full pre-registration (copy of `_TEMPLATE.md`), written and
  merged **before** the run.
- `results*.md` / `results*.json` — outcomes, written **after**, append-only.

## The merge-order rule (epistemic standard as a merge gate)

Per PLAN §11.2, *"an experiment results file cannot merge unless its prereg file is
already in history."* This makes pre-registration a mechanical gate, not a norm:
you cannot retro-fit a hypothesis to a result you already have.

**How the CI prereg-gate enforces it** (`.github/scripts/prereg_gate.sh`, runs on
PRs only):

1. The gate diffs the PR against the **merge-base with `main`** — the commit where
   this PR branched off.
2. It lists every file the PR **adds or changes** that matches
   `experiments/E*/results*` (the results files for any experiment).
3. For each such experiment directory `E?`, it checks whether that experiment's
   **prereg file already exists in the merge-base** (i.e. was merged in an *earlier*
   PR). The prereg must be in history *before* this PR, not merely present in this
   same PR.
4. If a results file is added/changed while its prereg is **not** already in the
   merge-base of `main`, the gate **fails the PR**.

Consequence: prereg and results land in **separate PRs**, prereg first. A single PR
that introduces both a brand-new prereg and its results is rejected.

## Pre-registration fields (PLAN §8 item 2)

Every `prereg.md` carries: **Hypothesis · Prediction** (expected fixes + at-risk
regressions) **· Pre-registered disconfirmer · Baseline · Decision rule** (Δ
thresholds *including cost*) **· Threats to validity · Results** (append-only).
See [`_TEMPLATE.md`](_TEMPLATE.md).

## Review tier

`experiments/**` is **load-bearing** (PLAN §11.3, tier **T3**): a change here can
*silently invalidate experiments*. PRs touching it get the `load-bearing` label
(via `.github/labeler.yml`), a deep review, **reviewer ≠ author**, and Logan's
approval. Plumbing-only PRs are tier **T2** (one light reviewer pass).

## The programme (PLAN §9)

| # | Question (ladder) | One line |
|---|---|---|
| E1 | GT validity | Does synthetic GT (GT-A) rank variants like real-scan GT (GT-B)? — the instrument experiment, validated first. |
| E2 | Baseline ladder | How close does a local small VLM + checkers (C0) get to frontier transcription? Establishes B*. |
| E3 | Cascade dividend (A1 vs A0) | Does confidence-routed escalation recover ≥70% of the frontier gap at ≤3× B* cost? |
| E4 | Structure question (A2 vs A1) | Do bounded verify→revise loops beat single-pass structure by ≥10 pts? — heart of the research question. |
| E5 | Transcription-loop question (A2 on L1) | Skeptical: do re-OCR loops add ≤2 pts over the cascade? |
| E6 | Tier×harness interaction | Is harness lift non-monotone across fm / Haiku / Sonnet, requiring per-tier tuning? |
| E7 | Open-agent probe (A3) | VOI-gated, last: does a tool-using agent find error classes C2 misses? |

**Programme-level decision rule:** a future scholardoc supports an agentic config
**iff** E4 (or E5) clears its pre-registered quality-per-dollar margin over C1 on at
least one corpus stratum. Otherwise: cascade yes, agent no — a reportable answer.
