# Evidence — D-250 autonomous drive

**Work order:** `goal/codex-drive.goal.md`
**Executor:** D-250 (`gpt-5.6-sol`, Codex)
**Started:** 2026-08-12 (America/Toronto)

Claims below are scoped to the named receipts. Corpus text and acquisition provenance
are intentionally excluded.

## W1 — PR #3 checker-suite certification and merge

**Disposition: DONE — CERTIFIED-READY and merged.**

- **Measured, initial verdict:** `NOT-CERTIFIED` on evidence integrity, not checker
  behavior. D-251 and D-252 found stale CI provenance and four-checker CLI transcripts
  in `goal/evidence/checker-suite.md`; neither found a blocker/major checker-code defect.
- **Fix:** commit `bd28b446fa48b195fc60bca0168d01eb5512c058` corrected the evidence,
  made all examples five-checker outputs, and aligned structural-contract wording with
  the depth-uniform implementation.
- **Measured, local validation at the fixed tip:** `.venv/bin/pytest -q` → 215 passed,
  1 intentional xfail; `.venv/bin/ruff check --no-cache .` → clean;
  `.venv/bin/mypy --cache-dir /tmp/agentic-ocr-pr3fix-mypy-cache-final .` → no issues
  in 40 source files; `git diff --cached --check` → exit 0.
- **Measured, exact-head CI:** `gh pr checks 3 --repo rookslog/agentic-ocr --watch`
  → all five checks passed on head `bd28b44`; CI run
  <https://github.com/rookslog/agentic-ocr/actions/runs/31661148998>, labeler run
  <https://github.com/rookslog/agentic-ocr/actions/runs/31661148157>.
- **Merge receipt:** `gh pr merge 3 --repo rookslog/agentic-ocr --merge` → PR #3
  `MERGED`; `gh pr view 3 --json state,mergedAt,mergeCommit,headRefOid` returned merge
  commit `e57ec0f49adb2f3820c9d2d89e9f5af56a85055b` for certified head `bd28b44`.
- **Known boundary retained:** text-fidelity remains machine-marked
  `reward_ready=false`; the farmable minor-defect aggregate is not approved for reward
  use. W1 certifies the Phase-0 checker/CI scope, not later reward-service fitness.

## W2 — PR #5 GT-B aligner review and merge

**Disposition: BLOCKED-ON-HUMAN — mechanical repair checkpointed; PR remains draft.**

- **Measured, three-lens verdict:** D-253 correctness/exploit, D-254 calibration,
  and D-255 test adequacy each returned `REQUEST-CHANGES`. Root reproduced the
  load-bearing false-accept: 15 candidate tokens were reused by overlapping anchors
  to credit 55 GT tokens (`coverage=0.846154`, legacy `accepted=true`). Other reproduced
  findings included anchorless tiny accepts, unreliable-page spillover, unvalidated
  cached anchors, omitted default test discovery, a vacuous zero-anchor regression,
  and valid single-quoted EPUB XML rejected by the regex parser.
- **Fix checkpoint:** commit `910cf8b2d03a3dce3752a6ead7afb835e29d9907`
  (`fix(gtb): close mechanical review findings`) makes anchor spans injective on both
  streams, requires anchor evidence for the legacy flag, validates parameters and cached
  chains, prevents prior-page ends from contaminating successors, parses EPUB metadata as
  XML, adds extraction/property/exploit tests, and includes `eval/gtb` in default pytest
  discovery. D-257 returned `MECHANICAL-CLOSURE-CLEAN` after one additional boundary
  spillover was reproduced and fixed.
- **Measured, final local gates at `910cf8b`:**
  `UV_CACHE_DIR=/tmp/agentic-ocr-w2-uv-cache uv run pytest -p no:cacheprovider -o addopts=`
  → 273 passed, 1 intentional xfail; `uv run ruff check --no-cache .` → clean;
  `uv run mypy --cache-dir /tmp/agentic-ocr-w2-commit-mypy .` → no issues in 47 files;
  `git diff --cached --check` before commit → exit 0.
- **Measured, real numeric smoke under the repaired code:** the three recorded candidates
  produced GT recall `0.966950`, `0.992694`, and `0.977653`; the two unrelated controls
  produced `0.005421` and `0.011782`. The page-key smoke exited 0 with 40/40 pilot keys
  reliable. Its first post-repair run falsified an old nondecreasing-end oracle; a
  numeric-only probe showed later anchors advancing inside a prior extrapolated tail, so
  the local smoke now asserts nondecreasing starts and does not demand unsupported spillover.
- **Push receipt:** `git push origin feat/gtb-aligner` advanced draft PR #5 from
  `721af22` to `910cf8b`; `gh pr view 5` returned `isDraft=true`, `OPEN`, `MERGEABLE`,
  and `BEHIND`. Exact-head CI was not observed to completion before the forced stop;
  only labeler run <https://github.com/rookslog/agentic-ocr/actions/runs/31663377237>
  was queued at the final check. The PR was intentionally neither readied nor merged.
- **Reasoned, open contract:** GT recall cannot distinguish exact GT from exact GT plus
  unrelated material, duplication, or substantial reordering. Synthetic probes still make
  those cases pass the legacy recall flag; changing that flag's schema is not licensed by
  the recorded three positives and two extreme controls.

### Batched owner decision — GT-B certification semantics

- **Decision:** what may produce a certified `ACCEPT` for gate clause 4 while realistic
  same-work/compound/reordered hard negatives are not calibrated?
- **Recommendation:** adopt a versioned tri-state Phase-0 result: recall ≥0.60 is necessary;
  integrity failures `REJECT`; recall-passing pairs are `REVIEW_REQUIRED`; reserve mechanical
  `ACCEPT` until a preregistered labeled calibration promotes candidate-coverage/length/order
  diagnostics into gates. This is the D-256 Sol High recommendation, accepted here as a
  proposal rather than authority.
- **Alternatives:** (1) calibrate a bidirectional/symmetric gate now on a new labeled set;
  (2) explicitly declare compound, duplicated, and substantially reordered candidates valid
  GT-B pairs and retain recall-only `ACCEPT`.
- **Load-bearing assumption:** “GT-B pair” means edition correspondence suitable as an
  answer key, not merely containment of the GT somewhere in a larger candidate.
- **What flips the recommendation:** an owner ruling that containment is the intended gate,
  or a preregistered calibration with legitimate edition variation plus compound,
  duplicate, reordered, abridged, and near-boundary negatives that licenses mechanical
  cutoffs. Until then PR #5 must remain draft.

## W3 — satellite PRs and corpus-starter PR

**Disposition: PARTIAL — three authorized merges done; corpus-starter PR not opened.**

- `rookslog/scholar-schema` PR #1: exact head `1b22b5d`, five checks passed in
  <https://github.com/rookslog/scholar-schema/actions/runs/31236422860>; merged as
  `306d6a150d45aa0b0d2a6c8854fd3ad18688e221`.
- `rookslog/scriptorium` PR #2: exact head `0141992`, both checks passed in
  <https://github.com/rookslog/scriptorium/actions/runs/31236602700>; merged as
  `6c8b185ea5da730563d5ec2651873cb696feb9db`.
- `rookslog/agentic-ocr` PR #4: GitHub first refused the stale branch as behind; the
  authorized update-branch operation produced head `fbde8ec`. All five checks passed in
  <https://github.com/rookslog/agentic-ocr/actions/runs/31662807415> and labeler run
  <https://github.com/rookslog/agentic-ocr/actions/runs/31662806570>; merged as
  `c69a6a3a563c8bf97f41df4bbd8efee24a097191`, independently matched by `git ls-remote`.
- `feat/corpus-starter`: primary checkout stayed on the required branch. A clean merge
  preview against current `origin/main` produced tree `a834d61f…`, but the actual reconcile,
  PR open, CI, and merge were not started before the forced stop.

## W4 — ADR-0002 post-G1 enforcement cascade

**Disposition: PENDING — not started before forced stop.**

## W5 — local-mac + dionysus smoke

**Disposition: PENDING — authorized, not run before forced stop.**

## W6 — GT-B pairs 4–5

**Disposition: PENDING — no owned/PD mining or fallback acquisition started.**

## W7 — scriptorium stretch

**Disposition: PENDING — not started.**

## Stop condition

The harness reported `Codex Tend pressure: weekly hard limit reached` after the final W2
validation commands. Per that binding stop, no W4–W7 work or additional campaign launch was
started. The safely parked state is: W1 done; W2 mechanical repair committed/pushed but
contract-blocked and draft; W3 three merges done with corpus-starter reconciliation pending.
