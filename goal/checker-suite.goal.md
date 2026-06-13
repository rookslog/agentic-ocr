# /goal packet — Deterministic checker suite (eval/checkers)

**Objective:** A deterministic, unit-test-style checker suite (olmOCR-2
unit-test-rewards pattern, PLAN §5) that scores any candidate pipeline output against
a GT page, running end-to-end on the scriptorium fixture page — Phase-0 gate item 5.

**Read first (in order):**
- `STATE.md`, `PLAN.md` §5 (GT + checker strategy), §4 (L0–L4 representation).
- `eval/lib/` (normalize/matching/metrics — reuse, don't duplicate).
- scholar-schema repo (the PageGT/DocumentGT contract) and scriptorium's
  `tests/fixtures/minimal_page.json` + its rendered PDF (the first GT-A page).
- `docs/delegation-triage.md` — if you delegate, follow the rubric and log it.

**Allowed scope:** `eval/checkers/` (new), `tests/`, `goal/evidence/checker-suite.md`,
`STATE.md` (status section only), `delegation-log.jsonl` (append only).

**Forbidden:**
- Modifying `eval/lib/` semantics (additive helpers OK; behavior changes need a T3 PR
  with reviewer ≠ author).
- Any checker that calls a model — this suite must be **deterministic**: same inputs,
  same verdicts, exit codes usable as CI assertions and (later) as reward signals.
- Editing preregs, `PLAN.md`, or past ledger/log rows.

**Data hygiene:** fixtures committed to git must be synthetic (scriptorium-derived) or
already-public eval JSON; never real-corpus pages.

**Milestones:**
1. **Checker contract** — `eval/checkers/__init__.py` defining the interface: a checker
   takes (candidate output, GT page) → `CheckResult{id, passed, severity, detail}`;
   a runner aggregates to a scorecard with exit code — done when the contract has
   docstrings + a trivial always-pass checker wired through the runner under pytest.
2. **Core checkers** (each its own module + tests; done when green on the fixture):
   a. text-fidelity: normalized n-gram containment of GT text in candidate text
      (reuse `eval/lib/normalize`);
   b. reading-order: GT block sequence preserved (Kendall-tau or LIS-based);
   c. footnote-anchor integrity: every GT anchor appears once, attached to the right
      block (fixture has the Bendis footnote);
   d. structure typing: GT block types (body/footnote/heading) recovered, scored as
      per-type precision/recall.
3. **Negative controls** — mutate the fixture candidate (drop the footnote anchor,
   swap two blocks, corrupt 5% of characters) and assert the corresponding checker
   *fails* — done when each checker demonstrably catches its target mutation and
   ignores the others.
4. **CLI + CI** — `uv run python -m eval.checkers --gt <json> --candidate <json>`
   prints the scorecard, exits non-zero on hard failures; wired into CI as a smoke run
   on the fixture — done when CI is green with the checker step visible in the log.

**Verification:** `uv run pytest tests/ -k checker` green; the CLI run on
(fixture GT, fixture-derived candidate) exits 0; on the mutated candidates exits ≠0.

**Completion evidence — file AND transcript:** fill `goal/evidence/checker-suite.md`
(scorecard output, negative-control table, CI link) and echo the pytest + CLI output
into the conversation.

**Pause / escalate when:** the checker contract seems to require schema changes
(scholar-schema is the contract's home — escalate, don't fork it locally); any checker
needs nondeterminism to work at all (that's a design question for the experiments
track, not a packet decision).

**Budget:** tokens: ≤140k; wallclock: one focused session; escalate-at: Milestone 2
incomplete after two sessions.
