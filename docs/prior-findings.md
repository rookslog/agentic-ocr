# Prior findings — distilled from scholardoc

Empirical record carried forward from the `scholardoc` repo (PLAN.md §12 salvage
manifest: *carry the findings and data; leave the code*). Source: the read-only
clone at `./scholardoc`, branch **`revival/2026-05-audit-and-reset`**. Every claim
cites a file path relative to that repo root; the branch suffix
`@ revival/2026-05-audit-and-reset` applies to all paths. `[CONFIRMED]` = read the
primary source directly; `[UNCERTAIN]` = inferred or unreconciled.

These numbers are inherited under the §8 epistemic standard as **Reported, narrow,
and not yet re-validated in this repo.** None bears weight on an agentic-ocr
decision until a checker in `eval/` reproduces it on our own corpus.

## Architecture decisions (ADRs)

- **ADR-001 — PyMuPDF (fitz) as primary PDF library.** Chosen for best text
  extraction with full font/position data + page labels and C-speed batch
  processing; trade-off is the AGPL license. Status in the ADR is still
  **PROPOSED — pending spike validation** (never marked Accepted in-file, though
  downstream docs/code treat it as decided).
  `[CONFIRMED — docs/adr/ADR-001-pdf-library-choice.md @ revival/2026-05-audit-and-reset]`
  — *"Status: PROPOSED - Pending Spike Validation"*; *"Recommended: PyMuPDF (fitz) as primary extraction library"*.

- **ADR-002 — Spellcheck as selector, not corrector.** Spellcheck only *flags*
  suspicious words; selective neural re-OCR runs only on flagged lines (cropped at
  line, not word, level). Rationale: auto-correction corrupts scholarly terms
  ("Dasein" → "Design").
  `[CONFIRMED — docs/adr/ADR-002-ocr-pipeline-architecture.md @ revival/2026-05-audit-and-reset]`
  — *"Spellcheck flags suspicious words but never auto-corrects."*

- **ADR-003 — Position-based line-break rejoining with block filtering.** Only
  rejoin hyphenated words within the *same* PyMuPDF block, to exclude margin
  content (page numbers, headers). Measured on Heidegger *Being and Time* (50 pp):
  "Valid joins: 1 ... Correctly rejected: 4".
  `[CONFIRMED — docs/adr/ADR-003-line-break-detection.md @ revival/2026-05-audit-and-reset]`
  — *"CRITICAL: Only if SAME block"*.

- **ADR-004 — Track OCR source engine in metadata.** All sample PDFs are Adobe
  Acrobat Paper Capture (Acrobat 9.0–24, ~14 years of versions); single-vendor
  coverage accepted as a known limitation.
  `[CONFIRMED — docs/adr/ADR-004-ocr-source-tracking.md @ revival/2026-05-audit-and-reset]`
  — *"All identified sources use Adobe Acrobat Paper Capture (single vendor)"*.

## Measured metrics

- **PyMuPDF speed: 32–57× faster.** Baseline is **pdfplumber specifically**
  (wall-clock extraction time). Underlying timings: Comay born-digital pymupdf
  0.64s vs pdfplumber 36.27s (≈57×); Kant OCR'd scan pymupdf 3.69s vs pdfplumber
  118.90s (≈32×). vs `pypdf` the gap is only ~9–15×, not 32–57×.
  `[CONFIRMED — spikes/FINDINGS.md @ revival/2026-05-audit-and-reset]`
  — *"PyMuPDF is 32-57x faster than pdfplumber"*.

- **Spellcheck-as-selector: 99.2% detection / 23.4% false positive.** Population =
  a validation set of **130 OCR error pairs** (detection rate is OF those 130; 1
  false negative) and **77 correct words** (FP rate is OF those 77; mostly German
  philosophical terms). These two figures are the headline numbers in PLAN §2.3 /
  CHANGELOG.
  `[CONFIRMED — docs/adr/ADR-002-ocr-pipeline-architecture.md @ revival/2026-05-audit-and-reset]`
  — *"Test set: 130 OCR error pairs, 77 correct words"* with *"Detection rate | 99.2%"*, *"False positive rate | 23.4%"*.

- **Validation-set composition: 130 error pairs + 77 correct words — confirmed by
  inspecting the JSON.** Top-level `error_pairs` length = 130; `correct_words`
  length = 77; `summary.total_errors` = 130; 103/130 errors come from a single book
  (Heidegger *Being and Time*).
  `[CONFIRMED — ground_truth/validation_set.json @ revival/2026-05-audit-and-reset]`
  — `summary: {"total_errors": 130, "correct_words": 77}`. (This file is carried into
  this repo as `eval/fixtures/validation_set.json`.)

## Spikes of note (concrete measured results only)

- **Spike 05 (OCR quality survey):** Kant scan is 99.76% valid words despite a
  "DEGRADED" rating; corpus split ≈70% acceptable / ≈30% need correction / <5% need
  full re-OCR. `[CONFIRMED — spikes/FINDINGS.md @ revival/2026-05-audit-and-reset]` — *"99.76% valid words"*.
- **Spike 09 (TrOCR re-OCR):** TrOCR not better than existing Adobe OCR;
  misspellings devastate embeddings ("judgment" sim 1.000 existing vs 0.288 TrOCR);
  GPU ~21× faster than CPU. Self-flagged caveat: *"neither is ground truth!"*
  `[CONFIRMED — spikes/FINDINGS.md @ revival/2026-05-audit-and-reset]`.
- **Spike 10 (engine comparison):** docTR (GPU) wins on ground-truth similarity
  (0.402 vs existing 0.392) and is fastest (~0.6s/page).
  `[CONFIRMED — spikes/FINDINGS.md @ revival/2026-05-audit-and-reset]`.
- **Spike 13 (spellcheck risk):** "41% of Philosophy Terms Would Be Wrongly
  'Corrected'" (24 of 59); "dasein → casein" = 21.5% embedding loss. Empirical
  backing for the selector-not-corrector decision (ADR-002).
  `[CONFIRMED — spikes/FINDINGS.md @ revival/2026-05-audit-and-reset]`.

## Caveats / non-transfer

- **The headline 99.2% / 23.4% numbers have no primary spike record.** They live in
  ADR-002 / CHANGELOG / ROADMAP / production code but are *absent* from
  `spikes/FINDINGS.md` and every spike script (grep confirmed). Treat as a one-time,
  unreproduced measurement. `[CONFIRMED — grep over spikes/ + docs @ revival/2026-05-audit-and-reset]`.
- **Two contradictory metric pairs coexist, unreconciled.** ADR-004 and ROADMAP
  report **96.9% detection / 20.8% FP** — a *different* run from ADR-002's 99.2% /
  23.4%. Which is authoritative is undetermined in-repo.
  `[CONFIRMED — docs/adr/ADR-004-ocr-source-tracking.md vs ADR-002 @ revival/2026-05-audit-and-reset]` `[UNCERTAIN — reconciliation]`.
- **The audit branch itself flags these as unverifiable:** *"Cannot validate '99.2%
  detection rate' claims"*; *"One-time spike validation, no ongoing verification"*;
  *"no regression test suite exists"*.
  `[CONFIRMED — .planning/codebase/CONCERNS.md @ revival/2026-05-audit-and-reset]`.
- **Narrow population / single vendor.** Rates are over 130 pairs + 77 words, 103 of
  130 errors from one book; OCR engine coverage is Adobe-only (ADR-004).
- **Speed baseline is partial.** "32–57×" is strictly vs pdfplumber; vs pypdf only ~9–15×.

### Implication for this repo

The spellcheck-as-selector result is the strongest narrow-OCR salvage and a natural
**routing-signal candidate** for the cascade (PLAN §6 mechanism 4: routing from
checkers/agreement, never VLM self-confidence). But its provenance is thin and
its population is one book in one language from one OCR vendor. Before it informs
any routing threshold it must be re-measured by an `eval/` checker on our stratified
corpus — exactly the Goodhart / re-validation discipline of PLAN §8 and §13.
