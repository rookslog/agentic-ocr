# E1 — GT validity (the instrument experiment)

**Status:** prereg pending · run order: **first** (validate the instrument before
selecting anything with it).

**Hypothesis (one line).** Synthetic GT (GT-A) ranks pipeline variants
*concordantly* with real-scan GT (GT-B) — so GT-A is a valid selection instrument.

**Pre-registered disconfirmer.** Kendall τ < 0.7 on transcription metrics over
≥3 trivially-different variant rankings, **or** top-pick disagreement between GT-A
and GT-B ⇒ GT-A is demoted to smoke tests and selection runs on GT-B + GT-C only.

Also gates (per PLAN §9): the alignment-coverage threshold for GT-B pair acceptance,
and the first schema-revision pass (does real material fit the forked schema?).

Full pre-registration → `prereg.md` (copy `../_TEMPLATE.md`, merge before any run).
Derived from PLAN.md §9 E1.
