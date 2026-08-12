# /goal — codex drive handoff (D-250)

**Issued:** 2026-08-12 by the Claude drive session (delegation D-250 in
`delegation-log.jsonl`), on Logan's direction. **Executor:** a codex session
(gpt-5.6-sol, ultra reasoning) driving this repo autonomously.
**Contract:** `AGENTS.md` binds everything here. Read `STATE.md` before starting.

## Terminal condition

Work the ordered list below until each item is DONE or BLOCKED-ON-HUMAN. Batch
human questions; never idle on one item while another is unblocked. On session
end (or when the list is exhausted), write `goal/evidence/codex-drive.md`:
per-item disposition, receipts (commands, run URLs, merge SHAs), and anything
learned that changes STATE.md — then update STATE.md itself.

## Ordered worklist

### W1 — Certify and merge PR #3 (checker suite) — gate AG-1
- Worktree: `/Users/rookslog/Development/agentic-ocr-pr3fix` (branch
  `feat/checker-suite` @ `4b9d7ea`). PR #3 is CI-green and MERGEABLE.
- Task: a certification review pass — the recorded round-4/5/6 conditions are in
  `delegation-log.jsonl` rows D-243..D-246 (spot_check fields carry the findings
  and adjudications). Check blocker+major closure from code/doc, judge the
  self-referential attestation wording in `goal/evidence/checker-suite.md`
  (in-branch), and sweep the final commit `4b9d7ea` for new surface.
- Verdict contract: **CERTIFIED-READY** or **NOT-CERTIFIED + findings**.
- On CERTIFIED-READY: merge PR #3 via `gh pr merge 3 --merge` (merge-commit
  sanctioned; agential merge authorized 2026-08-01, re-confirmed 2026-08-07).
- On findings: fix in the worktree, re-run the full validation set, re-verify
  your own findings closed, then merge. A finding needing design judgment the
  packet doesn't cover → BLOCKED-ON-HUMAN, move on.

### W2 — Review, fix, and merge PR #5 (eval/gtb aligner) — gate AG-6
- Branch `feat/gtb-aligner` (draft PR #5), evidence `goal/evidence/gtb-aligner.md`,
  spec `goal/gtb-aligner.goal.md`.
- Three review lenses, all mandatory: (1) **correctness/exploit** — can a
  mismatched or degenerate pair force ACCEPT; can page-key reliability flags lie;
  (2) **calibration integrity** — threshold 0.60 + 5-gram choices vs the recorded
  probe; D-GTB-1-class regressions (the negative-control bug class); (3) **test
  adequacy** — do the 34 co-located tests pin the claimed properties.
- Verdict contract: APPROVE / APPROVE-WITH-CHANGES / REQUEST-CHANGES, findings
  severity-ranked per lens. This module decides gate-clause-4 pair acceptance;
  a false-ACCEPT poisons every downstream experiment — that is the expensive miss.
- Apply fixes on the branch, un-draft PR #5 (`gh pr ready 5`), merge on green.

### W3 — Merge the green satellite PRs
- `rookslog/scholar-schema` PR #1 (docs) and `rookslog/scriptorium` PR #2
  (schema pin) — both CI-green, merge any time.
- `rookslog/agentic-ocr` PR #4 (ADR cascade, pre-G1 half) — merge after W1.
- Then open a PR for `feat/corpus-starter` (this branch — state sync + corpus
  starter docs + this packet) and merge on green. Expect append-conflicts in
  `delegation-log.jsonl`/`STATE.md` against merged work; resolve by keeping both
  sides (the log is append-only).

### W4 — Post-G1 half of the ADR-0002 cascade — gate AG-7 (unlocked by W1)
Read `docs/adr/0002-schema-evolution-policy.md` first. Build, in this repo:
1. A vocabulary module asserting vocabulary ⊆ pinned schema enums.
2. A `SchemaVersionChecker` (fails on unpinned/mismatched `SCHEMA_VERSION`).
3. The one-seam-per-schema grep guard in CI.
4. **Both enforcement probes**: on a throwaway branch, commit a deliberate
   violation, verify CI goes red, record the run URL in the evidence doc, then
   delete the branch. A probe that never flipped CI red is not evidence.

### W5 — dionysus cross-target smoke — gate clause 2
- Run the same trivial job on local-mac AND dionysus through `runner/`
  (`python -m runner.run …`, targets in `runner/targets.toml`; dionysus is
  SSH-over-Tailscale, authorized by ruling H-1). Record both outputs + exit
  codes in the evidence doc. Needs network/SSH escalation in your sandbox —
  if the harness blocks it, mark BLOCKED-ON-HUMAN (approval), move on.

### W6 — GT-B pairs 4–5 from the owned library (gate clause 4, ruled autonomous)
- Pair 4: Otherwise Than Being — owned scan at
  `~/Library/CloudStorage/OneDrive-…/Reading Now/Levinas/Levinas_OtherwiseThanBeing.pdf`
  (locate exactly; the stem is `Levinas_OtherwiseThanBeing.pdf`) + the already
  staged EPUB in `corpus/`. Stage copy-only with sha256 provenance per the
  existing `corpus/` manifest pattern.
- Run the aligner + **negative controls** on each candidate pair; ACCEPT needs
  coverage ≥ 0.60 and controls REJECTing. Mine the owned library for a 5th pair
  the same way. Report stats (numbers only — no corpus text) in the evidence doc.
- Pairs still short of 5 after owned + PD mining → record the shortfall; the
  zlibrary gate (H-2) is Logan's alone.

### W7 (stretch) — scriptorium engine packet, ≥500 GT pages (gate clause 3)
Only if W1–W6 are dispositioned. Scope it first as a written plan in the
scriptorium repo (the sous-rature template spike precedes bulk generation);
do not bulk-generate against an unreviewed plan.

## Explicitly NOT yours

- The PD-lane **content-filter probe** (tests a Claude-platform behavior; runs
  in a Claude session).
- Anything touching **zlibrary** (H-2 human gate).
- Editing `PLAN.md`.
- New standing config (CI required-check changes, branch-protection edits,
  account settings) — propose in the evidence doc instead.

## Reporting

Every merge, fix-commit, and verdict gets one line in
`goal/evidence/codex-drive.md` with its receipt. Sub-delegations (if you spawn
any) get `delegation-log.jsonl` rows — run the validator before committing.
STATE.md updated at the end (or at any natural checkpoint). Findings you
disposition yourself must state the check that licensed the disposition.
