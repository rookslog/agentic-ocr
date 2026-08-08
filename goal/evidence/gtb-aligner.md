# Evidence — GT-B aligner (eval/gtb)

**Packet:** `goal/gtb-aligner.goal.md` · **Date:** 2026-06-19 · **Phase:** 0 (gate clause 4).
**Status:** built + smoked on the 3 owned pairs; calibration holds. The **≥5 accepted
pairs** gate clause stays open by design (only 3 candidates owned — the expected G3 stall;
see "Stall" below). No human judgment in any verdict.

## What was built

A NEW module `eval/gtb/` (distinct from the G1-locked `eval/checkers/`):

- `eval/gtb/extract.py` — EPUB (pure-Python `zipfile` + OPF-spine order + XHTML tag-strip)
  and PDF (`pdftotext`/poppler, no OCR) text extraction, generalized from
  `.local/eval/og_smoke.py`.
- `eval/gtb/align.py` — the three-stage aligner + the mechanical coverage statistic and
  accept/reject verdict. No I/O, pure/deterministic.
- `eval/gtb/test_align.py` — 16 co-located unit tests (synthetic tokens only; no corpus
  bytes), incl. a regression test for the large-gap over-credit bug (see DEVIATION).
- `.local/eval/gtb_smoke.py` — `.local`-only real-corpus smoke (reads the gitignored
  `corpus/` pairs); prints counts/coverage only — never corpus bytes or provenance ids.

### Page-key layer (added 2026-07-31)

- `eval/gtb/page_keys.py` — slices ONE whole-book alignment into **per-PDF-page GT token
  spans** (answer keys for scoring vision transcriptions of single page images), plus
  per-page coverage and a `reliable` flag. Pure logic; reuses `unique_shared_anchors` +
  `align_tokens` rather than reimplementing them.
- `eval/gtb/extract.py` — gained `split_pdf_pages` / `extract_pdf_page_texts` (one
  `pdftotext` pass, split on the form feed poppler writes after every page). Token identity
  with the whole-book pass is *verified at run time* by `page_keys.page_token_ranges`
  (raises `TokenizationMismatch`), not assumed; measured identical on all 3 pairs.
- `eval/gtb/test_page_keys.py` — 18 co-located unit tests (synthetic tokens only).
- `.local/eval/page_keys_smoke.py` — real-corpus smoke; writes the 40 vision-pilot answer
  keys under `.local/vision-pilot/keys/` (gitignored). Counts/coverage to stdout only.

Reliability floor (named constants): `MIN_PAGE_ANCHORS = 3`, `MIN_PAGE_COVERAGE = 0.60`
(= `ACCEPT_THRESHOLD`; a page key is a miniature GT-B pair), `MIN_PAGE_TOKENS = 5`.
Per-page anchor counts are sharply bimodal — the observed values are 0 or 1 for
front-matter/plate/index pages and then jump to 6+ (p05 = 141–287) for body pages, so the
floor sits in an empty band and the classification is insensitive to any choice in [2, 6].

| pair                  | PDF pages | keyed | **reliable** | unreliable | cov p05 | p50 | p95 |
|-----------------------|----------:|------:|-------------:|-----------:|--------:|----:|----:|
| of-grammatology       | 444 | 442 | **439** |  5 | 0.8856 | 0.9693 | 0.9844 |
| specters-of-marx      | 277 | 276 | **275** |  2 | 0.9085 | 0.9883 | 0.9920 |
| totality-and-infinity | 315 | 285 | **283** | 32 | 0.9000 | 0.9821 | 0.9922 |

All 40 vision-pilot pages are reliable (min page_coverage 0.8750). The unreliable pages are
front matter, blank/plate pages, section dividers and back-matter index pages absent from the
EPUB — i.e. exactly the material with no GT to key against.

## Method (PLAN.md:139)

1. **Anchor extraction** — word **5-grams that occur exactly once in BOTH** token streams
   (EPUB-GT and PDF-candidate) are candidate anchors. Their `(gt_pos, cand_pos)` coordinates
   are filtered to a strictly-monotone chain by a longest-increasing-subsequence (LIS) pass,
   so transposed/duplicated material cannot forge a crossed "alignment".
2. **DP fill** — between consecutive anchors, the GT and candidate sub-segments are aligned
   by an LCS dynamic program over tokens; the LCS length is the count of GT tokens recovered
   in that gap. Gaps longer than `MAX_GAP=4000` tokens are treated as unalignable (0 matched)
   so a single runaway gap (edition divergence) cannot dominate runtime and cannot be
   silently counted as covered.
3. **Coverage + verdict** — `coverage = matched_gt_tokens / total_gt_tokens` ∈ [0, 1],
   counting **distinct** GT token indices (anchor spans ∪ gap-LCS matches, no double count).
   A pair **ACCEPTS iff `coverage >= ACCEPT_THRESHOLD` (0.60)**.

### Coverage schema (decision, not invented)

The denominator is the **GT (EPUB) token count**. The born-digital edition is the trusted
reference we want to recover from the scan, so "what fraction of the trusted text did the
scan-side stream let us align" is the meaningful quantity — the recall direction the OG smoke
measured at 0.904, made anchor-local instead of bag-of-n-grams. It is bounded, monotone in
alignment quality, 0 for disjoint texts. (Goal packet said to escalate if "coverage" were
genuinely underspecified; PLAN.md:139 + the OG smoke pinned it down enough to decide here.)

## Coverage table (deterministic smoke)

Command (reads gitignored `corpus/`): `uv run python .local/eval/gtb_smoke.py`

| pair                  | edition      | GT tok | PDF tok | anchors | matched | **coverage** | verdict |
|-----------------------|--------------|-------:|--------:|--------:|--------:|-------------:|---------|
| of-grammatology       | **confirmed**| 222116 | 230804 | 177622 | 212687 | **0.9575** | ACCEPT |
| specters-of-marx      | uncertain    |  94305 |  95428 |  88439 |  93616 | **0.9927** | ACCEPT |
| totality-and-infinity | uncertain    | 118315 | 123040 | 109495 | 115671 | **0.9777** | ACCEPT |

> **Re-measured 2026-07-31** (same command, same corpus files): of-grammatology now reads
> 228370 PDF tokens / coverage **0.9670** rather than 230804 / 0.9575; the other two pairs and
> both negative controls are unchanged to 4 dp, and calibration still holds (exit 0). Cause
> unconfirmed — most likely a poppler/`pdftotext` build change on this machine, since the
> extraction code path is unmodified. Verdicts are unaffected (the empty band is ~0.95 wide).

**Negative controls** (GT of one book vs PDF of an unrelated book — must REJECT):

| control                         | GT tok | PDF tok | anchors | matched | coverage | verdict |
|---------------------------------|-------:|--------:|--------:|--------:|---------:|---------|
| og-GT × ti-PDF                  | 222116 | 123040 |      31 |    1210 | **0.0054** | REJECT |
| ti-GT × sm-PDF                  | 118315 |  95428 |      27 |    1400 | **0.0118** | REJECT |

Both edition-uncertain pairs score as high as the confirmed pair — the *coverage statistic*
says all three are well-aligned same-text pairs. Per the packet I report what the statistic
says and do **not** force a verdict on the uncertain pairs from edition metadata alone.

## Threshold rationale (calibration)

The packet's calibration target: the confirmed OG pair must ACCEPT and a deliberately-
mismatched pair must REJECT, and reject verdicts are not to be trusted until that holds — it
does (exit 0 from the smoke). The separation is not marginal:

- **True pairs:** 0.9575 – 0.9927.
- **Negative controls:** 0.0054 – 0.0118.

The gap between the lowest true pair (0.9575) and the highest control (0.0118) is ~0.95 wide
and **empty**. The threshold 0.60 sits in the middle of that empty band, so the verdict is
insensitive to threshold choice anywhere in roughly [0.05, 0.95]. 0.60 is deliberately well
*above* any plausible mismatch coverage and well *below* any true-pair coverage; it is not
tuned to a single pair (forbidden by the packet — "loosening the threshold to make a pair
pass"), and tightening it would not change any current verdict.

**Why n=5 anchors** — probe over n ∈ {3,4,5,6} on OG (true) and og-GT×ti-PDF (control):

| n | OG coverage | NC coverage | OG anchors | NC anchors |
|---|------------:|------------:|-----------:|-----------:|
| 3 | 0.9575 | 0.0687 | 142313 | 112 |
| 4 | 0.9575 | 0.0270 | 172280 |  63 |
| **5** | **0.9575** | **0.0054** | **177622** | **31** |
| 6 | 0.9575 | 0.0003 | 175573 |  12 |

The true-pair signal is n-robust (0.9575 at every n); the control's spurious-anchor coverage
collapses as n grows (0.069 → 0.0003). n=5 gives a clean separation with a large true-pair
anchor count. Reproduce: the probe block is in the session log; it calls
`eval.gtb.align.align_tokens(..., n=n)` over the same two extractions.

## Negative-control result

Two cross-book controls REJECT at 0.0054 and 0.0118. The calibration assertion
(`OG accepts AND all controls reject`) holds; the smoke exits 0 only when it does.

## Quality gates

- **Tests:** `uv run pytest eval/gtb/test_align.py` → 16 passed in 0.04s. Full repo suite
  `uv run pytest -q` → 127 passed (no regression in the existing suite). Note: pyproject
  `testpaths=["tests"]`, so the co-located gtb tests are run by explicit path (the locked
  `tests/` tree is untouched).
- **ruff:** `uv run ruff check eval/gtb/` → clean.
- **mypy:** `uv run mypy eval/gtb/` → clean; `uv run mypy` (full, 37 files) → clean.

## DEVIATION

- **D-GTB-1 (self-found bug, fixed):** a first "non-double-counting" coverage rewrite credited
  the *entire* inter-anchor gap as anchor-covered (it advanced coverage to `a.gt_pos + n` from
  the previous covered end instead of from `a.gt_pos`). With sparse anchors this made the
  negative controls score 0.85+ and ACCEPT — a false-accept. Caught by the negative-control
  smoke (the controls are exactly the guard the packet mandates), fixed by clipping the
  anchor-span credit to `[max(prev_gt_end, a.gt_pos), a.gt_pos+n)`, and locked with the
  regression test `test_sparse_anchors_large_gap_not_credited`. Post-fix numbers are the table
  above. *Lesson: trust the negative control, not the headline number.*

## Stall (expected, per packet "Pause / escalate when")

Gate clause 4 wants **≥5 accepted** GT-B pairs. Only **3** candidate pairs are owned and all 3
accept, so the apparatus is built and validated but the count target cannot be met on owned
files. This is the expected **G3 stall** (zlibrary acquisition of more paired editions). Per
the packet I built + smoked the aligner and surfaced the stall; I did **not** attempt
acquisition. Decision owner: Logan (acquisition is HUMAN-GATEd, zlibrary ≤10/day) —
`goal/corpus-acquisition.goal.md`.

## Reproduce

```
uv run python .local/eval/gtb_smoke.py     # 3 pairs + 2 negative controls; exit 0 iff calibration holds
uv run pytest eval/gtb/test_align.py       # 16 co-located unit tests
uv run ruff check eval/gtb/ && uv run mypy eval/gtb/
```
