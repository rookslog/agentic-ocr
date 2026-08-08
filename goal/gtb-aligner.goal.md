# /goal packet — GT-B aligner (eval/gtb)

**Objective:** an anchor-based scan-PDF↔EPUB text aligner with a **mechanical
alignment-coverage statistic** that decides GT-B pair accept/reject with NO human judgment
(PLAN.md:139). Phase-0 worklist item 1 (`goal/phase-0-drive.goal.md`); advances gate
clause 4 (≥5 accepted GT-B pairs). Pure code over already-owned files; no human gate to start.

**Read first (in order):**
- `STATE.md`; `PLAN.md` around :139 (the GT-B anchor-align + coverage method).
- `.local/eval/og_smoke.py` — the existing Of-Grammatology smoke (baseline **0.904 recall /
  0.870 precision**). Understand what scan-side text it has (OCR text layer? a prepared
  text?) and how it matches BEFORE replacing it — the aligner generalizes this smoke.
- `corpus/` staged pairs (`of-grammatology` edition-confirmed; `specters-of-marx`,
  `totality-and-infinity` edition-uncertain) + their `provenance.json`.
- `docs/delegation-triage.md` — if you sub-delegate, follow the rubric + log it.

**Allowed scope:** `eval/gtb/` (NEW module), `.local/eval/` (scratch/smoke),
`goal/evidence/gtb-aligner.md`, `delegation-log.jsonl` (append only), `pyproject.toml`
(add a PDF/EPUB parse dep if needed). Co-locate tests in `eval/gtb/` (e.g.
`eval/gtb/test_align.py`).

**Forbidden:**
- Touching `eval/checkers/`, `tests/`, `.github/` — **G1-locked** by the open checker-suite
  PR #3 (the new module is distinct from `eval/checkers/align.py`, the region-IoU checker).
- Any corpus bytes / PDF / EPUB committed to git (read the gitignored staged copies; never
  commit them). Any zlibrary id / acquisition provenance in a **tracked** file (provenance
  stays in gitignored `corpus/`).
- Extending acquisition (G2/G3): build + smoke on the **3 owned pairs only**.
- Loosening the accept threshold to make a pair pass.

**Milestones:**
1. **Anchor extraction** — unique shared n-grams between scan-side text and EPUB text as
   alignment anchors.
2. **DP fill** — dynamic-programming alignment between consecutive anchors (PLAN.md:139).
3. **Coverage statistic + accept/reject** — a mechanical alignment-coverage number + a
   threshold → accept/reject, no human judgment. **Calibrate the threshold against the OG
   baseline:** the confirmed `of-grammatology` pair must ACCEPT; a deliberately-mismatched
   pair (negative control) must REJECT. Do not trust reject verdicts until the OG-accepts /
   mismatch-rejects calibration holds.
4. **Smoke on the 3 staged pairs** — run deterministically; report per-pair coverage +
   accept/reject honestly (specters/totality are edition-uncertain — report what the
   statistic says, don't force a verdict).

**Verification:** deterministic run on the 3 pairs; OG accepts at the calibrated threshold;
a mismatch negative-control rejects; co-located tests green; ruff + mypy clean. Fill
`goal/evidence/gtb-aligner.md` (coverage table + threshold rationale + negative control) and
echo the run output.

**Pause / escalate when:** reaching **≥5 accepted** is impossible on owned files (only 3
candidates, 2 edition-uncertain) — this is the expected **G3 stall** (zlibrary acquisition).
Build + smoke the aligner, surface the stall, do NOT try to acquire. Any question about what
"coverage" should *mean* schema-wise → escalate, don't invent.

**Budget:** build ≤110k tokens; one focused session.
