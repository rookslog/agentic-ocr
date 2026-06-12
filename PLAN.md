# Agentic OCR + Semantic Segmentation for Humanities Libraries — Research & Build Plan

**Status:** Plan only — nothing implemented. **Date:** 2026-06-12.
**Working title:** `agentic-ocr` (may become scholardoc v3 — that is a Phase 4 decision, not a premise).

---

## 1. Mission: one product goal, one research question

**Product goal.** A pipeline that converts libraries of humanities/philosophy PDFs (rough/old scans, clean modern scans, heavy critical apparatus, multilingual quotation) into a representation richer than extracted text — at a target of **~200 books/day at ~$0.10/book** — serving downstream uses: audiobook generation, flashcards, agentic analysis, cross-text connection visualization, discourse mapping.

**Research question.** *Does an agentic pipeline beat a non-agentic one for this task — for which sub-tasks, at which model tiers, by how much, and at what cost?* We do not have an epistemically reliable answer, and the external evidence does not transfer cleanly to this domain (§2.4). The answer determines whether a future scholardoc supports an agentic configuration. The experiments in §9 are designed to answer it under the lab's epistemic standard (§8).

These two goals share infrastructure but are distinct: the product goal can succeed with a fully non-agentic pipeline; the research question is answered either way.

### Definitions: the agenticity ladder

"Agentic" hides four different architectures. All claims and experiments use this ladder:

| Level | Name | Control flow |
|---|---|---|
| **A0** | Fixed pipeline | No LLM control flow; deterministic stages (classical OCR + rules, or single-pass VLM per page) |
| **A1** | Cascade / routing | Data-dependent branching, no loops: confidence-routed escalation, consensus voting, model tiering |
| **A2** | Bounded loops | Per-artifact verify→revise loops with fixed iteration cap (k≤2), deterministic checkers as the verifier |
| **A3** | Open agent | An agent with tools decides per-book what to do, when to stop |

Prior evidence (§2) predicts the quality-per-dollar peak is at **A1 for transcription** and **A2 for structure recovery**, with A3 unjustified (4–8× token multiplier for marginal gains). These are pre-registered predictions, not conclusions.

---

## 2. Evidence base (what we know, with warrant labels)

Labels follow the epistemic standard (§8): **[Corroborated]** = we checked the primary source/file directly; **[Reported]** = subagent or secondary source asserts it, not independently checked; **[Uncertain]** = inference. Three research passes feed this: the AgenticHarnessResearch corpus, a web sweep of 2025–2026 document-AI literature, and a scholardoc repo audit. Source URLs/paths in §15.

### 2.1 Harness design (from the AgenticHarnessResearch lab)

- **The harness, not the model, dominates outcomes for weak models.** Harness choice moves aggregate scores ~24 points at fixed model+task; weak models are "performance hostage to the harness" — the biggest lift from good harness design accrues to exactly the cheap models we must use. [Reported — lab notes on arXiv 2605.27922]
- **Harness benefit is non-monotone and tier-specific.** The best harness shape differs per model; a Sonnet-tuned harness will not transfer to Haiku or Apple fm. Tune per tier. [Reported — lab notes on 2605.26731]
- **The dominant failure mode of structured extraction is format/contract drift, not wrong content** (36.4% of failures across frontier models; on capable models, 25/26 failures were format violations, never wrong answers). Mitigation: keep the output contract immediately adjacent to the generation step, out of long process preambles; long process-heavy prompts *cause* format drift. [Reported — lab notes on 2605.27922, 2605.26731]
- **Structure transfers, prose doesn't.** Gains localize to tools/middleware/data structures, not system-prompt wording. Engineering effort goes to interfaces, checkers, and the representation. [Reported — lab notes on 2604.25850]
- **Verifier ≠ producer; never cost-cut the verifier.** Producer can be cheap; the gate must be stronger and a separate role. [Reported — lab HANDOFF.md]
- **More harness ≠ better; agentic must earn its multiplier.** Multi-agent machinery is a ~4–8× token multiplier; the lab's default prior is that added structure is cost with non-guaranteed benefit. [Reported — lab multi-agent synthesis]
- **Files-as-environment / progressive disclosure:** never load a whole book into context; keep evidence in files, drill down. At our budget this is not hygiene but economics (§7). [Reported — lab notes on 2604.25850]

### 2.2 Document-AI state of the art (2025–2026)

- **Small specialized VLMs beat frontier general models on parsing at a fraction of cost:** PaddleOCR-VL 0.9B (OmniDocBench leader, 109 languages), MinerU2.5 1.2B (decoupled layout-pass-then-content-pass — the architecture pattern relevant to apparatus-heavy pages), olmOCR-2 7B (~10,000 pages for <$2 on one H100; trained via GRPO against deterministic "unit-test rewards"). [Reported — vendor blogs/papers]
- **For the hardest scholarly material, frontier models still lead:** on socOCRbench (historical scholarly scans) SOTA tops out ~0.6, with Gemini 3 Flash the cost-efficiency standout; multimodal post-correction reached <1% CER on 1754–1870 German. Non-Latin scripts systematically underperform. [Reported — socOCRbench; arXiv 2504.00414]
- **Hallucination is the dominant fidelity risk and self-reported confidence is miscalibrated.** VLM self-verification underperforms simple voting (the generate/verify asymmetry *reverses* for VLMs). External checks required: multi-engine consensus (Consensus Entropy: +42% F1 over VLM-as-judge at equal cost via adaptive routing) and deterministic programmatic assertions. [Reported — arXiv 2511.19806, 2509.17995, 2504.11101]
- **Constrained decoding is near-free reliability for cheap models** (observed 0%→75% on structured-output tasks with grammar constraints). Directly addresses the format-drift failure mode in §2.1. [Reported — JSONSchemaBench 2501.10868]
- **Public benchmarks do not cover our job:** olmOCR-Bench deliberately excludes footnotes, floating elements, and all non-English text. Footnote anchoring and critical apparatus are precisely the under-benchmarked capabilities. We must build our own eval. [Reported — llamaindex review of olmOCR-Bench]

### 2.3 scholardoc repo audit (branch `revival/2026-05-audit-and-reset`, cloned to `./scholardoc`)

- The repo is a dual-package monorepo: `scholardoc/` (the original extraction library, bit-rotted: two parallel OCR pipelines, a 1,524-line god module, empty `writers/`, 43–62% stale docs) and `scholargt/` (a GT schema package, genuinely well-built, zero-coupled to the rotted code). [Reported — repo audit; partially Corroborated below]
- **The scholargt v2.0.0 schema is the highest-value salvage.** Hybrid `PageGT` (spatial: regions, bboxes, reading order, registers) + `DocumentGT` (cross-page semantics: Note, Commentary, Citation, BibEntry, Section, SousRature, CrossReference, MarginalReference) with Stephanus/Bekker/Akademie/Diels-Kranz reference systems, RTL/bidi support, and per-element `VerificationRecord`s. **[Corroborated — read `scholargt/schema/{document,labels}.py` directly: class structure, reference-system enums, and v2.0.0 removal of cross-document links all check out.]**
- **The schema's central unretired risk: it has never survived contact with real annotation.** Zero verified GT documents exist; the audit rates this CRITICAL and prescribes pilot annotation before any extractor work. [Reported — `.planning/audit/2026-05-01/00-SYNTHESIS.md`]
- **Cross-document linkage was explicitly removed from v2.0.0** ("corpus layer concern") — yet discourse mapping and connection visualization are core goals here. The corpus layer must be designed by us (§4, L4). [Corroborated — `document.py` header documents the removal]
- **Narrow OCR-specific salvage:** spellcheck-as-selector finding (99.2% error detection, 23.4% false positives on philosophical terms), `ground_truth/lib/` metrics harness (~1,200 LOC, actively imported by tests), OCR-quality eval data (130 error pairs; classified Heidegger/Derrida/Hegel pages), 4 ADRs + 32 spikes. **Carry the findings and data; leave the code.** [Reported — repo audit]
- **There are no working downstream consumers.** Audiobooks/flashcards/mapping are vision-doc aspiration only. A fresh representation breaks nothing. [Reported — repo audit]

### 2.4 The agentic-vs-non-agentic evidence, and why it doesn't settle our question

The cleanest controlled comparison is ParseBench (arXiv 2604.08538): same vendor, single-pass vs agentic mode.
**[Corroborated — fetched the paper directly:]** overall 71.89% → 84.88% (+13.0); tables +17.6; visual grounding +22.1; **content faithfulness only 88.02% → 89.68% (+1.7)**; cost ~3× (<0.4¢/page → ~1.2¢/page).

Two implications and one caveat:

1. **The agentic dividend concentrates in structure/grounding/anchoring — not raw transcription.** Looping the transcription buys almost nothing; looping structure recovery buys a lot. This shapes the architecture (§6) and experiments E4/E5.
2. **OCR-Agent (+2.0 pts over 3 rounds) and "diminishing returns" studies corroborate small transcription gains at real cost.** [Reported — 2602.21053, 2506.04301]
3. **Caveat found in our own spot-check:** ParseBench's corpus is *enterprise documents* (insurance, finance, government) — not scanned books, footnotes, or critical apparatus. Its numbers pass through the evidence-appraisal card (§8) as *suggestive, non-transferable*. Severity line: the observation that would falsify transfer — agentic structure passes failing to beat single-pass on *our* gold set — has not yet been sought. That is experiment E4.

---

## 3. Stakeholders, user stories, and what "better than text extraction" means

scholardoc's original vision listed applications (RAG, Anki, citation management) but never derived representation requirements from them — and the things plain text extraction cannot do were never made explicit. Doing that now.

### 3.1 Stakeholders and stories

| Stakeholder | Story | Representation requirement (beyond text) |
|---|---|---|
| **Reading scholar** | "Quote and cite this passage by Bekker number / Akademie page, with confidence it's what the page actually says" | Canonical reference anchors; print-page↔span mapping; per-span provenance (bbox + confidence); apparatus preserved, not flattened |
| **Listener (audiobook)** | "Read me the book — main text only, footnotes on demand, Greek quoted properly" | Reading order; apparatus *separated* from body flow; dehyphenation; per-span language tags (TTS voice/pronunciation switching); chapter navigation |
| **Student** | "Make flashcards of key terms and claims from chapter 3" | Typed semantic elements; section context on every span; term/definition/quote structure |
| **Computational humanist** | "Query the corpus; export TEI; map a discourse" | TEI-exportable structure; stable IDs; corpus-level linkage (quotations, citations resolved to works) |
| **Agent / tool-builder** | "Retrieve, address, and reason over passages programmatically" | Stable addressable span IDs; structure-aware chunking; machine-readable confidence so agents know what to trust |
| **Archivist / fidelity guardian** | "Never present hallucinated text as the author's words" | Provenance on everything; uncertain spans *marked*, not silently smoothed; the representation distinguishes verified from generated |

### 3.2 The thesis

Text extraction yields strings. This representation yields **addressable, provenance-carrying, semantically typed, canonically citable objects**. Six properties no markdown dump has:

1. **Addressability** — stable IDs; canonical reference systems (Stephanus, Bekker, Akademie, SZ pagination) as first-class anchors.
2. **Provenance** — every span traces to a bbox on a page image, with confidence. Hallucination protection is *structural*, not aspirational: for this population, hallucinated text is worse than omitted text.
3. **Typed semantics** — body vs footnote vs block quote vs apparatus vs marginal reference are different *types*, not different markdown decorations.
4. **Multilingual span awareness** — Greek/German/French/Latin spans tagged with script and language.
5. **Print citability** — bidirectional mapping between print pagination and content position.
6. **Corpus linkage** — a layer above the document: bibliography entries resolved to works, quotations detected and linked across texts, the substrate for discourse mapping.

Every downstream story in 3.1 is enabled by some subset of these; none is enabled by plain extraction.

---

## 4. Target representation: layered, scholargt-seeded

**Decision (per Logan): design fresh, but respond to the user stories scholardoc never adequately derived requirements from.** We fork the scholargt v2.0.0 schema as the seed for layers L0–L3 — it encodes hard-won domain knowledge (registers, RTL, catchwords, reference systems) — and extend where the stories demand. We do *not* import the scholardoc monorepo.

| Layer | Contents | Seed |
|---|---|---|
| **L0 Facsimile** | Page images, dimensions, page labels, bboxes — the pixel ground every claim traces to | `PageGT` spatial side |
| **L1 Transcription** | Text per region with confidence + provenance; uncertainty marked in-band | `Region.text` + new confidence model |
| **L2 Logical structure** | Sections/ToC, paragraphs, reading order across registers, footnotes *anchored* to in-text markers, block quotes, hyphenation resolved | `DocumentGT` structure + `LayoutRegister` |
| **L3 Scholarly semantics** | Citations, marginal reference systems, apparatus, emphasis, sous rature, language/script tags per span | `SemanticElement` union |
| **L4 Corpus / discourse** | Cross-document: works registry, resolved bibliographies, detected quotations, concept indexing — the substrate for connection mapping | **New — deliberately excluded from scholargt v2; ours to design** |

Design rules carried from the evidence: output contracts (JSON Schema per layer) live adjacent to generation steps; grammar-constrained decoding wherever a model emits L1–L3 objects; L4 is a separate store built *on top of* document objects, never entangled with extraction. Exports (markdown, TEI, EPUB, audiobook manifest) are views, not the representation.

**Inherited risk, inherited fix:** scholargt's schema has never been annotation-tested (audit finding G1). Our pipeline is itself the better test vehicle the audit asked for — it generates draft GT whose *corrections* exercise the schema. Schema-revision triggers are pre-registered in E1.

---

## 5. Ground truth without manual labor (the scholargt problem, rethought)

The previous attempt stalled because GT required an annotation product (scholargt) which required a GT schema which was never validated — a circular dependency on Logan's labor. The rethink: **manufacture GT instead of annotating it**, three complementary sources, each with a pre-registered validity check.

### GT-A: Synthetic typeset corpus (perfect GT by construction)

Take trusted digital texts (Gutenberg, Wikisource, Perseus/Open Greek & Latin for Greek, Deutsches Textarchiv for German/Fraktur, plus EPUBs via the zlibrary-mcp server) → programmatically typeset with LaTeX templates that mimic scholarly layouts: footnotes/endnotes, marginal Stephanus/Bekker numbers, critical apparatus blocks, bilingual quotation, two-column, old-style fonts including Fraktur → render to PDF → degrade with a scan simulator (augraphy: skew, noise, bleed-through, scanner shadow, JPEG artifacts) at parameterized severity.

Because we authored the typesetting, we have **perfect text AND structure GT** (footnote anchors, reading order, region types) at zero annotation cost, with difficulty as a controlled variable. This is the only GT source that covers L2/L3 structure exhaustively.

The generator is its own public project, not a pipeline module (§11.1), and its design rule is **schema-first generation**: its input language is a `DocumentGT`/`PageGT` instance plus a degradation spec, so GT alignment holds by construction and every schema element must earn a renderer. The template set includes the hardest real layouts from the start — sous rature, Glas-style dual-register columns (Derrida), Talmudic/commentary frames (Rashi-style apparatus; Robert Gibbs) — the cases the schema claims to express and no public benchmark tests.

**Pre-registered disconfirmer (E1):** synthetic GT is a valid *selection instrument* only if pipeline variants rank the same on synthetic as on real-scan GT (GT-B). If rank correlation fails threshold, synthetic GT is demoted to smoke-testing.

### GT-B: Paired editions (real scans, aligned to trusted text)

Via zlibrary-mcp, fetch both the scan PDF and a born-digital edition (EPUB) of the same text. Anchor-based alignment (unique shared n-grams as anchors, dynamic-programming fill between) yields real-scan transcription GT; EPUB markup (headings, footnotes) yields partial structure GT. Edition mismatch is detected mechanically by alignment-coverage statistics — low coverage ⇒ pair rejected, no human judgment needed.

### GT-C: Consensus-divergence silver labels (ongoing, in-production)

Run 2–3 independent engines on sampled pages. Agreement = silver GT (calibrated against GT-A/B); divergence = automatic hard-case mining for the eval set and escalation triggers. A frontier-model panel arbitrates divergences, with its own agreement stats logged. Logan's labor: optional spot-verdicts on a tiny stratified sample, bounded at ~30 minutes total, used only to calibrate the silver labels — never as a pipeline dependency.

### The eval instrument built on this GT

olmOCR-2's "unit-test rewards" pattern, repurposed as our checker suite — deterministic assertions, no LLM judge in the loop:
footnote marker↔note pairing completeness · reading-order consistency across registers · hyphenation/dehyphenation legality (against lexicons) · quote/bracket balance · per-span language-ID agreement (Greek where Greek is expected) · schema validity · print-page mapping consistency · **anti-hallucination tripwires** (n-gram containment of output against GT/source; flagging fluent text in low-confidence image regions). Port `ground_truth/lib/` metrics (edit-distance, matching, normalization, reports) from scholardoc as the scoring core.

---

## 6. Architecture candidates and harness mechanisms

### Candidates (the contenders to trial — map to the ladder in §1)

- **C0 — Single-pass baseline (A0):** Tier-0 embedded-text extraction where a text layer exists (PyMuPDF; validated 32–57× faster in scholardoc spikes); one local small VLM pass (olmOCR-2 or PaddleOCR-VL class) per scanned page; deterministic post-processing (dehyphenation, checker suite); single cheap-LLM pass for L2 structure from compressed page features. *The free default every contender must beat (X-003 rule: Δ ≤ 0 ⇒ cost without benefit).*
- **C1 — Cascade (A1):** C0 + confidence-routed escalation: checker failures and low-confidence pages go to a stronger VLM (Gemini-Flash/Haiku-class); consensus voting on divergent regions. No loops. *Prediction: most of the cost-quality win lives here.*
- **C2 — Structure-agentic (A2):** C1 transcription (frozen) + bounded verify→revise loops for L2/L3 only: propose structure → run checkers → revise once with checker output in context. Layout-then-content decoupling (MinerU2.5 pattern) for apparatus-heavy pages. *Prediction from ParseBench (+22 grounding) and lab priors: this is where agentic earns its keep.*
- **C3 — Open agent (A3):** an agent with tools (re-OCR region, compare engines, consult ToC, look ahead/behind pages) plans per book. *Prediction: fails the cost gate at 200 books/day; trialed narrowly to test whether it finds error classes C2 misses — VOI-gated, smallest experiment last.*

### Harness mechanisms applied across all candidates (the "lift cheap models above baseline" toolkit)

1. **Grammar-constrained decoding** to layer schemas — eliminates the dominant (format-drift) failure mode for free.
2. **Output contract adjacent to generation; no process preambles** — process-heavy prompts measurably cause contract violations on cheap models.
3. **Verifier ≠ producer; verification never cost-cut** — deterministic checkers always; model-based verification only by a *stronger* model than the producer, on sampled/escalated output.
4. **No VLM self-confidence** — routing signals come from checkers + cross-engine agreement, never from the model's own confidence report.
5. **Files-as-environment** — page/region objects on disk; structure passes consume *compressed projections* (line styles, candidates, outlines), never whole-book text. At our budget this is load-bearing economics (§7).
6. **Per-tier tuning** — the harness is re-tuned for each producer tier (Apple fm / Haiku / Sonnet); E6 measures the tier×harness interaction rather than assuming transfer.

Model roles: **Apple fm (free, on-device)** — page-type classification, routing features, language ID, candidate filtering, dehyphenation arbitration. **Local small VLM** — bulk transcription. **Haiku-class (batch API)** — L2/L3 synthesis over compressed projections, escalated regions. **Sonnet/frontier** — verification sampling and GT-C arbitration only.

---

## 7. Cost & throughput model (planning estimates — validated in E2/E3, all [Uncertain] until measured)

Budget arithmetic at target scale: 200 books/day × ~400 pages = **80,000 pages/day ≈ 1 page/sec sustained**; $0.10/book = **0.025¢/page all-in**.

| Item | Estimate | Consequence |
|---|---|---|
| olmOCR-2-class local VLM | ~0.02¢/page reported (H100 FP8); ~4–5 pages/s ⇒ ~4.5 H100-hours/day ≈ $10–14/day spot | Bulk transcription fits budget **only** local/rented-GPU; M-series throughput unknown → measure |
| Haiku vision, per page | ~0.5¢/page (≈$2/book full-vision) | 20× over budget as bulk engine; affordable only for ≤~2% escalation, or ~5% with batch-API discount |
| Haiku text, whole-book structure pass | ~$0.45/book naive (200k tok in) | **Over budget alone** ⇒ structure passes must run on compressed projections (mechanism 5), targeting ≤$0.03–0.05/book |
| Apple fm | $0; throughput unknown on this Mac | The free tier for classification/routing — capability measured in E6 |

Three consequences worth stating plainly: (a) the cascade's escalation thresholds are **economically determined**, not just quality-determined; (b) progressive disclosure is what makes LLM structure synthesis affordable at all; (c) single-Mac throughput is an open risk — standing fallbacks are dionysus (§7.1) and, later, a rented GPU (~$10–15/day, inside budget) or cloud batch APIs. The experimental phase is exempt from the budget (find the quality ceiling first, then optimize down — but every run logs cost so the curve is known).

### 7.1 Compute topology: local-first, three targets

**Decision (Logan, 2026-06-12):** Mac-local by default — use Apple silicon where it makes sense, without overloading the daily-driver machine; **dionysus** (on Tailscale: GTX 1080 Ti 11GB, 32GB RAM, Intel Xeon) as the standing remote execution target; GPU rental supported as a third target but unused until needed.

| Target | Best suited for | Honest constraints |
|---|---|---|
| **Mac (Apple silicon)** | Apple fm tasks, MLX small-model experiments, dev loop, interactive eval | shared with daily use — batch jobs niced/capped, never saturating |
| **dionysus** | batch corpus rendering + degradation (augraphy is CPU-bound — the Xeon earns its keep), classical layout models, quantized GGUF VLM inference via llama.cpp, self-hosted CI runner, artifact store | Pascal (SM 6.1): **no vLLM** (requires ≥7.0), no tensor cores/FP8, FP16 not accelerated — a batch workhorse, not a modern serving target; 11GB fits a 7B VLM at 4-bit |
| **Rented GPU (later)** | full-speed engine benchmarking (e.g., olmOCR-2 FP8 on vLLM), Phase 4 scale-up | ~$2–3/hr; the config exists from Phase 0, the spend doesn't |

Engineering rule: **one execution abstraction from day 0** — jobs declare a target; the runner is plain SSH-over-Tailscale + rsync'd artifacts (+ containers where a stack demands it). No orchestrator or queue until batch-experiment scale demonstrates the need. One useful consequence of the Pascal constraint: **quality and throughput measurements decouple in E2** — engines needing modern serving stacks are scored for *quality* on dionysus (quantized, slow) and for *throughput/cost* in a short rented-GPU session, so most experimentation stays local and free.

---

## 8. Experimental protocol (the epistemic spine)

Adopted from AgenticHarnessResearch — borrowed, not nested: this project runs as its own apparatus and may write an uplift note back to the lab's `integration/`, but does not live inside its vault/governance machinery.

1. **Shared epistemic standard** (`meta/shared-epistemic-standard.md`): corroboration not verification; searching is testing. We adopt the proposed label set here (this project's choice; the standard is still `#proposed` lab-side): `Corroborated (scope, severity)` · `Reported` · `Resolved` · `Concordant` · `Survived current tests` · `Partially supported` · `Proxy support` · `Underdetermined` · `Not tested` · `Normative judgment`.
2. **Pre-registration.** Every experiment file is written *before* the run: Hypothesis · Prediction (expected fixes + at-risk regressions) · **Pre-registered disconfirmer** (the observation that would show the hypothesis false, and how we'll seek it) · Baseline · Decision rule (Δ thresholds *including cost*) · Threats to validity · append-only Results.
3. **The X-003 gold-set pattern, transplanted:** a free/cheap baseline every method must beat; **Δ ≤ 0 ⇒ the method is cost without benefit**; metrics are heuristics, not deciders — no single number flips a decision unless the qualitative picture agrees.
4. **Decision-observability ledger:** every significant pipeline change logs predicted impact before, verdict after (`ledger.md`, append-only).
5. **Evidence-appraisal card** for every imported benchmark number before it bears weight (setup/saturation, baseline fairness, metric construct validity, statistical robustness, transfer). Already applied once: ParseBench → *suggestive, non-transferable* (§2.4).
6. **Severity line on load-bearing claims:** what observation would have shown this false? was it sought? did it survive?
7. **Independent critic:** before any phase-gate conclusion, a fresh context-free agent red-teams the claim.
8. **Self-grading is `Proxy support`** — external surfaces (GT-B real scans, downstream-task probes) are required for any "it works" claim.

---

## 9. Pre-registered experiment programme

Order matters: the eval instrument is validated before it is used to select anything.

**E1 — GT validity (the instrument experiment).**
H: synthetic GT (GT-A) ranks pipeline variants concordantly with real-scan GT (GT-B). Method: ≥3 trivially-different pipeline variants scored on both; Kendall τ over variant rankings, per metric family. **Disconfirmer: τ < 0.7 on transcription metrics, or top-pick disagreement ⇒ GT-A demoted to smoke tests; selection runs on GT-B + GT-C only.** Also gates: alignment-coverage threshold for GT-B pair acceptance; first schema-revision pass (does real material fit the forked schema? — the audit's deferred pilot-annotation, executed mechanically).

**E2 — Baseline ladder.**
H: a local small VLM + checker suite (C0) lands within usable distance of frontier-model transcription on clean and mid-difficulty strata. Contenders: PyMuPDF tier-0; olmOCR-2; PaddleOCR-VL; Marker; Docling; raw Haiku-vision (reference point); fm-assisted variants. Output: B* (the baseline to beat), measured cost/throughput on real hardware (validates §7), stratified error profile. Disconfirmer for the "small VLMs suffice" prior: B* CER on rough-scan stratum > 2× frontier reference ⇒ cascade must escalate more than budgeted, revisit §7.

**E3 — Cascade dividend (A1 vs A0).**
H: confidence-routed escalation + consensus on divergent regions recovers ≥70% of the frontier-quality gap at ≤3× B* cost. **Disconfirmer: ΔQuality ≤ 0 or cost > pre-set ceiling ⇒ cascade is cost without benefit at this corpus mix.** Also tests: routing-signal ablation (checkers+agreement vs model self-confidence — prediction: self-confidence routing is *worse* than checker routing).

**E4 — The structure question (A2 vs A1) — the heart of the research question.**
H (from ParseBench + lab priors, both flagged non-transferable): bounded verify→revise loops on L2/L3 beat single-pass structure emission by ≥10 points on footnote-anchoring/reading-order/section metrics, at acceptable cost, with transcription held frozen. **Disconfirmer: Δstructure < pre-set margin (set when the metric variance is known from E2) ⇒ the agentic dividend does not transfer from enterprise docs to scholarly books — a publishable negative answer to the research question.**

**E5 — The transcription-loop question (A2 on L1).**
H (pre-registered *skeptically*): agentic re-OCR loops on flagged regions add ≤2 points over C1's consensus — i.e., **not** worth it beyond the cascade. Disconfirmer for the skeptical prior: Δ > cost-justified threshold on the rough-scan stratum ⇒ transcription loops earn a place for that stratum only.

**E6 — Tier×harness interaction.**
H: harness lift is non-monotone across Apple fm / Haiku / Sonnet producers; the cheap-tier lift is largest but per-tier tuning is required (Sonnet-tuned harness transfers negatively to fm). Measures: same task battery, per-tier-tuned vs transferred harnesses. This experiment is what licenses (or kills) the "fm does the bulk thinking" cost model.

**E7 (VOI-gated, smallest, last) — Open agent probe (A3).**
Run C3 on a small hard-stratum sample purely to mine error classes C2 misses. No throughput claims. Kill criterion: if C3 finds no error class C2 misses, A3 is closed for this domain and recorded as such.

**Programme-level decision rule (the scholardoc-config question):** the future scholardoc supports an agentic configuration **iff** E4 (or E5) clears its pre-registered margin on quality-per-dollar over C1 on at least one corpus stratum. Otherwise the answer is: cascade yes, agent no — and that is a satisfying, reportable answer.

---

## 10. Phases and gates

**Phase 0 — Apparatus (no models yet).**
Three public repos initialized with shared CI scaffolding (§11): `scholar-schema` (fork of scholargt v2.0.0 → v3-draft, L4 design sketch), the corpus generator (schema-first renderers + augraphy degradation), and `agentic-ocr` (`eval/` checkers + ported `ground_truth/lib`; `pipeline/` empty; `experiments/` pre-registrations; `ledger.md`; `STATE.md`). Execution abstraction running against both local targets (Mac, dionysus — §7.1). Corpus acquisition via zlibrary-mcp into the private store: stratified sample (clean modern / rough-old / apparatus-heavy; target ~30 books + ~20 GT-B candidate pairs). GT-B aligner built. **Gate: CI green on all three repos; the same job runs on Mac and dionysus through the abstraction; ≥500 synthetic GT pages across strata incl. ≥1 sous-rature and ≥1 multi-register template; ≥5 accepted GT-B pairs; checker suite runs end-to-end on GT-A.**

**Phase 1 — Instrument.** Run E1. **Gate: GT instrument validated (or demoted per disconfirmer) and schema v3.0-draft revised against real material.**

**Phase 2 — Baselines.** E2, E3. **Gate: B* and C1 characterized with real cost/throughput; §7 model replaced by measured numbers; corpus-stratum error profiles published to `experiments/`.**

**Phase 3 — The agentic question.** E4, E5, E6, then VOI-gated E7. **Gate: programme-level decision rule evaluated; claims labeled per §8 and red-teamed by independent critic.**

**Phase 4 — Synthesis & decisions.** (a) scholardoc v3: fresh-start repo becomes the successor (carrying schema fork + findings), with the old repo archived as reference — *recommended by the audit evidence, decided here*; (b) agentic-configuration verdict written up; (c) representation v3.0 frozen at L0–L3, L4 design doc issued; (d) optional uplift note back to AgenticHarnessResearch `integration/`; (e) scale-up plan (GPU rental vs batch APIs) for the 200/day product goal.

Kill criteria stand at every gate: a phase that cannot meet its gate within its VOI budget logs a `design-and-shelve` decision rather than drifting — the scholardoc failure mode this plan exists to avoid.

---

## 11. Development process & long-horizon governance

scholardoc didn't die of bad code; it died of process drift — stale authority docs, a stalled phase nobody resumed, three competing memory systems, a planning framework with 5/10 fit. The harness lab names the opposite failure in itself: "governance-rich, execution-thin." This section is the engineering-process layer, built on one principle carried over from the harness findings: **enforce mechanically what you can; review what you can't; never rely on discipline.** Each mechanism below traces to a finding in §2.1 or §2.3.

### 11.1 Repo topology: three public repos

| Repo | Contents | Why separate |
|---|---|---|
| `scholar-schema` | scholargt v2.0.0 fork → representation v3 (L0–L3 models, generated JSON Schema, L4 design doc) | It is the contract both other repos pin. Schema changes are load-bearing by definition — separating them makes every change a visible, versioned, reviewed event. scholargt's audited value came precisely from its independence. |
| corpus generator (name TBD, §14) | schema-first renderers (LaTeX), degradation engine (augraphy), corpus release tooling | (a) A standing side-goal with independent public value: a synthetic apparatus-heavy benchmark from public-domain sources fills the gap every public benchmark documents (footnotes, non-English, apparatus excluded). (b) Epistemic independence: the GT source must not cohabit with the system it evaluates, or checkers drift toward generator quirks (Goodhart). |
| `agentic-ocr` | pipeline, eval/checkers, experiments, ledger, STATE | The system under test. Pins exact versions of the other two; every eval result records both pins (provenance). |

Three repos cost coordination for a solo developer; the mitigation is identical CI scaffolding across all three, not merging them.

### 11.2 Documents with single authority (the anti-drift contract)

`PLAN.md` — strategy; edited only at phase gates. `STATE.md` — what is true *now*; updated every working session; the surface /goal packets and fresh agent sessions read first. `ledger.md` — append-only predict→verdict. `experiments/` — prereg + results, immutable once verdict-labeled. `README` — pointers only; no claims that can go stale. CI enforces the mechanically checkable: generated `schema.json` matches the models; counts/statuses in docs are generated, never hand-written; and **an experiment results file cannot merge unless its prereg file is already in history** — the epistemic standard as a merge gate, not a norm.

### 11.3 Review taxonomy — checks scaled to what they protect

| Tier | Scope | Trigger | Mechanism |
|---|---|---|---|
| **T1 — deterministic self-checks** | lint, types, unit + golden checker tests, schema-regen match, no-corpus-blob guard | every PR | CI, blocking |
| **T2 — standard PR review** | plumbing, scripts, runners | every PR | one reviewer pass; light |
| **T3 — load-bearing PR review** | `schema/**`, `eval/checkers/**`, generator renderers, `experiments/**/prereg*`, decision rules — anything that can *silently invalidate experiments* | path-labeled, automatic | deep multi-agent review + **reviewer ≠ author** (verifier≠producer, applied to process) + Logan approves |
| **T4 — design review** | representation v3, generator input language, execution abstraction, metric definitions | before an interface freezes (≈ phase gates) | written design doc + independent critic red-team in fresh context + Logan sign-off |
| **T5 — phase gate** | per §10 | phase boundary | checklist of **shipped, runnable artifacts** + experiment verdicts labeled per §8 + critic pass |

The T5 rule is the "execution-thin" guard: a gate item must name something that runs or measures. "Design complete" is not a gate item.

### 11.4 /goal and the division of labor

Two kinds of work, two execution modes:

- **Build tracks** (Phase 0 infra, generator renderers, checker suite, runners, aligner): well-specified, crisp acceptance, long-horizon — formatted as **small /goal packets**, one gate each, with `STATE.md` as the shared surface, phase gates expressed as HUMAN-GATEs, and escalation-watch as the supervision bridge. The scholardoc packet audit's lesson (25–40% success as-authored, acceptable only after revision) becomes policy: packets are revised before adoption and never grow into a mega-packet.
- **Experiment tracks** (E1–E7: design, prereg, runs, verdicts): judgment-heavy, and precisely where confirmation-seeking creeps in — **stay interactive** (Logan + Claude), never delegated to autonomous execution. Preregs and verdicts are human-reviewed by construction.

### 11.5 Public repos, CI, and what never leaves the machine

Public from day 0 (proposed: Apache-2.0 code; CC-BY-4.0 synthetic-corpus releases). **Never pushed:** acquired corpus PDFs, GT-B artifacts derived from them, zlibrary provenance of any kind — enforced by gitignore plus a T1 CI guard that rejects PDF/binary blobs. CI: GitHub Actions for T1 on every PR; **dionysus as a self-hosted runner** (over Tailscale) for scheduled model-touching integration jobs and a nightly small-GT eval smoke (GitHub-hosted runners have no GPU). Security decision needed (§14): self-hosted runners on *public* repos can execute fork-PR code — mitigations are approval-required for outside workflows, label-gated runner jobs that never trigger on fork PRs, or keeping model-touching CI on a private mirror. Branch protection on main; PRs mandatory even solo — the review tiers need PRs to attach to.

---

## 12. Salvage manifest (from `./scholardoc`)

| Take | As | Leave |
|---|---|---|
| `scholargt/schema/` (9 modules) + `generated/schema.json` | Fork → `schema/` (seed of L0–L3) | The dual-package monorepo and its GSD planning framework |
| `ground_truth/lib/` (~1,200 LOC metrics/matching/normalize) | Port → `eval/` | Both legacy OCR pipelines, `models.py` god module, empty `writers/` |
| `ground_truth/validation_set.json` (130 error pairs), `ocr_quality/classified/` | Eval fixtures | v1.1.0 YAML GT fixtures (stale schema — actively misleading) |
| ADRs, 32 spikes, FINDINGS (PyMuPDF speed, spellcheck-as-selector 99.2%/23.4%) | `docs/prior-findings.md` with provenance | All Era-1 root docs (43–62% stale) |

---

## 13. Risks and threats to validity

- **Process drift (the scholardoc failure mode):** mitigated by §11's mechanical enforcement; the residual solo-dev risk is review fatigue — T3 and T4 are the tiers never to skip.
- **Synthetic-real gap (GT-A):** the central instrument risk; E1 exists to measure it before anything is selected with it.
- **Corpus acquisition via zlibrary:** Logan's existing infrastructure, but bulk-scale acquisition is his legal/ethical call to make explicitly — flagged, not assumed.
- **Single-Mac throughput:** 1 page/sec sustained may not hold locally; fallback (rented GPU ≈ $10–15/day) is inside budget but changes the "local-first" character. Measured in E2.
- **Apple fm capability unknown** — assigned only fallback-safe roles until E6 reports.
- **Schema never annotation-tested** (inherited from scholargt): mitigated by making E1/Phase 1 the pilot-annotation the audit prescribed.
- **Benchmark transfer:** all imported numbers (ParseBench, OmniDocBench, olmOCR-Bench) fail domain-transfer to apparatus-heavy scholarly books in at least one way; none bears weight without the §8 appraisal card.
- **Goodhart on the checker suite:** checkers double as routing signals and eval metrics; periodic GT-B-only audits of checker-passing pages guard the gap.
- **Confirmation-seeking in our own search:** the web sweep asked for "promising approaches" (a support-collecting frame); E4/E5's skeptical pre-registrations and the independent-critic rule are the structural correction.

## 14. Open questions for Logan (none block Phase 0)

1. ~~Hardware~~ **Resolved 2026-06-12:** local-first (Apple silicon used sensibly, never overloaded), dionysus as the standing remote target, GPU rental supported later (§7.1).
2. **200 books/day:** hard requirement or aspiration? (It only binds at Phase 4 scale-up; experiments are unaffected.)
3. **Language priority** beyond Greek/German/French/Latin (Hebrew/RTL? The scholargt corpus was 33% RTL — does that reflect *your* corpus?)
4. **The lab relationship:** want the uplift note written back into AgenticHarnessResearch `integration/` at Phase 4?
5. ~~Generator repo name + licenses~~ **Resolved 2026-06-12:** `scriptorium`; Apache-2.0 code, CC-BY-4.0 corpus releases.
6. ~~Self-hosted CI on public repos~~ **Resolved 2026-06-12:** deferred — GitHub-hosted runners only until model-touching CI exists; the §11.5 mitigation gets chosen then.

## 15. Sources

Local: `/Users/rookslog/Projects/AgenticHarnessResearch/` (esp. `agentic-harness-research/{meta,research/notes,experiments/x-003-retrieval-goldset.md,HANDOFF.md}`); `./scholardoc` (esp. `scholargt/schema/`, `.planning/audit/2026-05-01/00-SYNTHESIS.md`, `ground_truth/`). Web (key): allenai.org/blog/olmocr-2 · arXiv 2604.08538 (ParseBench, corroborated) · 2504.11101 (Consensus Entropy) · 2509.17995 (VLM self-verification) · 2501.10868 (constrained decoding) · 2509.22186 (MinerU2.5) · 2504.00414 (historical German post-correction) · socOCRbench · github.com/opendatalab/OmniDocBench · IBM Granite-Docling/DocTags. Full agent reports with per-claim tags are in this session's transcript; re-derivable.
