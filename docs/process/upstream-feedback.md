# Upstream feedback — /goal packet format & related skills

**Purpose:** Logan's directive (2026-06-12): packets need not strictly follow goalflow
conventions, but every observed improvement to the packet format or its skills must be
recorded *retrievably* for later auditing / self-improvement workflows. This file is that
record. Each entry: what we deviated from, why, and what should be upstreamed (to
`goalflow/goal/TEMPLATE.goal.md`, the `escalation-watch` skill, or a new skill).
Append-only; date every entry.

## 2026-06-12 — drafting the first two agentic-ocr packets

1. **No data-hygiene slot.** TEMPLATE.goal.md has Forbidden, but corpus work needs a
   first-class "never enters git / never leaves the machine" section (PDFs, EPUBs,
   zlibrary provenance) distinct from "don't touch these paths." We added a **Data
   hygiene** section to our packets. → Upstream: add an optional slot to the template.

2. **No delegation/triage slot.** A packet executed by an orchestrating agent that
   itself delegates needs (a) a pointer to the triage rubric and (b) the obligation to
   log to `delegation-log.jsonl`. The template predates this layer. We added a
   **Delegation** section. → Upstream: optional slot + reference once the rubric
   stabilizes; candidate for a dedicated skill the packet can invoke.

3. **HUMAN-GATE is not first-class.** The template's "Pause / escalate when" conflates
   *planned blocking gates* (Logan must approve the corpus selection — known at
   authoring time) with *exception escalations* (surprise ambiguity). escalation-watch
   handles the latter well; the former deserves an explicit **HUMAN-GATE** marker on the
   milestone itself, so the executor plans the pause instead of discovering it.
   → Upstream: milestone syntax `N. <milestone> [HUMAN-GATE: <who decides what>]`.

4. **Budget slot is free text.** `Budget: <token / $ / wall-clock cap>` can't be compared
   against actuals by any later audit. We use a structured line
   (`tokens: …, wallclock: …, escalate-at: …`). → Upstream: structured budget fields;
   pairs with the meta-audit's token-prediction-calibration stat.

5. **Evidence-echo is evaluator-specific.** The template's warning ("Claude's /goal
   evaluator reads the transcript only") makes the *transcript* the only evidence
   channel. Better: the packet names a **completion-evidence file** (committed, e.g.
   `goal/evidence/<packet>.md`) that the executor fills AND echoes — then CI, humans,
   and both evaluator loops can all check it, and the evidence survives the session.
   We do both in our packets. → Upstream: add the file-based channel to the template.

6. **"Read first" list assumes goalflow's file set.** `INITIATIVE.md`, `docs/tenets.md`,
   `docs/glossary.md` don't exist in every project; this repo's equivalents are
   `STATE.md`, `PLAN.md` (sectioned), `ledger.md`. Minor: the template should mark that
   line as per-project, or projects should keep a stable alias (STATE.md is ours).

<!-- Append new entries above this line's section sibling, never rewrite old ones. -->
