# E? — <short title>

> Pre-registration template. Copy this file to `experiments/E?/prereg.md` and fill
> every field **before** the run (PLAN.md §8 item 2). Everything except *Results*
> is frozen once the prereg PR merges. *Results* is append-only.
>
> **Merge order is enforced (PLAN §11.2):** the prereg file must be merged in an
> *earlier* PR than any `results*` file for the same experiment. See
> [`../README.md`](../README.md) for how the CI prereg-gate checks this.

**Status:** `prereg` | `running` | `verdict-labeled`
**Owner:** Logan + Claude (experiment tracks stay interactive — PLAN §11.4)

## Hypothesis

<One claim, falsifiable. The thing we are testing.>

## Prediction

- **Expected fixes / wins:** <what improves, on which metric family, by how much>
- **At-risk regressions:** <what this change could *break* or trade off>

## Pre-registered disconfirmer

<The specific observation that would show the hypothesis FALSE — stated as a
threshold or comparison — AND how we will actively seek it (PLAN §8 item 6:
"what observation would have shown this false? was it sought?"). A disconfirmer
that cannot be sought is not a disconfirmer.>

## Baseline

<The free/cheap method this must beat (the X-003 pattern, PLAN §8 item 3).
Name it concretely: B*, C0, single-pass, etc. Δ ≤ 0 ⇒ cost without benefit.>

## Decision rule (including cost)

<Δ thresholds per metric family, *and* the cost ceiling. No single number flips the
decision unless the qualitative picture agrees (PLAN §8 item 3). State the cost
budget explicitly — quality-per-dollar, not quality alone.>

## Threats to validity

<Confounds, sample-size limits, Goodhart risk on shared checker/eval metrics,
benchmark-transfer caveats, self-grading (= Proxy support only).>

## Results (append-only)

> Append dated entries below as runs complete. Never edit a prior entry.

<!-- _yyyy-mm-dd_ — run id / pins (schema, generator) / outcome / verdict label per §8 -->
