# AGENTS.md — operating contract for any agent working this repo

This file is vendor-agnostic: it binds Claude, codex/GPT, Gemini, or any other
agent session equally. Session-specific work orders live in `goal/*.goal.md`
packets; this file carries only the durable rules.

## Read-first, in this order

1. `STATE.md` — what is true now. The first thing any fresh session reads.
2. The active goal packet in `goal/` (a handoff prompt names it).
3. `PLAN.md` — strategy. **Frozen outside phase gates — do not edit it.**
4. `ledger.md` — append-only predict→verdict history.
5. `docs/delegation-triage.md` — the delegation-trace discipline.

## Hard constraints (non-negotiable)

- **No corpus bytes in git.** No PDFs, EPUBs, page images, or extracted book text
  may ever be committed — CI enforces a no-PDF/no->1MB guard, but the rule covers
  small fragments too. Corpus files live only in gitignored `corpus/` and `.local/`.
- **No acquisition provenance in tracked files.** No zlibrary IDs, URLs, or
  source-site identifiers anywhere in git history. Provenance stays in gitignored
  `corpus/` manifests.
- **Do not quote corpus text** into transcripts, reports, PR bodies, or evidence
  docs. Titles, counts, and metrics are fine; passages are not.
- **zlibrary acquisition is HUMAN-GATED (H-2).** Never invoke it; only Logan opens
  that gate, and only if owned + public-domain mining leaves gate clause 4 short.
- **No content-filter circumvention.** Chunked/obfuscated output schemes to defeat
  a provider's output filtering are out of policy, full stop.
- **PR-only workflow.** `main` is protected on all three repos. Merges execute
  agentially only when the branch is CI-green AND the review gate named in the
  active packet has passed.
- **Experiments need pre-registration before results.** CI runs a prereg-gate on
  PRs; `experiments/_TEMPLATE.md` holds the required fields. Never write a verdict
  into `experiments/` for a run that wasn't prereg'd (operator-sanctioned probes
  are recorded in STATE.md instead, labeled as probes).

## Process discipline

- **Claims discipline.** State only what a check you actually ran licenses.
  Separate measured from reasoned inline ("measured: …", "unchecked: …"). A
  load-bearing claim carries its receipt (command, path, run-id) in the same
  sentence. Failure-claims ("stalled", "broken") need MORE warrant than success
  claims — establish the expected baseline, rule out benign causes, check the
  primary artifact, or down-label to "no result surfaced yet (cause unconfirmed)".
- **Propagation.** Any change brings every dependent artifact current in the same
  pass: STATE.md, ledger.md, goal packets, READMEs, cross-references. After your
  change, no file is silently stale because of it.
- **Delegation trace.** Every delegated subtask (including cross-vendor handoffs
  and any subagents you spawn) gets a row in `delegation-log.jsonl` per
  `docs/delegation-triage.md`. Validate before committing:
  `uv run python .github/scripts/validate_delegation_log.py delegation-log.jsonl`.
- **STATE.md is updated every working session** — it is "what is true now", and a
  fresh session must be able to resume from it alone.
- **Batch human decisions.** Drive autonomously to terminal conditions; collect
  genuinely-human decisions (value calls, spending, external accounts) into one
  batched ask rather than dribbling them. A surfaced decision states: what it is,
  the option space, your recommendation and why, the load-bearing assumption, and
  what would flip it.

## Validation commands (run from repo root)

```
uv run pytest                 # full suite
uv run ruff check .           # lint
uv run mypy .                 # types
uv run python .github/scripts/validate_delegation_log.py delegation-log.jsonl
```

## Repo map

- `eval/lib/` — scoring core (normalize/matching/metrics/reports).
- `eval/checkers/` — deterministic checker suite (PR #3 until merged).
- `eval/gtb/` — GT-B aligner + page-key layer (PR #5 until merged).
- `eval/fixtures/` — JSON-only eval data; legacy labels in `eval/fixtures/README.md`.
- `experiments/E1…E7/` — pre-registered experiment skeletons.
- `runner/` — SSH-over-Tailscale execution skeleton (`targets.toml`: local-mac,
  dionysus, rental).
- `goal/` — work packets + `goal/evidence/` completion evidence.
- `docs/adr/` — architecture decision records (ADR-0002 = schema-evolution policy).
- `corpus/`, `.local/` — gitignored; never pushed.

## Sibling repos (same rules apply)

- `rookslog/scholar-schema` — the GT schema (import name `scholargt`), pinned here
  at tag `v0.1.0` via `[tool.uv.sources]`.
- `rookslog/scriptorium` — schema-first synthetic-corpus generator.
