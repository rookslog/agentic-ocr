# E6 — Tier×harness interaction

**Status:** prereg pending · run order: Phase 3.

**Hypothesis (one line).** Harness lift is **non-monotone across producer tiers**
(Apple fm / Haiku / Sonnet): the cheap-tier lift is largest, but per-tier tuning is
required — a Sonnet-tuned harness transfers *negatively* to fm.

**Pre-registered disconfirmer.** If a single harness shape transfers across all three
tiers without per-tier tuning (no negative transfer, monotone lift), the "tune per
tier" prior is falsified and the cost model can assume harness reuse.

Measures: the same task battery, per-tier-tuned vs transferred harnesses. This is the
experiment that **licenses or kills the "fm does the bulk thinking" cost model**
(PLAN §6, §7).

Full pre-registration → `prereg.md`. Derived from PLAN.md §9 E6.
