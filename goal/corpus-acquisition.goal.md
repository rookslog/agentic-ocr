# /goal packet — Phase-0 evaluation corpus: selection + acquisition

**Objective:** A stratified ~30-book evaluation corpus staged under `corpus/` with
per-item provenance records, plus ≥20 GT-B candidate pairs (scan + EPUB of the same
edition), assembled from Logan's existing library first and a rate-limited zlibrary queue
second — with Logan's explicit approval of the selection before anything is acquired.

**Read first (in order):**
- `STATE.md` — what is true now.
- `.local/corpus/manifest.md` + `manifest.json` — the library inventory (already built,
  74 records; do not redo it).
- `scholardoc/ground_truth/selected_pages.json` + `spikes/sample_pdfs/MANIFEST.md` +
  `ground_truth/validation_set.json` (read-only clone) — scholardoc already *named* its
  difficult documents/pages; re-acquiring those exact documents lets us reuse that
  page-level knowledge instead of regenerating it.
- `PLAN.md` §1 (strata), §5 (GT-A/B/C strategy), §11.5 (data hygiene).
- `docs/delegation-triage.md` — if you delegate, follow the rubric and log it.

**Known inventory facts (from D-001, spot-checked):** all ~29 `~/Downloads/corpus`
"PDFs" are actually **ZIP archives of JPEG page scans** — stage them as-is and record
`format: zip-of-jpegs` (the ingest normalizer is pipeline work, not acquisition work).
**Zero Derrida EPUBs exist locally**, so every Derrida GT-B pair needs acquisition.
OneDrive holds ~235 Derrida + ~289 Heidegger PDFs as **dataless placeholders** — treat
it as an acquisition-priority *index* (especially `…/Reading Now/Derrida/`), not as a
usable corpus; materializing files counts as acquisition work and needs Logan's nod.

**Allowed scope:** `corpus/` (gitignored), `.local/corpus/`, `goal/evidence/corpus-acquisition.md`,
`STATE.md` (status section only), `delegation-log.jsonl` (append only).

**Forbidden:**
- Any acquisition before Milestone 1's HUMAN-GATE clears.
- More than **10 zlibrary items per calendar day** — track the count in the evidence
  file; stop at 10 even mid-milestone.
- Moving, renaming, or deleting Logan's original files anywhere — stage by **copy** only.
- Editing `PLAN.md`, `eval/`, experiment preregs, or any past ledger/log rows.

**Data hygiene (absolute):** no PDF/EPUB, no `corpus/` content, and no zlibrary
provenance (URLs, IDs, account traces) ever enters git history or leaves this machine.
The gitignore and the CI blob guard enforce this; do not work around them. Provenance
records live inside `corpus/` (gitignored) as `provenance.json` per item: sha256, byte
size, page count, source (`local-library: <original path>` or `zlibrary: <internal id>`),
strata tags, acquisition date, and `format` (`pdf` | `zip-of-jpegs` | `epub` |
`text-artifact`).

**Milestones:**
1. **Selection proposal** — from the manifest, propose 25–30 books spread across strata
   A (rough scan) / B (clean scan) / C (heavy apparatus) / D (born-digital), *including
   all four PDFAgentialConversion difficult examples* and ≥1 apparatus-extreme text
   (Glas / Post Card / Truth in Painting class) early, plus the prioritized zlibrary
   queue: day 1 ≈ EPUB counterparts for owned scans (GT-B pairs — Grammatology, Margins,
   Dissemination, Specters, Post Card…), then scholardoc-named documents (Being and
   Time, Discourse on Thinking), then gaps in under-filled strata. Write it to `goal/evidence/corpus-acquisition.md` as a table:
   title / path-or-source / strata / why selected / GT-B pair? — done when the table is
   complete and self-consistent with the manifest.
   **[HUMAN-GATE: Logan approves or edits the selection + queue. Pause here.]**
2. **Stage local items** — copy approved locally-held files into
   `corpus/<slug>/original.<ext>` with `provenance.json` — done when every staged item
   has a provenance record whose sha256 matches the file.
3. **Run the zlibrary queue** — ≤10/day via zlibrary-mcp, EPUB-counterparts first —
   done when the approved queue is exhausted or 3 acquisition days have elapsed
   (whichever first; report remainder).
4. **GT-B readiness list** — enumerate staged scan+EPUB pairs (target ≥20 candidates;
   ≥5 will need to survive alignment for the Phase-0 gate) — done when the list is in
   the evidence file with both file paths per pair.

**Verification:** `ls corpus/*/provenance.json | wc -l` matches the approved count;
`python -c` sha256 spot-check on 3 random items matches provenance; `git status` shows
no corpus files staged; CI blob guard green on the PR that touches evidence/STATE.

**Completion evidence — file AND transcript:** fill `goal/evidence/corpus-acquisition.md`
(selection table, daily acquisition counts, GT-B pair list, verification output) and echo
the verification output + the ticked milestone list into the conversation.

**Pause / escalate when:** the HUMAN-GATE (always); a wanted item is unavailable on
zlibrary (log it, continue — don't substitute unilaterally if it changes stratum
balance); any ambiguity about whether an item's provenance is safe to record.

**Budget:** tokens: ≤120k per session, multi-day by design (zlibrary limit);
wallclock: ≤30 min/day of acquisition work; escalate-at: any single milestone exceeding
its second session — **except Milestone 3**, which spans up to 3 acquisition days by
design (escalate only if it stalls with the queue neither advancing nor exhausted).
