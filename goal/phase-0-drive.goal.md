# /goal packet — Phase-0 completion DRIVER (autonomy policy + sequencer)

**Type:** driver / orchestration packet (NOT a build packet — it builds nothing
itself; it sequences the small per-item build packets and sets the autonomy policy so
the apparatus prep grinds to its gate with the *minimum* human check-ins). Honors
PLAN.md §11.2 "never a mega-packet": the actual builds stay small one-gate packets;
this packet only drives them.

**Why this exists (Logan, 2026-06-19):** "is there a goal that would continuously drive
you to the point where we have done all the prep work such that we can execute the other
actual goals that develop this repo? … i just get annoyed with continuously having to
come back and revisit … and you aren't working on something." This packet is the answer:
it converts the open-ended "where to next?" loop into a self-driving grind toward a fixed
terminal condition, surfacing to Logan ONLY genuine human-decisions.

---

## Terminal condition — the Phase-0 gate (verbatim, PLAN.md:248)

> **Gate:** CI green on all three repos; the same job runs on Mac and dionysus through
> the abstraction; ≥500 synthetic GT pages across strata incl. ≥1 sous-rature and ≥1
> multi-register template; ≥5 accepted GT-B pairs; checker suite runs end-to-end on GT-A.

When all five clauses hold + evidence is filed, Phase 0 is done and the **actual
repo-developing goals begin (Phase 1 — Instrument, run E1)**. This packet then closes.

---

## Operating / interruption policy — E1 stop-legitimacy, turned on myself

The default is **PROCEED**. I stop and surface only for a *legitimate* stop (the E1
criterion in `.local/research/decisions-15.md`, grounded in Logan's own rules). This is
the whole point: drive the unnecessary-stop rate to ~0.

**PROCEED autonomously (do NOT stop to ask) when the work is:**
- authorized + reversible + within a packet's Allowed scope;
- a build/verify/fix/refactor, a delegation, a doc/propagation sync, logging to
  `delegation-log.jsonl` / `ledger.md` / `STATE.md` status;
- a decision with an obvious default or one the code/PLAN already settles;
- anything I'd otherwise pause on merely to *report progress* or get authorization
  Logan's `propagation.md` says not to re-ask. → Just do it; note it in the running log.

**STOP and surface ONLY for (post-I-001 — the genuinely irreducible):**
- **irreducible creds / authorization** I cannot obtain or self-resolve: SSH to infra not
  yet authorized (dionysus), an MCP needing Logan's auth (zlibrary);
- a genuine **value conflict** resting on Logan's goals with no defensible default — NOT a
  design question I can settle by spike or draft-ADR + agential review;
- a declared packet **HUMAN-GATE** that is still *genuinely* open (most are now agential).

Default: everything formerly treated as a human gate is an **agential gate** (next section)
or self-resolved (spike / draft + agential review). **PR merges are agential, not Logan's
click.** When I do stop, I **batch** all open gates in one decision-presentation ask. An
interrupt / frustration from Logan = corroboration that I over-gated → tighten this policy.

---

## Gate register (post-I-001 de-gating intervention, evidence-backed 2026-06-19)

I-001 (`delegation-log.jsonl`) replaces human gates with **agential** review gates wherever
the human step was not irreducible. The drive runs the agential gates itself and logs them;
only the short "genuine human residuals" list pulls Logan in.

### Agential gates — run without Logan (logged)
| id | was | agential mechanism | status |
|----|-----|--------------------|--------|
| AG-1 | G1 "merge PR #3" | **agential PR gate**: opus adversarial review + codex connector cross-vendor review + `/pr-review-journal:pr-review-triage` → merge via `gh`. Evidence it needs no human: owner-authed, **0 required reviews**, PR `MERGEABLE`/`CLEAN`; only reviewer≠author (a norm) applies, satisfied agentially | IN PROGRESS — 7 review rounds done (D-210…D-246); certification D-247 cancelled (session-end stall, logged); re-launches D-248 (2026-08-07) AND D-247 both cancelled (session-end stall, platform limit); **re-routed cross-vendor as D-250 W1 (codex drive, 2026-08-12); merge executes on certified-clean** |
| AG-6 | eval/gtb merge gate | first T3-style review of the aligner (D-249, 3 lenses, opus/high) → fixes → PR `feat/gtb-aligner` + codex cross-vendor pass → agential merge | IN PROGRESS — D-249 cancelled (platform limit 2026-08-07, no findings); re-routed as D-250 W2 (codex drive, 2026-08-12) |
| AG-7 | ADR-0002 cascade | Accepted by Logan 2026-08-07 (single approval covers the whole cascade). Pre-G1 half: scholar-schema `v0.1.0` tag → pyproject pin → scriptorium pin PR → legacy-fixture labels. Post-G1 half (after AG-1 merge): vocabulary/version/seam CI mechanisms + BOTH enforcement probes (must flip CI red) | pre-G1 half DONE 2026-08-07 (tag v0.1.0 @ 8610d5e, pins, labels — PRs #4/scriptorium#2); post-G1 half = D-250 W4 |
| AG-4 | G4 "schema ADR" | I **draft** `docs/adr/0001-…` then agential review; escalate only on a real value conflict | QUEUED |
| AG-5 | G5 "scriptorium scope" | **spike**: draft one sous-rature template against the current schema; low rework → build in Phase 0, else → deferred follow-on. Self-resolved by evidence | QUEUED |

### Genuine human residuals — the short list that truly needs Logan
| id | gate | unblocks | status |
|----|------|----------|--------|
| H-1 | **Authorize SSH to dionysus** (add a Bash allow-rule, or run the cross-target smoke yourself via `! python -m runner.run …`) | gate clause 2, dionysus half only | **GRANTED 2026-08-07** (batched ask, option "scoped allow-rule") — installing the rule, then the smoke runs agentially |
| H-2 | **zlibrary auth** (the MCP needs Logan's auth) — ONLY if owned + PD mining can't yield ≥5 GT-B pairs | gate clause 4 beyond the staged pairs | **OPENED to the drive 2026-08-12** (operator, direct): H-2 delegated to the D-250 codex drive as a capped fallback (≤10/day, owned+PD first, bytes/provenance constraints unchanged). zlibrary-mcp mirrored into `~/.codex/config.toml`. See codex-drive W6 |

~~G2 corpus selection~~ — **STRUCK 2026-06-19**: local selection approved this session; 3 GT-B pairs staged (`corpus/{of-grammatology,specters-of-marx,totality-and-infinity}`).

---

## Worklist — autonomously grindable now (made precise by the gate-status audit)

Each becomes a small one-gate /goal packet, executed in order, delegated where it fits
the triage rubric, logged to `delegation-log.jsonl`. Status is established by the audit
(first drive action) and kept live in STATE.md.

1. ~~**Gate-status audit**~~ — DONE (re-audited 2026-08-07; scoreboard in STATE.md).
2. **Corpus generator → ≥500 GT pages** (scriptorium: schema-first renderers + augraphy
   degradation; ≥1 sous-rature, ≥1 multi-register) — the largest pure-build item; next
   after the in-flight gates. AG-5 spike (sous-rature template) precedes it.
3. ~~**GT-B aligner**~~ — DONE 2026-06-19/07-31 (D-209/D-229; evidence filed); under
   first T3 review (AG-6/D-249).
4. ~~**CI green on the sibling repos**~~ — DONE (both verified green 2026-08-07).
5. **Runner cross-target abstraction** — local-mac half + committed smoke job; dionysus
   half unblocked by H-1 grant, smoke owed.
6. **GT-B pairs 4–5** — stage Otherwise Than Being (owned OneDrive scan + staged EPUB);
   mine remaining owned library (ruled autonomous 2026-08-07); PD-lane pairs also count.
7. **PD lane + filter probe** (operator ruling 2026-08-07) — ~3-page probe (GT-A synthetic
   page + PD pages through the unchanged vision contract) tests filter-is-copyright-specific;
   then PD pair sourcing (archive.org + Gutenberg/Perseus) with provenance.
(Checker suite / gate clause 5 = built; D-248 certification → AG-1 merge in flight.)

---

## Drive mechanism — never idle

Each worklist item runs as a workflow/agent in the background. On completion I
**verify (spot-check load-bearing claims myself) → log disposition → propagate STATE.md /
ledger.md / evidence → advance to the next item**, re-invoked by the completion
notification. I do not end a turn parked on a question while autonomous work remains; if
the only remaining work is gated, I surface the batched gate register and stop. The
delegation-log + (local) cost ledger trace the drive.

## Verification / evidence
Per-item: the item's own packet acceptance + `goal/evidence/<item>.md`. Gate-level: the
five clauses each cite a reproducible check. `ledger.md` carries the predict→verdict for
each item.

## Pause / escalate when
Any human-gate (batched per the policy); a kill-criterion (a gate clause unmeetable
within its VOI budget → log `design-and-shelve`, don't drift — PLAN §13); a genuine
scope fork. **Otherwise: keep grinding.**

## Budget
Multi-session, runs until the gate or a kill-criterion. Per-item budgets live in each
small packet (default ≤140k, triage rubric). Escalate-at: any item that misses its
packet's escalate-at, or two consecutive items unable to advance without a gate.
