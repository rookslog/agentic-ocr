# STATE — what is true now

**Authority:** this file is *what is true now* (PLAN.md §11.2). Updated every
working session; the first thing a fresh agent session or /goal packet reads.
For strategy read `PLAN.md`; for the predict→verdict history read `ledger.md`.

**Last updated:** 2026-08-12 (eighth pass — D-250 parked on weekly hard-limit pressure;
W1 merged, W2 mechanically repaired but contract-blocked, and three W3 PRs merged)
**Phase:** 0 — Apparatus (no models in the pipeline; model-touching *probes* are
operator-sanctioned case-by-case — see "Vision-transcription pilot" below). **In progress.**

## Parked drive state / next-action owner

- **D-250 is safely parked** after the harness reported `Codex Tend pressure: weekly hard
  limit reached`. Do not resume campaign work until launch authority is available. The
  resumption source is `goal/evidence/codex-drive.md`.
- **W1 DONE:** checker-suite PR #3 was certified at exact head `bd28b44` and merged as
  `e57ec0f49adb2f3820c9d2d89e9f5af56a85055b`.
- **W2 BLOCKED-ON-HUMAN:** the three-lens review was repaired and D-257 returned
  `MECHANICAL-CLOSURE-CLEAN` at `910cf8b`; PR #5 remains draft pending the GT-B
  certification-semantics decision. Exact-head CI was not observed to completion.
- **W3 PARTIAL:** scholar-schema PR #1, scriptorium PR #2, and agentic-ocr PR #4 are
  merged. `feat/corpus-starter` still needs reconciliation, PR creation, CI, and merge.
- **W4–W7 were not started** before the forced stop.
- **D-248 and D-249 were both CANCELLED** — the two reviewer agents died 2026-08-07 on a
  platform session-limit API error (D-248 mid-review, D-249 before producing anything).
  Their gates re-enter as W1/W2 above; log rows carry the details.
- **AG-7 pre-G1 half: DONE 2026-08-07** — scholar-schema `v0.1.0` tag live @ `8610d5e`;
  this repo pinned (PR #4 merged); scriptorium pinned (PR #2 merged); legacy-fixture
  labels in `eval/fixtures/README.md` (PR #4 merged). Post-G1 half is W4.

## Pull requests and mainline

- **Open:** agentic-ocr PR #5 remains draft at `910cf8b`. Measured at the last live check:
  `OPEN`, `MERGEABLE`, and `BEHIND`; only its labeler run was queued, so no exact-head
  CI-green claim is made. Mechanical review is clean; the contract decision above blocks
  readying or merging it.
- **Merged by D-250:** agentic-ocr PR #3 as `e57ec0f`, agentic-ocr PR #4 as `c69a6a3`,
  scholar-schema PR #1 as `306d6a1`, and scriptorium PR #2 as `6c8b185`. A fresh
  `git ls-remote` matched agentic-ocr `main` to the recorded PR #4 merge SHA.
- **Still to open:** the corpus-starter PR, after reconciling this branch with current
  `origin/main` on an authorized resume.

## Operator rulings (2026-08-07, batched decision-presentation ask)

1. **Vision arm / copyright fork → PD lane now + filter probe.** Public-domain pair
   sourcing (archive.org scans + Gutenberg/Perseus texts) joins corpus expansion; first a
   ~3-page probe (synthetic GT-A page + PD pages through the unchanged vision contract)
   tests the load-bearing assumption that the output filter is copyright-specific. PD pairs
   count toward gate clause 4 (reading of PLAN.md:248 — recorded, contestable at the gate).
2. **ADR-0002 → Accepted, full cascade authorized** (one approval covers tag, pins,
   labels, post-G1 CI mechanisms, both enforcement probes). Status flipped in the ADR.
3. **H-1 dionysus SSH → granted**: scoped Bash allow-rule (ssh/rsync to dionysus)
   authorized; installing via settings. Cross-target smoke runs once the rule is live.
4. **Acquisition authority (delegate ruling, recorded not asked):** owned-library mining is
   autonomous (copy-only staging + provenance, report-after — the already-approved pattern);
   zlibrary (H-2) stays gated on Logan and opens only if owned + PD mining leaves clause 4
   short of 5 pairs.
   - **UPDATE 2026-08-12 (operator, direct):** H-2 opened to the D-250 codex drive as a
     capped fallback — the drive may run zlibrary-mcp once owned + PD mining is exhausted,
     ≤10 downloads/day, bytes/provenance constraints unchanged. The fallback *ordering* from
     the original ruling is retained; only the operator (was: Logan-only) changed to the
     delegated drive. See `goal/codex-drive.goal.md` W6.

## Vision-transcription pilot (2026-07-31) — the run and its finding

Operator-sanctioned probe (NOT a prereg'd experiment; no verdict claimed into
`experiments/`). 40 stratified page PNGs from the 3 then-recorded GT-B candidates;
4 model×effort
cells; 36 workers launched. **RUN HALTED: 32/36 workers killed by platform output
filtering on long verbatim reproduction of in-copyright text** — across both model
families and all effort levels; only one short front-matter fragment survived (n=1 usable
page per cell — insufficient for scoring). Full log: `.local/vision-pilot/RUNLOG.md`
(local-only). Implication: the frontier-API transcription arm cannot run on in-copyright
books via this provider path — hence ruling 1 above. Unaffected: everything in Phase 0
(zero model calls needed), local-model E2 contenders, checker-based eval. The concat-limit
probe (designed 07-31) never ran; its design + stitched images are retained for a
permissible corpus.

## What exists (this repo)

- `PLAN.md` — full strategy, committed as-is (edited only at phase gates).
- `eval/lib/` — scoring core ported from scholardoc (normalize/matching/metrics/reports).
- `eval/checkers/` — deterministic checker suite, merged to `main` by PR #3. The
  text-fidelity boundary remains machine-marked `reward_ready=false`.
- `eval/gtb/` — **GT-B aligner + page-key layer** at draft PR #5 head `910cf8b`:
  span-disjoint anchors, validated cached chains/parameters, candidate-side diagnostics,
  non-contaminating page keys, XML EPUB extraction, and default-suite discovery. The
  repaired branch has 58 GT-B tests. Measured real-pair recalls were
  0.966950/0.992694/0.977653 and controls 0.005421/0.011782, but those high recalls are
  not certified pair accepts while the recall-only contract decision remains open.
  Evidence: `goal/evidence/gtb-aligner.md` and `goal/evidence/codex-drive.md`.
- `docs/adr/` — ADR-0001 (GT schema layering; Accepted) + ADR-0002 (schema-evolution
  policy; **Accepted 2026-08-07**, cascade in flight).
- `tests/` plus co-located eval tests — exact-head W1 run: 215 passed + 1 intentional
  xfail; exact-head W2 repair run: 273 passed + 1 intentional xfail. See drive evidence
  for the bounded commands and heads.
- `eval/fixtures/` — JSON-only eval data (legacy labeling lands with the AG-7 cascade).
- `docs/prior-findings.md`, `experiments/E1…E7/` skeletons, `runner/` walking skeleton,
  `docs/delegation-triage.md` + `delegation-log.jsonl` (67 delegations / 124 events;
  validator green with 0 warnings), `docs/process/upstream-feedback.md`.
- `ledger.md` — rows 4–7 appended 2026-08-07 (corpus starter, aligner, vision pilot,
  ADR-0002 — the first three retroactive, labeled as such); row 8 appends the W2
  mechanical-repair result and corrects row 5's recall→pair-acceptance overclaim.
- `corpus/` (gitignored) — 12 books / 15 files staged with sha256 provenance; 3 GT-B
  candidate pairs pending the W2 certification-semantics decision.
- `.local/` (gitignored) — corpus manifest, smokes, vision-pilot, research notes.

## Sibling repos (org is `rookslog`; older docs said loganrooks, redirect works)

- `rookslog/scholar-schema` — scholargt fork, 293/293 tests. Tag `v0.1.0` @ `8610d5e`
  (CI-green commit) pushed 2026-08-07; docs PR #1 merged as `306d6a1`.
- `rookslog/scriptorium` — synthetic-corpus generator; render verified on the
  Republic/Bendis fixture page. scholar-schema pinned at v0.1.0 via `[tool.uv.sources]`
  (PR #2 merged as `6c8b185`; recorded branch gates: 15 passed / 2 skipped,
  ruff+mypy clean).

## What does NOT exist yet

- `pipeline/` — empty by design in Phase 0.
- The ≥500-page synthetic corpus (GT-A) — the scriptorium engine build is the largest
  remaining pure-build item (own packet, executed in the scriptorium repo).
- GT-B pairs 4 & 5 — Otherwise Than Being flagged as pair 4 (owned scan on OneDrive +
  staged EPUB); owned-library mining authorized (ruling 4).
- The dionysus half of gate clause 2 — unblocked by ruling 3, smoke not yet run.
- PD corpus lane — approved (ruling 1), not started.

## Carried but DEFERRED

- `eval.lib.normalize.scholar_doc_to_elements()` — untested until `pipeline/` lands.
- scholardoc GT regression test — re-port when `pipeline/` + accepted GT documents exist.

## Phase-0 gate scoreboard (PLAN.md:248, audited 2026-08-07)

1. **CI green on all three repos — DONE** (all three verified green).
2. Mac + dionysus through the abstraction — dionysus half unblocked (ruling 3), smoke owed.
3. ≥500 synthetic GT pages — **not started**; scriptorium engine packet is next after the
   in-flight gates.
4. ≥5 accepted GT-B pairs — **certified count unresolved**: three candidates have high
   measured GT recall, but review proved recall alone can false-accept compound, duplicated,
   or reordered inputs. Resolve the W2 semantics decision before counting accepts; pair
   mining remains unstarted.
5. Checker suite e2e on GT-A — checker suite merged; full-corpus run waits on item 3.

**Immediate next steps on an authorized resume:** decide W2 certification semantics;
reconcile/open/merge the corpus-starter PR; then execute W4→W6 in packet order (W7 stretch).
The PD content-filter probe remains outside D-250 scope. Do not start any of these while the
weekly hard-limit stop remains active.
