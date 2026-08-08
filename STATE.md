# STATE — what is true now

**Authority:** this file is *what is true now* (PLAN.md §11.2). Updated every
working session; the first thing a fresh agent session or /goal packet reads.
For strategy read `PLAN.md`; for the predict→verdict history read `ledger.md`.

**Last updated:** 2026-08-07 (sixth pass — drive resumed after the 07-31/08-01 sessions;
operator rulings on vision arm / ADR-0002 / dionysus SSH; PR #3 certification re-launched;
aligner + ADRs finally committed)
**Phase:** 0 — Apparatus (no models in the pipeline; model-touching *probes* are
operator-sanctioned case-by-case — see "Vision-transcription pilot" below). **In progress.**

## In flight RIGHT NOW (next-action owners — the D-247 stall fix)

- **D-248** — PR #3 certification pass (re-launch of the cancelled D-247). Owner: reviewer
  agent, running. On certified-clean → **AG-1 agential merge executes immediately** (merge
  via `gh`, merge-commit, sanctioned 2026-08-01 and re-confirmed by the drive policy).
- **D-249** — 3-lens adversarial review of `eval/gtb/` (first T3-style review of the
  aligner). Owner: reviewer agent, running. On verdict → fixes → PR → agential merge (AG-6).
- **ADR-0002 cascade, pre-G1 half** (AG-7): scholar-schema `v0.1.0` tag → pyproject pin +
  scriptorium pin PR + legacy-fixture labels. Post-G1 half (CI mechanisms + enforcement
  probes) unlocks when PR #3 merges.

## Open PRs

- #3 `feat/checker-suite` — deterministic checker suite (`eval/checkers/`), now hardened
  through **seven adversarial rounds** (D-237 exploit harness; rounds 3–6 fix commits
  0b466d3…4b9d7ea on 2026-07-31/08-01; two executed BLOCKER reproductions found and closed,
  incl. a reward-farming construction). CI green, `MERGEABLE`; certification (D-248) is the
  last gate before the AG-1 agential merge. Evidence: `goal/evidence/checker-suite.md`
  (in-branch). D-247 (the 08-01 certification) was **cancelled** — session ended before any
  result; that 6-day silent stall is logged as a repeat of the D-210 pattern.

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

## Sibling repos (both CI green — verified via `gh run list` 2026-08-07)

- `loganrooks/scholar-schema` — scholargt fork, 293/293 tests. **No tags yet**; `v0.1.0`
  tag is the first cascade action (AG-7).
- `loganrooks/scriptorium` — synthetic-corpus generator; render verified on the
  Republic/Bendis fixture page. scholar-schema dep commented out pending the pin.

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

**Immediate next steps** (drive order): D-248 certification → AG-1 merge → post-G1 cascade
half; D-249 verdict → gtb fixes/PR; scholar-schema v0.1.0 tag + pins; dionysus smoke;
scriptorium engine packet; OTB staging + owned mining; PD lane + filter probe.
