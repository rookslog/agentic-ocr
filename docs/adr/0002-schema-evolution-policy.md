# ADR-0002 — Schema-evolution policy: bounded blast radius for GT-schema revisions

**Status:** **Accepted** 2026-08-07 by Logan (option "Accept, execute cascade" — one approval
authorizes the full cascade: v0.1.0 tag + pins + legacy labels now; CI mechanisms + both
enforcement probes post-G1). Rev 3 (rev 1 REQUEST-CHANGES → rev 2 APPROVE-WITH-AMENDMENTS by
the same 3-lens reviewer, D-231; amendments N-1–N-6 folded in — changelogs at bottom).
**Deciders:** Logan.
**Amends:** ADR-0001 (adds the *how* of the revision that ADR schedules; changes none of
its decisions). **Date:** 2026-07-31.

## Context

ADR-0001 pins scholargt v2.0.0 through Phase 0 and *schedules* revision (v3.0-draft at the
E1 gate, freeze at Phase 4). Schema change is therefore a certainty; the question is whether
a revision is a bounded change or a rewrite. Measured position (D-228 coupling audit +
delegator spot-checks + D-231 review corrections, 2026-07-31):

- **The scholargt seam exists and holds — for keys.** All checker consumption funnels
  through `PageView`/`RegionView` (`eval/checkers/pagegt.py`); zero raw scholargt-key access
  elsewhere in `eval/checkers/` (independent grep). `Checker`/`CheckResult` is generic
  (`PageLike = Mapping[str, Any]`, `eval/checkers/base.py:35`).
- **But the seam's real exposure is label VOCABULARY, not keys** (D-231 L1-3): hardcoded
  label sets (`_NOTE_SPATIAL_LABELS` etc., `pagegt.py:46-59`) plus the deliberate
  unknown-label→"other" mapping mean a v3 label rename silently reclassifies regions and
  mis-scores with a green exit code — the worst class, since the exit code is destined to
  become a reward signal (`base.py:10-11`). The vocabulary is also already duplicated AND
  diverged in tests (`tests/_mutations.py:88`: 3-member note set vs the seam's 5).
- **There are TWO live schema seams, not one** (D-231 L1-2): scholargt via `pagegt.py`, and
  the legacy scholardoc-YAML 1.1.0 loader `eval/lib/normalize.py` — live and tested
  (`tests/test_normalize.py:13` consumes `eval/fixtures/test_yaml/`).
- **The stamp is decorative.** Fixtures carry `"schema_version"` but zero code reads it.
- **Nothing is pinned.** No scholar-schema in `pyproject.toml`/`uv.lock` (the only "scholar"
  hit is a comment); scriptorium's own scholar-schema dep is commented out pending a
  pinnable tag — no repo has any tag at all (devops sweep D-234 #4).
- **Truly consumer-free legacy data:** `eval/fixtures/candidates/`, `classified/`, and
  `validation_set.json` (grep: zero .py references). `test_yaml/` is NOT consumer-free.

## Decision (policy — five planks, roughly ordered by dependency: the pin enables the rest)

1. **Pin the schema, first and now.** Add `scholar-schema` to `pyproject.toml` at a
   resolvable ref (`pyproject.toml` is NOT G1-locked — the packet's Allowed scope names
   it outright, `goal/gtb-aligner.goal.md:17-20`; PR #3 touches no pyproject). Enabler:
   cut `scholar-schema v0.1.0` (no tag exists today), which also unblocks scriptorium's
   commented-out dep; scriptorium is pinned in the same PR that cuts the tag, so
   "resolvable" has an owner and a trigger (D-231 N-6). **Mechanism (post-G1):** a CI job
   validating the committed fixtures against the pinned schema (template: the existing
   validator-script job pattern, `ci.yml:86-93`).
2. **Vocabulary integrity, derived from the pin.** One vocabulary source, asserted
   `⊆` the pinned scholargt enums, imported by BOTH the checkers and the test
   builders/mutators (removing the measured 3-vs-5 divergence). **Mechanism (post-G1):**
   CI check that every label literal in `eval/checkers/` + `tests/_mutations.py` is a
   member of the pinned enum (or the retired-label allowlist `pagegt.py:42-52` documents).
   Depends on plank 1 — which is why the pin goes first.
3. **Version stamps are read, machine-visibly — split by side.** A
   `SCHEMA_VERSION_EXPECTED` constant lands in `eval/checkers/`; a dedicated
   `SchemaVersionChecker` (id `schema-version`) joins the checker list — it receives
   `(candidate, gt)` and knows both sides natively, which a `PageView`-side surface
   cannot (all eight call sites pass GT and candidate identically, and nothing built
   inside a view reaches `Scorecard.results`; D-231 N-1) — emitting mismatch as a
   severity-graded CheckResult (the crashed-flag precedent, `base.py:245`), never a
   Python warning (CI-invisible; D-231 L3-2): **GT-side mismatch =
   hard severity** (a wrong-version answer key is an invalid instrument, not scoreable
   input); **candidate-side mismatch/absence = info** (the tolerate-malformed-candidates
   stance stands, correctly scoped to candidates only). `eval/gtb` page-key artifacts stamp
   the generating pin version — the key-index writer moves from the gitignored smoke
   script into tracked `eval/gtb/page_keys.py` so the field is CI-assertable (closes
   D-231 L1-5 and N-4). **Mechanism (post-G1):** CI asserts the version field is present
   in scorecard JSON output.
4. **One seam per schema, mechanically guarded.** scholargt shape is touched only in
   `eval/checkers/pagegt.py` (+ one test-only builder that replaces the raw-key fixture
   dicts in 6 test files); the legacy scholardoc-YAML 1.1.0 loader
   (`eval/lib/normalize.py`) is declared a **frozen legacy seam** — kept for its live
   consumer, closed to new consumers. **Mechanism (post-G1):** a `git ls-files`-based grep
   guard (template: `ci.yml:49-83`) failing on scholargt key literals outside the seam and
   on new imports of the legacy loader.
5. **Label the legacy now; migrate at E1.** Phase-0 half: mark `eval/fixtures/candidates/`,
   `classified/`, `validation_set.json` as legacy (README note) or remove them —
   remove-option restricted to these three verified consumer-free paths; `test_yaml/` is
   labeled LIVE-legacy and stays. E1 half (deferred by design, and that is ~90% of this
   plank): `migrate_v2_v3()` + golden before/after fixtures ship in the same PR that bumps
   the pin.

## Alternatives considered

- **Multi-version adapter/plugin registry now** — rejected: one schema version has ever
  been used in anger; registry machinery before a second version exists is speculation.
  Revisit at Phase-4 freeze, when community extension points (Checker implementations,
  scriptorium templates) become real.
- **Version mismatch as hard-fail everywhere / as warning only** — both rejected for the
  split in plank 3: hard-fail on candidates contradicts the recorded tolerate-malformed
  stance; a Python warning is CI-invisible (decorative). The adopted middle rung — a
  severity-graded CheckResult — uses machinery the repo already has (`base.py:37,245`).
- **Hand-maintained vocabulary lists (status quo)** — rejected: divergence is not
  hypothetical, it is measured (`_mutations.py:88` vs `pagegt.py:46-48`); negative
  controls can drift into testing the wrong labels while green.
- **Do nothing (rely on the seam as-is)** — rejected: the seam is held by convention;
  the stamp is unread; nothing records which schema version the suite was validated
  against. The repo's own principle is "enforce mechanically what you can; review what
  you can't; never rely on discipline" (PLAN.md:264) — every plank above names its
  mechanism or is explicitly the review-tier exception.

## Consequences & sequencing

- **Now (pre-G1):** plank 1's pin (pyproject unlocked) + the v0.1.0 tag on scholar-schema;
  plank 5's labeling half touches only `eval/fixtures/` READMEs (unlocked).
- **Post-G1:** every `.github/` mechanism (planks 1–4) and all `eval/checkers/` +
  `tests/` edits — G1's locked set is `eval/checkers/`, `tests/`, **`.github/`**
  (PR #3 modifies `ci.yml`). G1 exit is the **agential AG-1 merge gate** (intervention
  I-001), not a human merge click; that gate is being re-driven now after its silent
  6-week stall (D-210, agential sweep V2).
- **Doctrine note (not a plank — demoted per D-231 L2-1):** producers emit intermediate
  representations; a compiler emits schema instances ("IR-then-compile"). The vision-pilot
  contract v0 (`.local/vision-pilot/PROMPT.md`, gitignored — described here because it
  cannot be linked) already works this way, which is why its outputs survive any schema
  revision. This binds nothing today; the ADR that creates `pipeline/` must adopt or
  explicitly reject it.
- Cost accepted: a pin, one constant, one vocab module, two CI jobs from existing
  templates, README notes. No new abstraction layers.

## Falsifiers / what would reopen this

- **Phase-0 enforcement probes (testable as soon as the mechanisms land; if either leaves
  the build green, the policy is not enforcing and this ADR's central claim is refuted):**
  (i) rename a label in the vocabulary module (e.g. `note_area` → `note_region`) — the
  plank-2 ⊆-check must fail; (ii) rename the same label in a committed fixture, leaving
  `schema_version` untouched — the plank-1 fixtures-validate-against-pinned-schema job
  must fail. Probe (ii) is the one covering the silent-mis-scoring class (L1-3): unguarded,
  it yields a green build with wrong scores (`pagegt.py:39-40` maps unknown labels to
  "other"). (Split per D-231 N-2 — a fixture rename exercises plank 1, not plank 2.)
- **E1 falsifier (kept from rev 1):** if v3's restructuring changes checker *semantics*
  rather than data access (blast-radius cases (b)/(c) — e.g. L0–L3 first-class objects
  making DocumentGT note↔marker integrity page-reachable, which `footnote_anchor.py:6-13`'s
  escalation anticipates), "bounded = accessor edits" is refuted for that checker class; a
  follow-up ADR partitions checkers into shape-coupled vs semantics-coupled.

## References

ADR-0001 · PLAN.md:264 (§11) · D-228 audit + delegator spot-checks · D-231 3-lens review
(rev-1 verdict REQUEST-CHANGES) · D-233 agential sweep (D-210 stall) · D-234 devops sweep
(no-tags finding; ci.yml templates) · `eval/checkers/pagegt.py` · `eval/lib/normalize.py`
· `tests/_mutations.py` · `tests/test_normalize.py:13`.

## Changelog rev 1 → rev 2 (D-231 findings addressed)

L1-1 (false "zero consumers" — my compression error, not the audit's): corrected; remove-
option restricted to the three verified consumer-free paths. L1-2: two-seam reality stated;
plank 4 scoped per schema with the YAML loader frozen-legacy. L1-3/L1-4/L2-3: new plank 2
(vocabulary derivation) — the adopted alternative. L1-5: page-key artifacts stamp pin
version. L1-6: scriptorium pinning added to plank 1. L1-7 + L3-1: every plank names its CI
mechanism; new Phase-0 enforcement-probe falsifier. L2-1: IR-then-compile demoted to a
doctrine note. L2-2: hard-fail row repaired — GT/candidate split + the CheckResult middle
rung adopted. L2-4: plank 5's deferred fraction stated plainly. L3-2: warning surface
replaced with severity-graded CheckResult + named constant. L3-3/L3-4: sequencing corrected
(pyproject unlocked → pin first; `.github/` locked → mechanisms post-G1). L3-5: G1 exit
reframed as the agential AG-1 gate. L3-6: ADR-0001 back-link + `docs/adr/README.md` index
added in the same pass.

## Changelog rev 2 → rev 3 (re-review APPROVE-WITH-AMENDMENTS; N-1–N-6 applied)

N-1: delivery surface corrected to a dedicated `SchemaVersionChecker` (a PageView-side
surface cannot see which side it holds nor reach the Scorecard). N-2: falsifier split into
vocabulary-module and fixture probes, mapped to the planks they actually exercise. N-3:
ordering claim softened to dependency order. N-4: page-key index writer promoted to tracked
`eval/gtb/` so its stamp is CI-assertable. N-5: cites corrected (`base.py:10-11`;
Allowed-scope `:17-20` replaces the argument-from-silence `:23`). N-6: scriptorium pin
attached to the v0.1.0-tag PR.
