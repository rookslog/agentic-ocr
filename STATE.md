# STATE — what is true now

**Authority:** this file is *what is true now* (PLAN.md §11.2). Updated every
working session; the first thing a fresh agent session or /goal packet reads.
For strategy read `PLAN.md`; for the predict→verdict history read `ledger.md`.

**Last updated:** 2026-06-12 (third pass — triage layer mechanized + adversarially reviewed)
**Phase:** 0 — Apparatus (no models yet). **In progress.**

**Open PR:** #2 `process/delegation-triage` — the delegation-triage layer + validator +
skill + two /goal packets. Adversarially reviewed (D-005/D-006, both APPROVE-WITH-CHANGES,
fixes applied). Awaits Logan's merge (T3 load-bearing; branch protection requires it).

## What exists (this repo)

- `PLAN.md` — full strategy, committed as-is (do not edit outside phase gates).
- `LICENSE` — Apache-2.0, © 2026 Logan Rooks.
- `eval/lib/` — scoring core **ported** from scholardoc `ground_truth/lib`
  (normalize / matching / metrics / reports), imports rebased to `eval.lib`.
- `tests/` — 44 ported unit tests, **all passing** under `uv run pytest`.
  ruff + mypy clean.
- `eval/fixtures/` — JSON-only eval data: `validation_set.json` (130 error pairs
  / 77 correct words), `classified/` (75 OCR-quality batch files), `candidates/`
  (4 files, all <1MB), `test_yaml/` (2 unit-test fixtures).
- `docs/prior-findings.md` — distilled scholardoc empirical record, with
  provenance (file @ branch).
- `experiments/E1…E7/` — one pre-registered hypothesis + disconfirmer each
  (skeletons, not yet run). `experiments/_TEMPLATE.md` holds the §8 prereg fields.
- `runner/` — SSH-over-Tailscale + rsync **walking-skeleton**; `targets.toml`
  declares local-mac / dionysus / rental. No queue, no orchestrator (by design).
- `ledger.md` — append-only predict→verdict log (seeded with the scaffolding entry).
- CI (`.github/workflows/ci.yml`): ruff + mypy + pytest, no-PDF / no->1MB guard,
  the prereg-gate on PRs, and the **delegation-log validator** (schema + overkill
  guardrail on `delegation-log.jsonl`).
- `docs/delegation-triage.md` + `delegation-log.jsonl` — delegation triage rubric and
  append-only trace log (tier choice → disposition → review-gate verdicts →
  interventions → meta-audit). Enforced by `.github/scripts/validate_delegation_log.py`
  (+ `tests/test_validate_delegation_log.py`, 26 cases) and the in-repo skill
  `.claude/skills/delegation-triage/`. Every delegated subtask logs here.
- `docs/process/upstream-feedback.md` — append-only record of improvements to the
  /goal packet format and related skills, for later self-improvement workflows.
- `goal/` — packets: `corpus-acquisition.goal.md` (HUMAN-GATE on selection; zlibrary
  ≤10/day) and `checker-suite.goal.md` (Phase-0 gate item 5). Evidence files land in
  `goal/evidence/`.
- `.local/` (gitignored) — corpus inventory manifest + research notes produced by
  delegated exploration; never pushed.

## Sibling repos (created 2026-06-12, both CI green)

- `loganrooks/scholar-schema` — scholargt fork @ 6cdd98b, import name `scholargt`,
  293/293 tests, schema-regen byte-identity check.
- `loganrooks/scriptorium` — schema-first synthetic-corpus generator; tectonic render
  verified on the Republic/Bendis fixture page. PyPI name taken; dist name TBD.

## What does NOT exist yet

- `pipeline/` — empty by design in Phase 0 (no models).
- This repo does not yet **pin** scholar-schema/scriptorium versions (scriptorium's
  scholar-schema git dep is commented out pending a resolvable pin).
- The synthetic corpus (GT-A, beyond the 1 fixture page), GT-B aligner, acquired
  corpus — not started; see `goal/corpus-acquisition.goal.md`.
- A self-hosted dionysus CI runner — deferred (PLAN §14 item 6).

## Carried but DEFERRED

- `eval.lib.normalize.scholar_doc_to_elements()` / `_position_to_page()` — port the
  adapter contract for the future pipeline; import target does not exist yet, so
  these are `# pragma: no cover` and untested until `pipeline/` lands.

## Left behind from scholardoc `ground_truth/lib` (and why)

- `tests/integration/test_ground_truth_regression.py` — exercises
  `scholardoc.convert` + `scholar_doc_to_elements` over real PDFs and verified GT
  documents. Both dependencies are the rotted pipeline we deliberately did **not**
  port; the test self-skips when no verified GT exists. Re-port when `pipeline/`
  and accepted GT documents exist.

## Next gate items (PLAN §10 Phase 0 — what closes this phase)

Phase 0 gate (all must be *shipped, runnable artifacts*, not "design complete"):

1. CI green on all three repos (this repo: green ✅; schema + generator: not created).
2. The same job runs on **Mac and dionysus** through the execution abstraction
   (runner is a skeleton only — not yet demonstrated end-to-end on dionysus).
3. ≥500 synthetic GT pages across strata, incl. ≥1 sous-rature and ≥1 multi-register
   template (needs the generator repo — not started).
4. ≥5 accepted GT-B pairs (needs the aligner + corpus acquisition — not started).
5. Checker suite runs end-to-end on GT-A (needs GT-A — not started).

**Immediate next step:** execute the two `goal/` packets (corpus acquisition awaits
Logan's HUMAN-GATE on the selection; checker suite is unblocked), then make the runner
skeleton actually execute a trivial job on dionysus.
