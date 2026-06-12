# STATE — what is true now

**Authority:** this file is *what is true now* (PLAN.md §11.2). Updated every
working session; the first thing a fresh agent session or /goal packet reads.
For strategy read `PLAN.md`; for the predict→verdict history read `ledger.md`.

**Last updated:** 2026-06-12
**Phase:** 0 — Apparatus (no models yet). **In progress.**

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
  and the prereg-gate on PRs.

## What does NOT exist yet

- `pipeline/` — empty by design in Phase 0 (no models).
- The schema repo (`scholar-schema`) and corpus generator (`scriptorium`) — separate
  repos in the topology (PLAN §11.1); this repo will pin them once they exist.
- The synthetic corpus (GT-A), GT-B aligner, acquired corpus — not started.
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

**Immediate next step:** stand up the other two repos (`scholar-schema`,
`scriptorium`) with the same CI scaffolding, then make the runner skeleton actually
execute a trivial job on dionysus.
