# Evidence — Deterministic checker suite (`eval/checkers`)

**Goal:** A deterministic, unit-test-style checker suite (olmOCR-2 unit-test-rewards
pattern, PLAN §5) that scores any candidate pipeline output against a GT page, running
end-to-end on the scriptorium fixture page — **Phase-0 gate item 5**.

**Status:** ✅ shipped. PR [#3](https://github.com/loganrooks/agentic-ocr/pull/3),
branch `feat/checker-suite`. Built this session (`e9ecce02`), adversarially reviewed
(D-008, reviewer ≠ author), review findings applied.

---

## 1. What was built

| Component | File | Notes |
|---|---|---|
| Contract | `eval/checkers/base.py` | `CheckResult{id,passed,severity,detail,metrics}`, `Checker` ABC, `Scorecard` (exit code), `run_checkers()`, `AlwaysPassChecker` |
| PageGT accessors | `eval/checkers/pagegt.py` | read-only dict view; block-type classification (body/footnote/heading/other) |
| Normalizer | `eval/checkers/_normalize.py` | checker-local (eval/lib/normalize is element-, not string-oriented); n-gram helpers |
| Region alignment | `eval/checkers/align.py` | id-exact then bbox-IoU; **intrinsic-id tie-breaks** (permutation-invariant) |
| text-fidelity | `eval/checkers/text_fidelity.py` | recall n-gram containment (hard); precision reported |
| reading-order | `eval/checkers/reading_order.py` | Kendall-tau + LIS + coverage |
| footnote-anchor | `eval/checkers/footnote_anchor.py` | note presence + notable-span preservation |
| structure-typing | `eval/checkers/structure_typing.py` | per-type P/R/F1 **reusing `eval.lib.metrics`**; zero-type-error gate |
| CLI | `eval/checkers/__main__.py` | `python -m eval.checkers --gt … --candidate … [--json]` |

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

Verified on both fixtures (`tests/test_checkers_negative_controls.py`).

---

## 4. Verification

- `uv run pytest -k checker` → **57 passed**.
- `uv run pytest` (full suite) → **127 passed** (44 ported lib tests + 26 delegation-log
  tests + 57 checker tests). `ruff check` clean; `mypy` clean.
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
