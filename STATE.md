# STATE — what is true now

**Authority:** this file is *what is true now* (PLAN.md §11.2). Updated every
working session; the first thing a fresh agent session or /goal packet reads.
For strategy read `PLAN.md`; for the predict→verdict history read `ledger.md`.

**Last updated:** 2026-08-12 (seventh pass — codex drive handoff: D-248/D-249 both
cancelled on a platform session limit 2026-08-07; the whole drive re-routed cross-vendor
as D-250; pre-G1 cascade half executed 08-07 after the sixth pass was written)
**Phase:** 0 — Apparatus (no models in the pipeline; model-touching *probes* are
operator-sanctioned case-by-case — see "Vision-transcription pilot" below). **In progress.**

## In flight RIGHT NOW (next-action owner — the D-247 stall fix)

- **D-250 — codex drive handoff** (operator-directed 2026-08-12): a codex session
  (gpt-5.6-sol, ultra) owns the drive per `goal/codex-drive.goal.md` under the new
  `AGENTS.md` contract. W1 = PR #3 certification+merge (AG-1), W2 = eval/gtb review+merge
  (AG-6), W3 = satellite merges, W4 = post-G1 cascade (AG-7), W5 = dionysus smoke,
  W6 = GT-B pairs 4–5. Evidence lands in `goal/evidence/codex-drive.md`.
- **D-248 and D-249 were both CANCELLED** — the two reviewer agents died 2026-08-07 on a
  platform session-limit API error (D-248 mid-review, D-249 before producing anything).
  Their gates re-enter as W1/W2 above; log rows carry the details.
- **AG-7 pre-G1 half: DONE 2026-08-07** — scholar-schema `v0.1.0` tag live @ `8610d5e`;
  this repo pinned (PR #4); scriptorium pinned (its PR #2); legacy-fixture labels in
  `eval/fixtures/README.md` (PR #4). Post-G1 half is W4.

## Open PRs

All CI-green as of 2026-08-12 (`gh pr checks`, all five):

- #3 `feat/checker-suite` — deterministic checker suite (`eval/checkers/`), hardened
  through **seven adversarial rounds** (D-237 exploit harness; rounds 3–6 fix commits
  0b466d3…4b9d7ea on 2026-07-31/08-01; two executed BLOCKER reproductions found and closed,
  incl. a reward-farming construction). `MERGEABLE`; certification (now D-250 W1) is the
  last gate before the AG-1 agential merge. Evidence: `goal/evidence/checker-suite.md`
  (in-branch). Certification launches D-247 and D-248 were both **cancelled** (session-end
  stall, then platform session limit) — the D-210 stall pattern, twice.
- #4 `chore/adr-cascade` — ADR-0001+0002 (Accepted) + pre-G1 cascade (schema pin v0.1.0,
  legacy-fixture labels). Merge after #3 (D-250 W3).
- #5 `feat/gtb-aligner` (draft) — `eval/gtb/` committed 721af22 to protect the work;
  T3 review owed (D-250 W2).
- scholar-schema #1 (docs) and scriptorium #2 (schema pin) — green, merge any time.

**Merged to main:** #2 `process/delegation-triage` (2026-06-13).

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

## Vision-transcription pilot (2026-07-31) — the run and its finding

Operator-sanctioned probe (NOT a prereg'd experiment; no verdict claimed into
`experiments/`). 40 stratified page PNGs from the 3 accepted GT-B pairs; 4 model×effort
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
- `eval/checkers/` — deterministic checker suite (PR #3; see Open PRs).
- `eval/gtb/` — **GT-B aligner + page-key layer** (branch `feat/gtb-aligner`): anchor
  extraction (unique 5-grams + LIS), DP gap fill, mechanical coverage statistic with
  calibrated accept threshold 0.60; per-PDF-page answer-key slicing with reliability
  floors. All 3 owned pairs ACCEPT (0.9575/0.9927/0.9777); both cross-book negative
  controls REJECT (0.0054/0.0118); 34 co-located tests. Under first T3 review (D-249).
  Evidence: `goal/evidence/gtb-aligner.md`.
- `docs/adr/` — ADR-0001 (GT schema layering; Accepted) + ADR-0002 (schema-evolution
  policy; **Accepted 2026-08-07**, cascade in flight).
- `tests/` — 44 ported unit tests + validator tests; full suite green under `uv run pytest`.
- `eval/fixtures/` — JSON-only eval data (legacy labeling lands with the AG-7 cascade).
- `docs/prior-findings.md`, `experiments/E1…E7/` skeletons, `runner/` walking skeleton,
  `docs/delegation-triage.md` + `delegation-log.jsonl` (59 delegations traced, validator
  green), `docs/process/upstream-feedback.md` — as at the fifth pass.
- `ledger.md` — rows 4–7 appended 2026-08-07 (corpus starter, aligner, vision pilot,
  ADR-0002 — the first three retroactive, labeled as such).
- `corpus/` (gitignored) — 12 books / 15 files staged with sha256 provenance; 3 GT-B pairs.
- `.local/` (gitignored) — corpus manifest, smokes, vision-pilot, research notes.

## Sibling repos (both CI green — org is `rookslog`; older docs said loganrooks, redirect works)

- `rookslog/scholar-schema` — scholargt fork, 293/293 tests. Tag `v0.1.0` @ `8610d5e`
  (CI-green commit) pushed 2026-08-07; docs PR #1 open.
- `rookslog/scriptorium` — synthetic-corpus generator; render verified on the
  Republic/Bendis fixture page. scholar-schema pinned at v0.1.0 via `[tool.uv.sources]`
  (its PR #2; 15 passed / 2 skipped, ruff+mypy clean).

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
4. ≥5 accepted GT-B pairs — **3/5**; paths: OTB staging, owned mining, PD lane; zlibrary
   only if still short.
5. Checker suite e2e on GT-A — built; blocked only on the D-248→AG-1 merge; full-corpus
   run waits on item 3.

**Immediate next steps:** the D-250 codex drive owns the worklist —
`goal/codex-drive.goal.md` W1→W6 (+W7 stretch). Retained Claude-side: the PD-lane
content-filter probe, anything zlibrary (H-2), and D-250 disposition on return.
