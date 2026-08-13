# Evidence — GT-B aligner (eval/gtb)

**Packet:** `goal/gtb-aligner.goal.md` · **Built:** 2026-06-19 · **Reviewed:** 2026-08-12 ·
**Phase:** 0 (gate clause 4).
**Status:** W2 adversarial verdict **REQUEST-CHANGES**. The mechanical implementation defects
found by the three review lenses are repaired and the three recorded candidates plus two
unrelated controls were re-measured. The legacy `accepted` flag remains a **GT-recall gate,
not edition certification**: compound, duplicated, or substantially reordered candidates can
still pass recall. Changing that verdict contract is BLOCKED-ON-HUMAN; PR #5 stays draft and
must not merge on the current binary semantics.

## What was built

A NEW module `eval/gtb/` (distinct from the G1-locked `eval/checkers/`):

- `eval/gtb/extract.py` — EPUB (pure-Python `zipfile` + XML-parsed OPF-spine order + XHTML tag-strip)
  and PDF (`pdftotext`/poppler, no OCR) text extraction, generalized from
  `.local/eval/og_smoke.py`.
- `eval/gtb/align.py` — the three-stage aligner + the mechanical GT-recall statistic and
  provisional threshold flag. No I/O, pure/deterministic.
- `eval/gtb/test_align.py` — 28 co-located unit tests (synthetic tokens only; no corpus
  bytes), including candidate-injectivity and bounded global-LCS invariants.
- `eval/gtb/test_extract.py` — 3 synthetic extraction-contract tests, including namespaced,
  single-quoted EPUB XML and relative percent-encoded spine hrefs.
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
- `eval/gtb/test_page_keys.py` — 27 co-located unit tests (synthetic tokens only).
- `.local/eval/page_keys_smoke.py` — real-corpus smoke; writes the 40 vision-pilot answer
  keys under `.local/vision-pilot/keys/` (gitignored). Counts/coverage to stdout only.

Reliability floor (named constants): `MIN_PAGE_ANCHORS = 3`, `MIN_PAGE_COVERAGE = 0.60`
(= `ACCEPT_THRESHOLD`; a page key is a miniature GT-B pair), `MIN_PAGE_TOKENS = 5`.
The 2026-08-12 span-disjoint-anchor run measured 0/1-anchor page counts of 2/0, 1/1, and
30/2 across the three candidates. Minimum reliable-page anchor counts were 3, 4, and 12;
reliable-page p05 counts were 65, 31, and 31. This supports the current floor for these
cases but does **not** license the prior claim that every threshold in [2, 6] is equivalent.

| pair                  | PDF pages | keyed | **reliable** | unreliable | cov p05 | p50 | p95 |
|-----------------------|----------:|------:|-------------:|-----------:|--------:|----:|----:|
| of-grammatology       | 444 | 442 | **438** |  6 | 0.8856 | 0.9693 | 0.9844 |
| specters-of-marx      | 277 | 276 | **274** |  3 | 0.9085 | 0.9883 | 0.9920 |
| totality-and-infinity | 315 | 285 | **283** | 32 | 0.9000 | 0.9821 | 0.9922 |

All 40 vision-pilot pages remain reliable (minimum page coverage 0.8750). This run measured
counts and metrics only; it did not re-inspect or reclassify page content. The local smoke
asserts nondecreasing GT **starts**, not ends: a shorter later page can be independently
anchored inside the preceding page's extrapolated tail, so forcing nondecreasing ends would
reintroduce unsupported-text spillover.

## Method (PLAN.md:139)

1. **Anchor extraction** — word **5-grams that occur exactly once in BOTH** token streams
   (EPUB-GT and PDF-candidate) are candidate anchors. Their `(gt_pos, cand_pos)` coordinates
   are filtered to a strictly-monotone chain by a longest-increasing-subsequence (LIS) pass,
   then greedily made **span-disjoint in both streams**. The second constraint prevents one
   candidate token interval from explaining multiple disjoint GT intervals.
2. **DP fill** — between consecutive anchors, the GT and candidate sub-segments are aligned
   by an LCS dynamic program over tokens; the LCS length is the count of GT tokens recovered
   in that gap. Gaps longer than `MAX_GAP=4000` tokens are treated as unalignable (0 matched)
   so a single runaway gap (edition divergence) cannot dominate runtime and cannot be
   silently counted as covered.
3. **Coverage + legacy flag** — `coverage = matched_gt_tokens / total_gt_tokens` ∈ [0, 1],
   counting an injective common subsequence (anchor spans plus gap-LCS matches). The current
   `accepted` flag is true only with at least one anchor and coverage ≥ 0.60. It is retained
   for compatibility while the pair-certification contract is decided; it is not sufficient
   evidence that the candidate is the same edition.

### Coverage schema (decision, not invented)

The denominator is the **GT (EPUB) token count**. The born-digital edition is the trusted
reference we want to recover from the scan, so "what fraction of the trusted text did the
scan-side stream let us align" is the meaningful quantity — the recall direction the OG smoke
measured at 0.904, made anchor-local instead of bag-of-n-grams. It is bounded and zero for
disjoint texts. It is **not globally monotone** because gaps above `MAX_GAP` are deliberately
scored zero to bound runtime. More importantly, the denominator defines recall only: it
cannot distinguish exact GT from exact GT plus unrelated material or duplication. The packet
pinned the denominator but not recall's sufficiency for edition certification; W2 therefore
surfaces that contract decision instead of inventing an uncalibrated second gate.

## Coverage table (deterministic smoke)

Command after merge (reads gitignored `corpus/`):
`uv run python .local/eval/gtb_smoke.py`. W2 measured the unmerged repair with the
equivalent `PYTHONPATH=<PR5-worktree>:<repo> .venv/bin/python .local/eval/gtb_smoke.py`;
it exited 0 and printed only the counts and metrics below.

Measured 2026-08-12 after the span-disjoint-anchor repair. `candidate coverage` is the same
injective match count divided by candidate tokens; it is diagnostic-only.

| pair | GT tok | PDF tok | anchors | matched | **GT recall** | candidate coverage | length ratio | legacy flag |
|------|-------:|--------:|--------:|--------:|--------------:|-------------------:|-------------:|-------------|
| of-grammatology | 222116 | 228370 | 39708 | 214775 | **0.966950** | 0.940469 | 1.028156 | true |
| specters-of-marx | 94305 | 95428 | 18201 | 93616 | **0.992694** | 0.981012 | 1.011908 | true |
| totality-and-infinity | 118315 | 123040 | 22591 | 115671 | **0.977653** | 0.940109 | 1.039936 | true |

**Negative controls** (GT of one book vs PDF of an unrelated book — must REJECT):

| control | GT tok | PDF tok | anchors | matched | GT recall | candidate coverage | legacy flag |
|---------|-------:|--------:|--------:|--------:|----------:|-------------------:|-------------|
| control 1 | 222116 | 123040 | 25 | 1204 | **0.005421** | 0.009785 | false |
| control 2 | 118315 | 95428 | 19 | 1394 | **0.011782** | 0.014608 | false |

The statistic says the three candidates have high GT recall and the unrelated controls do
not. It does not by itself establish edition identity.

## Threshold rationale and calibration limit

The packet's recorded bracket still holds: the confirmed candidate's legacy flag is true and
both unrelated controls are false. The separation in this five-case sample is not marginal:

- **Recorded candidates:** 0.966950 – 0.992694.
- **Negative controls:** 0.0054 – 0.0118.

The observed sample has no point between 0.0118 and 0.9669, but that is an **unmeasured
region**, not evidence that the domain is empty. A synthetic exact 60-token prefix of a
100-token GT reaches the inclusive 0.60 boundary while omitting 40%; compound, duplicate,
and reordered candidates also pass recall. Therefore the sample brackets the recorded cases
but does not calibrate 0.60 for near-boundary same-work/wrong-edition decisions.

**Why n=5 anchors** — probe over n ∈ {3,4,5,6} on OG (true) and og-GT×ti-PDF (control):

| n | OG coverage | NC coverage | OG anchors | NC anchors |
|---|------------:|------------:|-----------:|-----------:|
| 3 | 0.9669 | 0.0687 | 57816 | 101 |
| 4 | 0.9669 | 0.0269 | 48806 | 54 |
| **5** | **0.9669** | **0.0054** | **39708** | **25** |
| 6 | 0.9669 | 0.0003 | 33015 | 11 |

The recorded candidate's recall is n-robust and the control decreases as n grows. This probe
does **not identify n=5 as uniquely calibrated**—n=6 has a lower control value and still many
candidate anchors. W2 retains the packet's n=5 default while recording that limitation.

## Negative-control result

Two cross-book controls remain below the legacy gate at 0.005421 and 0.011782. This licenses
only the recorded bracket, not general pair certification.

## Quality gates

- **Tests:** `.venv/bin/pytest -p no:cacheprovider -o addopts=` → 274 collected,
  273 passed, 1 intentional xfail; the output lists 58 GT-B tests under default discovery.
- **ruff:** `.venv/bin/ruff check --no-cache .` → `All checks passed!`.
- **mypy:** `.venv/bin/mypy --cache-dir /tmp/agentic-ocr-w2-final-mypy .` → no issues in
  47 source files.
- **real-corpus page smoke:** the first post-repair run correctly falsified the old
  nondecreasing-end oracle on one measured page. A numeric-only probe showed later anchors
  advanced while the shorter span ended 22 tokens before the previous page's extrapolated
  end. `.local/eval/page_keys_smoke.py` now checks nondecreasing starts; the rerun exited 0,
  with all 40 pilot keys reliable and the table above unchanged.

## DEVIATION

- **D-GTB-1 (self-found bug, fixed):** a first "non-double-counting" coverage rewrite credited
  the *entire* inter-anchor gap as anchor-covered (it advanced coverage to `a.gt_pos + n` from
  the previous covered end instead of from `a.gt_pos`). With sparse anchors this made the
  negative controls score 0.85+ and ACCEPT — a false-accept. Caught by the negative-control
  smoke (the controls are exactly the guard the packet mandates), fixed by clipping the
  anchor-span credit to `[max(prev_gt_end, a.gt_pos), a.gt_pos+n)`, and locked with the
  regression test `test_sparse_anchors_large_gap_not_credited`. Post-fix numbers are the table
  above. *Lesson: trust the negative control, not the headline number.*
- **D-GTB-2 (W2 blocker, fixed):** LIS constrained anchor starts but allowed overlapping
  candidate spans. A 15-token candidate could therefore explain 55 disjoint GT tokens and
  false-ACCEPT at 0.846. Anchors are now span-disjoint in both streams; a bounded exhaustive
  test asserts `matched_gt_tokens <= global LCS`, and the exploit now rejects.
- **D-GTB-3 (W2 major, fixed):** an unreliable page's extrapolated end constrained its
  successor, which could be labelled reliable while containing unsupported GT. Only reliable
  starts now constrain later pages and no previous end is propagated. A closure-audit
  boundary case also showed that a page barely above the 0.60 floor could leak its guessed
  tail; the reproduced successor now returns its exact supported span in both cases.
- **D-GTB-4 (W2 verification gaps, fixed):** default pytest omitted the co-located tests, the
  double-count fixture had zero anchors, supplied anchor chains were trusted, and extraction
  had no tests. Default discovery now includes `eval/gtb`; the exploit fixtures are non-vacuous;
  supplied chains must be canonical for the pair; EPUB metadata is parsed as XML.
- **D-GTB-5 (contract open):** recall-only acceptance still passes compound, duplicated, and
  substantially reordered candidates. No uncalibrated precision/length/order cutoff was
  invented. The owner decision is recorded in the W2 drive evidence.
- **D-GTB-6 (local-oracle correction):** after removing end propagation, the real page-key
  smoke's old `end >= previous_end` assertion failed. The anchors themselves advanced; the
  prior end was only an extrapolated tail. The local smoke now checks the licensed placement
  property (`start >= previous_start`) and no longer demands the spillover behavior W2 fixed.

## Stall (expected, per packet "Pause / escalate when")

Gate clause 4 wants ≥5 certified GT-B pairs. This W2 evidence covers three recorded
candidates only. The 2026-08-12 drive opened owned/PD mining and a capped fallback under W6,
but the unresolved certification semantics mean a recall-passing count must not be relabelled
as five certified pairs without the owner decision.

## Reproduce

```
uv run python .local/eval/gtb_smoke.py     # 3 candidates + 2 unrelated controls; legacy bracket
uv run pytest -p no:cacheprovider          # default discovery includes all 57 GT-B tests
uv run ruff check --no-cache .
uv run mypy --cache-dir /tmp/agentic-ocr-gtb-mypy .
```
