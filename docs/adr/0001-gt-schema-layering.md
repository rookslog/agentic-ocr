# ADR-0001 — GT schema: fork scholargt v2.0.0 and overlay L0–L3 layers

**Status:** Accepted (records an existing decision; the schema itself is **provisional —
frozen only at Phase 4**, revised against real material at the Phase-1 / E1 gate).
**Date:** 2026-06-19 · **Deciders:** Logan (per PLAN §4) · **Supersedes:** none ·
**Amended by:** [ADR-0002](0002-schema-evolution-policy.md) (schema-evolution policy; Proposed)

> This ADR was written to close a documentation gap, not to make a new decision: the fork
> choice is stated in `PLAN.md §4` and the L0–L3 layering appears in PLAN prose, but neither
> had a decision record in this repo (`docs/adr/` was empty). It records *what was decided
> and why*, and pins what remains open, so the choice is auditable and falsifiable.

## Context

The eval apparatus scores OCR/pipeline output against ground truth. Both ground-truth kinds —
synthetic **GT-A** (rendered from a schema by scriptorium) and paired-edition **GT-B** (a scan
+ a same-edition born-digital answer key) — must conform to one representation, which the
checkers (`eval/checkers/`) consume as PageGT-shaped dicts.

A schema already existed: **scholargt v2.0.0**, designed in the `scholardoc` repo through a
real, documented process (Phase 01 "universal-gt-schema" + Phase 01.1 "schema-taxonomy-review":
a stated design problem, an explicit *Alternatives Considered* table, a 6/6 verification
sign-off). Its **central unretired risk**, recorded in `PLAN.md §6`: *it has never survived
contact with real annotation.*

## Decision

1. **Fork, do not import.** Adopt `scholargt v2.0.0` as the seed schema via the standalone
   `loganrooks/scholar-schema` fork (import name `scholargt`); do **not** import the scholardoc
   monorepo. (PLAN §4.)
2. **Overlay an L0–L3 layering** as the representation's organizing axis:
   - **L0 Facsimile** — page geometry / spatial side (PageGT bboxes).
   - **L1 Transcription** — `Region.text` + a confidence model.
   - **L2 Structure** — reading order, region typing, footnote/anchor relations.
   - **L3 Semantics** — document-level relations (DocumentGT: notes↔markers, cross-refs).
3. **Defer fresh revision to evidence.** The forked schema is used **as-is (v2.0.0)** through
   Phase 0. The first revision pass (`v3.0-draft`) happens at the **Phase-1 / E1 gate**
   ("does real material fit the forked schema?"), and the representation is **frozen at
   `v3.0`, L0–L3, only at Phase 4**. (PLAN §9, §10.)

## Alternatives considered

- **Design a fresh schema from scratch** — rejected: discards a verified, alternatives-tested
  design; reintroduces risk the scholardoc deliberation already retired.
- **Import the scholardoc monorepo wholesale** — rejected: drags in the rotted pipeline and its
  coupling; the fork takes only the schema package (PLAN §4).
- **Freeze the schema now (v2.0.0 final)** — rejected: its annotation-validity risk is unretired;
  freezing before E1 would bake in untested assumptions. Deferral *is* the mitigation.

## Consequences

- **Positive:** scriptorium and the checkers can build against a stable v2.0.0 target through
  Phase 0; the annotation-validity risk has an explicit, gated mitigation (E1) rather than being
  silently assumed away.
- **Cost / open:** the **L0–L3 layering is currently an overlay asserted here and in PLAN prose,
  not encoded in the schema package** (the fork still exposes flat scholargt v2.0.0 classes:
  `PageGT`, `DocumentGT`). Whether L0–L3 should become first-class schema structure is itself a
  question for the E1 revision, not settled by this ADR.
- **Falsifier / what would reopen this:** if E1 shows real material does not fit v2.0.0 (regions,
  Note/marker model, or the layer boundaries break on actual scans/EPUBs), `v3.0-draft` revises
  the schema and a follow-up ADR supersedes the relevant parts of this one.

## References

- `PLAN.md` §4 (fork decision), §6 (annotation-validity risk), §9 (decision rule), §10 (phase gates).
- `experiments/E1/README.md` — E1 gates the first schema-revision pass.
- Inherited deliberation (read-only): `scholardoc/.planning/phases/01-universal-gt-schema/`
  and `01.1-schema-taxonomy-review-revision/`.
- `loganrooks/scholar-schema` @ `scholargt/schema/version.py` (`SCHEMA_VERSION = "2.0.0"`).
