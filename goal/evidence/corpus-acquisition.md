# Evidence — Phase-0 evaluation corpus: starter selection + staging

**Goal:** A stratified evaluation corpus staged under `corpus/` with per-item provenance,
plus GT-B candidate pairs (scan + same-edition EPUB), assembled from Logan's owned library
first — with Logan's explicit approval before anything is acquired (`goal/corpus-acquisition.goal.md`).

**Status (2026-06-19, session `eaa44f15`):**
- **Milestone 1 — selection proposal:** ✅ approved at the HUMAN-GATE by Logan (this session,
  option "stage all + start builds").
- **Milestone 2 — stage local items:** ✅ done — **12 books / 15 files** copied into
  `corpus/<slug>/` with sha256-matched `provenance.json`.
- **Milestone 3 — zlibrary queue** and **Milestone 4 — GT-B readiness (≥20 pairs):** not
  started (expansion work; see §6).

> This is a deliberate **starter subset** (12 books, 3 GT-B pairs) of the packet's
> ~30-book / ≥20-pair objective — a "begin now from owned, materialized files" cut.
> Expansion is deferred to M3 + further owned-library mining.

---

## 1. Selection table (approved)

| slug | title | author | strata | GT-B pair | why selected |
|---|---|---|:--:|:--:|---|
| `of-grammatology` | Of Grammatology | Derrida | B/C | ✅ **confirmed** | flagship pair (same-edition JHU/Spivak); first smoke 0.904/0.870; dense apparatus |
| `specters-of-marx` | Specters of Marx | Derrida | B/C | ✅ uncertain | 2nd pair (Routledge Classics 2006 EPUB) |
| `totality-and-infinity` | Totality and Infinity | Levinas | A | ✅ uncertain | full-book scan + Nijhoff/Springer 2012 EPUB; hardest scan stratum |
| `writing-and-difference` | Writing and Difference | Derrida | A/C | — | apparatus-extreme; holds chapter *Violence and Metaphysics* |
| `margins-of-philosophy` | Margins of Philosophy | Derrida | B/C | — | holds chapter *Différance* |
| `introduction-to-metaphysics` | Introduction to Metaphysics | Heidegger | A/C | — | apparatus |
| `what-is-philosophy` | What Is Philosophy? | Heidegger | A/C | — | short; **author flagged** (resolved to Heidegger, not D&G) |
| `being-and-time` | Being and Time | Heidegger | B/C | — | ~590pp; SZ marginal pagination (Blackwell 2001) |
| `husserls-ideas` | Ideas (First Book) | Husserl | B/C | — | phenomenology core |
| `end-of-comparative-philosophy` | The End of Comparative Philosophy | Burik | A/C | — | Chinese/Daoist apparatus |
| `gibbs-why-ethics` | Why Ethics? | Gibbs | C | — | multi-register |
| `otherwise-than-being` | Otherwise Than Being | Levinas | B | — | EPUB; possible 4th GT-B pair (see §5) |

Strata tally: **A=1, A/C=4, B=1, B/C=5, C=1** (12 books). GT-B pairs: **3** (1 confirmed, 2 uncertain).

---

## 2. Staging (Milestone 2)

- **Copy-only** into `corpus/<slug>/{original,gt-source}.<ext>` + `provenance.json`. Originals
  never moved/renamed/deleted (the stager only `os.stat`s + reads them).
- Provenance per item: `sha256`, `bytes`, `source_path`, `format`, `strata`, `gtb_pair`,
  `edition_match`, `acquisition` (= "owned — local copy"), `staged_date`.
- **Reproducible** via `.local/stage_corpus.py` (gitignored). The stager is **stat-guarded**:
  any source with `st_blocks == 0` (a dataless cloud placeholder) is **skipped, never copied** —
  so it can never force a cloud download.
- Result: **12 slug-dirs, 15 files, 0 errors**; `sha256(src) == sha256(dst)` for every file.
  Staged manifest: `.local/corpus/staged-manifest.json`.

---

## 3. The eviction incident (why local-disk staging matters)

The owned-library manifest snapshot (2026-06-12) marked 258 files materialized. By 2026-06-19,
live `stat` showed **all 250 GoogleDrive "materialized" files had been evicted to 0-block
placeholders** (free-space reclamation) — including the Of Grammatology GT EPUB. After Logan
re-enabled GoogleDrive, all 14 re-materialized and were verified readable.

**Lesson:** CloudStorage is *not durable* for our purposes. Staging by **copy** to `corpus/`
(local `/dev/disk3s1`) immunizes the eval corpus against re-eviction — which is exactly what
Milestone 2 is for. (The OG smoke survived the eviction only because its extracted n-grams
were already on local disk in `.local/eval/`.)

---

## 4. Verification

```
$ ls corpus/*/provenance.json | wc -l          → 12   (matches approved slug count)
$ find corpus -type f \( -name '*.pdf' -o -name '*.epub' \) | wc -l → 15
$ git status --porcelain                        → (no corpus/ paths; only delegation-log.jsonl)
$ sha256 spot-check (3 random items) vs provenance.json → match
```

`corpus/` and `.local/` are gitignored (`.gitignore:5`, `:12`) + CI blob guard — no book bytes
can enter git.

---

## 5. Open items / flags

- **"What Is Philosophy" = Heidegger**, not Deleuze & Guattari (no D&G copy owned). Confirm
  intended author; a D&G copy would be a zlibrary item.
- **Specters + Totality GT-B edition matches are UNCERTAIN** — to be decided at the aligner /
  E1 alignment-coverage gate, not asserted now.
- **Of Grammatology** GT-B is **same-edition confirmed**; first text-fidelity **smoke**:
  recall 0.904 / precision 0.870 (`.local/eval/og_grammatology.scorecard.json`). SMOKE, not a
  benchmark — cross-edition normalization, no page aligner yet.
- **Otherwise Than Being**: a materialized scan-PDF exists on OneDrive (`…/Reading Now/Levinas/
  Levinas_OtherwiseThanBeing.pdf`) alongside the staged EPUB → could be upgraded to a **4th
  GT-B pair**. Flagged, not done.
- **`page_count` not yet recorded** in provenance (the packet lists it) — deferred; needs a
  `pdfinfo`/parse pass. Not blocking M2's sha256 verification.
- **Packet inventory note is outdated:** `corpus-acquisition.goal.md` says "Zero Derrida EPUBs
  exist locally" (from D-001, Downloads-only). The GoogleDrive `…/Library/` folder in fact holds
  Derrida EPUBs (Of Grammatology, Specters) + Levinas EPUBs (Totality, Otherwise Than Being).

---

## 6. Path to the full corpus target (≥30 books / ≥20 GT-B pairs)

- **M3 zlibrary queue (≤10/day):** EPUB counterparts for owned scans that lack one (grows the
  pair pool); under-filled strata — D (born-digital), German critical editions, Stephanus Greek,
  non-continental scans.
- **Mine the remaining owned library** (775 placeholders, now re-materializable) for same-edition
  scan+EPUB pairs; ≥5 must survive alignment for the Phase-0 gate (item 4).
