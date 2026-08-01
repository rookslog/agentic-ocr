# Evidence — Deterministic checker suite (`eval/checkers`)

**Goal:** A deterministic, unit-test-style checker suite (olmOCR-2 unit-test-rewards
pattern, PLAN §5) that scores any candidate pipeline output against a GT page, running
end-to-end on the scriptorium fixture page — **Phase-0 gate item 5**.

**Status:** ✅ shipped. PR [#3](https://github.com/loganrooks/agentic-ocr/pull/3),
branch `feat/checker-suite`. Built this session (`e9ecce02`), adversarially reviewed
(D-008, reviewer ≠ author), review findings applied. Two further cross-vendor review
rounds followed — **D-237** (round 2, 8 findings) and **round 3** (both reviewers,
12 findings) — all applied; see §9.

---

## 1. What was built

| Component | File | Notes |
|---|---|---|
| Contract | `eval/checkers/base.py` | `CheckResult{id,passed,severity,detail,metrics}`, `Checker` ABC, `Scorecard` (exit code), `run_checkers()`, `AlwaysPassChecker` |
| PageGT accessors | `eval/checkers/pagegt.py` | read-only dict view; block-type classification (body/footnote/heading/other) |
| Normalizer | `eval/checkers/_normalize.py` | checker-local (eval/lib/normalize is element-, not string-oriented); n-gram helpers |
| Structural contract | `eval/checkers/contract.py` | validates the **raw** page dicts: unique region ids, depth cap, and a `reading_order` that is a complete, non-repeating, index-consistent list of strings |
| Region alignment | `eval/checkers/align.py` | id-exact, then **exact optimal bbox-IoU assignment** (Hungarian / Jonker-Volgenant, iterative O(n²m), no size cap, no degraded path); **intrinsic-id tie-breaks** (permutation-invariant); memoised per page pair |
| text-fidelity | `eval/checkers/text_fidelity.py` | three-part hard gate: page-level recall containment · per-region **retention** (graded gross/minor; n-gram ∨ character similarity) · per-region **misplacement**. Precision reported, not gated |
| reading-order | `eval/checkers/reading_order.py` | Kendall-tau + LIS + coverage |
| footnote-anchor | `eval/checkers/footnote_anchor.py` | note presence + notable-span preservation |
| structure-typing | `eval/checkers/structure_typing.py` | per-type P/R/F1 **reusing `eval.lib.metrics`**; zero-type-error gate |
| CLI | `eval/checkers/__main__.py` | `python -m eval.checkers --gt … --candidate … [--json]` |

The default suite is **five** checkers, structural-contract first: it is the
precondition the other four assume, so its verdict is read before theirs.

**Determinism (the load-bearing property):** every checker is a pure function of
`(candidate, gt)` — no clock, randomness, model, or I/O. Scoring is `+ - * /` over
integer ratios (IEEE-754-reproducible). The candidate consumes PageGT-shaped **dicts**
(no `scholar-schema` pin in Phase 0).

**Fixtures** (synthetic / public-domain — data-hygiene compliant, `tests/fixtures/`):
`minimal_page` (the scriptorium fixture, canonical end-to-end smoke) and a richer
`apparatus_page` (heading + two body blocks + an anchored note with a real `¹` marker),
added because the minimal fixture declares a note but **no in-text anchor marker**, so it
cannot meaningfully exercise footnote-anchor or its negative control.

---

## 2. Scorecard — end-to-end on the GT-A fixtures (CLI)

`uv run python -m eval.checkers --gt tests/fixtures/minimal_page.gt.json --candidate tests/fixtures/minimal_page.candidate.json` → **exit 0**

```
checker           severity  verdict  detail
text-fidelity     hard      PASS     recall 58/58 GT 3-grams contained (containment 1.0000, floor 0.95); precision 1.0000, 0 candidate 3-gram(s) not in GT (reported, not gated)
reading-order     hard      PASS     coverage 1.000 (floor 1.000), Kendall tau 1.000 (floor 1.000), LIS 2/2 in order
footnote-anchor   hard      PASS     notes 1/1 recovered; spans 0/0 preserved
structure-typing  hard      PASS     0 type-error(s) [FP 0 + FN 0] (tolerated 0); micro-F1 1.000, macro-F1 1.000; [body, footnote]
4/4 passed · 0 hard failure(s) · exit 0
```

`--gt apparatus_page.gt.json --candidate apparatus_page.candidate.json` → **exit 0**

```
text-fidelity     hard  PASS  recall 51/51 GT 3-grams contained (containment 1.0000, floor 0.95); precision 1.0000, 0 candidate 3-gram(s) not in GT
reading-order     hard  PASS  coverage 1.000, Kendall tau 1.000, LIS 4/4 in order
footnote-anchor   hard  PASS  notes 1/1 recovered; spans 1/1 preserved
structure-typing  hard  PASS  0 type-error(s) [FP 0 + FN 0]; micro-F1 1.000, macro-F1 1.000; [body, footnote, heading]
4/4 passed · exit 0
```

Mutated candidate (corrupt-5% on `apparatus_page`) → **exit 1**:

```
text-fidelity     hard  FAIL  recall 25/51 GT 3-grams contained (containment 0.4902, floor 0.95); precision 0.4902, 26 candidate 3-gram(s) not in GT
reading-order     hard  PASS  ...
footnote-anchor   hard  PASS  ...
structure-typing  hard  PASS  ...
3/4 passed · 1 hard failure(s) · exit 1
```

---

## 3. Negative controls — each mutation trips exactly its target

Deterministic mutators in `tests/_mutations.py` (no RNG — fixed stride for corruption).
Each mutation fails **only** its target checker; the suite exits non-zero in every case.

| mutation | text-fidelity | reading-order | footnote-anchor | structure-typing | exit |
|---|:---:|:---:|:---:|:---:|:---:|
| _(clean candidate)_ | PASS | PASS | PASS | PASS | **0** |
| drop-anchor | PASS | PASS | **FAIL** | PASS | **1** |
| swap-blocks | PASS | **FAIL** | PASS | PASS | **1** |
| corrupt-5%-chars | **FAIL** | PASS | PASS | PASS | **1** |
| mislabel | PASS | PASS | PASS | **FAIL** | **1** |

structural-contract passes on all five rows (none of these mutations is malformed).
Verified on both fixtures (`tests/test_checkers_negative_controls.py`).

**The isolation claim is conditional, and the condition is computed, not assumed.**
`drop_anchor` is text-fidelity-neutral only for markers normalization treats as *markup*
(`¹`, `*`, `†` — what both committed fixtures use). An **alphabetic** marker is an
ordinary content token after normalization, so removing it necessarily costs one token;
for those the control asserts a bounded residual instead. The test discovers the fixture
inventory from disk and branches on each fixture's declared markers, so a future fixture
cannot silently escape the claim.

---

## 4. Verification

- `uv run pytest` (full suite) → **175 passed** (44 ported lib tests + 26 delegation-log
  tests + 105 checker tests). `ruff check` clean; `mypy` clean (37 source files).
- CLI: faithful candidate → exit 0; mutated candidate → exit 1.
- **CI green on the final commit** (`a0b203e`):
  [run 27455116310](https://github.com/loganrooks/agentic-ocr/actions/runs/27455116310),
  all 5 checks success. The new step **"Checker suite smoke (GT-A fixtures)"** runs both
  fixtures in the `lint · typecheck · test` job
  ([job log](https://github.com/loganrooks/agentic-ocr/actions/runs/27455116310/job/81158097705))
  and is visible + green.

---

## 5. Adversarial review (D-008, reviewer ≠ author — T3 path `eval/checkers/**`)

A 3-lens panel (determinism · negative-control · schema-faithfulness; `reviewer` roster,
opus xhigh) ran in a workflow. **All three returned `request-changes`**; every finding was
corroborated against the code/schema and addressed (delegation-log: D-008 delegation +
accepted disposition).

| # | sev | lens | finding | resolution |
|---|---|---|---|---|
| 1 | major | determ. | `align.py` tie-break keyed on array order → a semantics-preserving permutation of `regions` flipped hard verdicts | tie-break on intrinsic ids; `test_checkers_alignment.py` asserts permutation invariance |
| 2 | major | determ. | structure-typing 0.999 float floor is page-size-dependent (1 mistype in 1000 → 0.999 → PASS) | gate on integer zero-type-errors (FP+FN==0); large-N regression test |
| 3 | major | neg-ctrl | text-fidelity "anti-hallucination tripwire" is recall-only / precision-blind | de-branded; `precision`+`excess_ngrams` now reported; **precision gate ESCALATED** (see §6) |
| 4 | major | schema | footnote-anchor misread `Region.text_anchors` (schema: "notable spans"; canonical marker channel is DocumentGT `Note.body_marker`) + `expected=1` forcing failed faithful candidates | reframed to notable-span preservation; Case-A bug fixed; **true marker-anchoring ESCALATED** (see §6) |
| 5 | minor | determ. | runner collapsed all crashes to indistinguishable hard FAIL | `metrics{crashed:True}` + `Scorecard.crashed` + clean-fixture zero-crash test |
| 6 | minor | determ. | stored `round(...,4)` metric could contradict the raw-float gate at the boundary | store the exact gated float; `test_metric_matches_verdict_at_boundary` |
| 7 | minor | schema | retired-enum comments wrong; `page_header` folded into "heading" | comments corrected (v1 back-compat); `page_header` routed to "other" |
| 8 | minor | neg-ctrl | isolation only tested against GT-identical candidates | added a hallucination-bearing divergent-candidate test |

---

## 6. Escalations (per the packet's pause/escalate clause)

Two items are genuine **design decisions for the schema / experiments track**, not packet
decisions, and are surfaced rather than forked locally:

1. **True footnote marker↔note anchoring.** The canonical binding is `DocumentGT.Note.body_marker`
   / `Note.marker_text`, which a *page*-level checker does not consume; `Region.text_anchors`
   is "notable text spans", not a marker channel. The page-level checker enforces note
   presence + notable-span preservation; full marker↔note integrity needs DocumentGT (or a
   schema addition) — **escalated to scholar-schema, not forked.**
2. **Hallucination (precision) gate.** text-fidelity's hard gate is recall (catches omission
   + corruption); the precision direction (hallucination) is computed and reported but the
   acceptable-excess **threshold is an experiments-track decision** — surfaced, not silently
   turned into a reward.

## 7. Known limitations (for the later reward-signal use)

- The text-fidelity hard gate is **recall-only**: a candidate that reproduces all GT text
  *and* fabricates extra text passes the hard gate (precision is reported, not gated). Any
  later "faithful / non-hallucinated" claim must read the precision metric, not just exit 0.
- A single dropped region intentionally fails multiple checkers (it is a multi-property
  gate). When the scorecard is mapped to a *scalar* reward, region-presence failures should
  be de-duplicated to one canonical checker to avoid stacked credit-assignment penalties.

## 8. Cross-session note

The shared `delegation-log.jsonl` was concurrently appended by session `eaa44f15`
(corpus-acquisition: D-101/D-102) using a separate id block. D-102 runs a real-corpus
text-fidelity smoke against the checker code; the review changes kept `TextFidelityChecker`'s
constructor and `containment` metric intact, so that usage is unaffected. (Multi-session
id-coordination on the shared log is already flagged for upstream-feedback by D-101.)

---

## 9. Cross-vendor review rounds D-237 (round 2) and round 3

Two further adversarial rounds ran after §5, both cross-vendor and both with executed
reproductions rather than code-reading alone. Every finding is closed; every reproduction
is now a regression test.

### Round 2 — D-237 (8 findings)

| # | sev | finding | resolution |
|---|---|---|---|
| H1 | high | reading order compared raw id sequences: honest model-generated ids false-FAILED (coverage 0); a phantom GT-id `reading_order` over reversed real indices PASSED | order evaluated over the `align_regions` mapping; candidate order derived from its own regions |
| H2 | high | page-pooled n-grams: swapping two regions' complete texts PASSED | per-region retention over aligned pairs |
| H3 | high | page-global n-gram backoff: blanking a 2-token heading PASSED | per-region backoff, plus character-similarity scoring (round 3) |
| H4 | high | duplicate region ids collapsed through last-wins dicts and PASSED | `StructuralContractChecker` |
| M5 | med | `PageView` traversed only top-level regions; `Region.children` unscored | depth-first flattening |
| M6 | med | greedy IoU assignment stranded matchable regions | exact assignment (finished in round 3) |
| M7 | med | `drop_anchor` used `str.replace`, destroying prose for an alphabetic marker | standalone-occurrence removal |
| L8 | low | `round(tau, 4)` reported 1.0 for a failing page | raw gated floats in telemetry |

### Round 3 (12 findings, both reviewers)

| id | sev | finding | resolution |
|---|---|---|---|
| L1-1 | major | reversed `reading_order_index` on every region + `"reading_order": ["head-1"]` → exit 0 at tau 1.0: one resolving entry suppressed the index signal, and a tail loop filled the rest from array order | both switches removed. A declared order is honoured only when complete; a present `reading_order` must be a list of strings naming every top-level region once and agreeing with the declared indices, else hard violation |
| L1-2 / L2-1 / L2-2 | major | the "smear" — every region's text set to the whole page — passed all five, because every GT region was perfectly *contained* in its counterpart | per-region **misplacement** gate (candidate n-grams belonging to a *different* GT region), zero tolerance. Scoped to misplacement only: novel text stays ungated, per the D-008 escalation |
| codex MEDIUM | medium | per-region zero-defect gate false-failed ordinary OCR noise (one changed character in a two-token heading → containment 0.0) | retention = max(n-gram containment, character similarity), graded gross/minor with a page-scaled minor allowance |
| L2-6 | low | `worst_region_containment` reported a flattering 1.0 whenever nothing crossed the floor | true minimum over every scored region |
| M6-NOT-CLOSED | medium | exactness above a 16-node cap only; a 17-node component matched 16 of 17 | Hungarian at every size; cap deleted |
| L2-3 | medium | the greedy fallback was an invisible degraded path | no fallback exists; there is one path |
| L2-4 | medium | recursion once per GT region while the cap counted only candidates: 200 GT took 55.7s, ~1000 GT raised `RecursionError` in all four consumers | iterative O(n²m) on the smaller side; both shapes are regression-tested with wall-time bounds |
| codex filtered-view | medium | the contract checker validated the already-filtered `PageView`, so a null region entry and a string-valued `reading_order` each scored a clean exit 0 | validates the **raw** page dicts |
| L2-7 / L2-5 | low | id-less regions uncounted (the "unique region ids" detail was not true); nesting past the depth cap silently truncated the GT | both are counted violations |
| codex LOW | low | `drop_anchor` walked only top-level regions, so the nested path was never exercised | mutators flatten through `children` |
| L2-9 | low | parent/child text convention unspecified | **exclusive** adopted as the documented working convention (§10) |

Reproduction harness (`.local/eval/triage/repro.py`, round 2) post-fix: baseline exit 0,
H1a (honest model ids) exit 0, H2 / H3 / H4 / H1b all exit 1.

### Constants introduced, and why

| constant | value | rationale |
|---|---|---|
| `MIN_REGION_RETENTION` | 0.95 | the same bar as the page-level floor — the region gate is the existing standard applied where pooling cannot dilute it, not a new stricter one |
| `GROSS_REGION_RETENTION` | 0.60 | separates *noise* from *gone*. Well above what deletion/swapping produce (~0.0–0.2) and well below any plausible OCR noise level. Zero tolerance, page-size invariant |
| `MINOR_REGION_DEFECT_RATE` | 0.05, floor 1 | a stochastic pipeline produces some minor noise on any long page; zero tolerance here was the round-3 false-fail. Scales with the page so a 40-region page is not held to a stricter effective standard than a 4-region one. The page-level floor still bounds accumulation |
| `MAX_REGION_FOREIGN_RATIO` | 0.5 | generous — a region must import *most* of its content from elsewhere to trip. Novel text only lowers the ratio, keeping the hallucination question escalated |
| `MAX_REGION_MISPLACEMENTS` | 0 | misplacement is categorical, not stochastic |
| `MAX_REGION_DEPTH` | 32 | bounds pathological nesting; exceeding it is a reported violation, never a silent truncation |

## 10. Open question for the E1 schema-revision inputs

**Does a parent `Region.text` include its children's text?** scholar-schema
(`scholargt/schema/spatial.py`) documents `Region.text` as optional and specifies no
inclusion semantics. The suite adopts **exclusive** (a parent's text holds only what is
not inside a child) as a documented working convention, recorded in `_flatten`'s
docstring: inclusive text would double-count every nested block in the page-level n-gram
multiset and would make a child's misplacement invisible to the per-region gate. No
runtime detection is attempted. If the schema later specifies inclusive text, `_flatten`
and `PageView.full_text` are the two places that change.
