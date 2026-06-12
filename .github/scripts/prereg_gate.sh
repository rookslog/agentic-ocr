#!/usr/bin/env bash
# prereg-gate (PLAN.md §11.2): an experiment results file cannot merge unless its
# prereg file is ALREADY in history — i.e. merged in an EARLIER PR than the results.
#
# This enforces pre-registration mechanically. You cannot retro-fit a hypothesis to
# a result you already have: prereg and results must land in separate PRs, prereg
# first. See experiments/README.md for the full rule.
#
# Runs on pull_request only. Inputs (env, set by the workflow):
#   BASE_SHA  — the merge-base of this PR with the base branch (main).
#   HEAD_SHA  — the PR head commit.
#
# Logic:
#   1. Find files this PR adds/changes (A or M) matching  experiments/E*/results*.
#   2. For each affected experiment dir E?, require its prereg file
#      (experiments/E?/prereg.md) to ALREADY exist at BASE_SHA (the merge-base).
#   3. If a results* file is added/changed while its prereg is not in BASE_SHA,
#      FAIL.

set -euo pipefail

BASE_SHA="${BASE_SHA:?BASE_SHA not set}"
HEAD_SHA="${HEAD_SHA:?HEAD_SHA not set}"

# Files added (A) or modified (M) by this PR, relative to the merge-base.
mapfile -t changed < <(git diff --name-only --diff-filter=AM "$BASE_SHA" "$HEAD_SHA")

# Filter to results files under experiments/E*/  (results.md, results.json, results-2.md, ...)
results_files=()
for f in "${changed[@]}"; do
  if [[ "$f" =~ ^experiments/(E[^/]+)/results ]]; then
    results_files+=("$f")
  fi
done

if [[ ${#results_files[@]} -eq 0 ]]; then
  echo "prereg-gate: no experiments/E*/results* files added or changed — OK."
  exit 0
fi

echo "prereg-gate: results files in this PR:"
printf '  - %s\n' "${results_files[@]}"

fail=0
# Collect the unique experiment dirs touched.
declare -A seen
for f in "${results_files[@]}"; do
  [[ "$f" =~ ^experiments/(E[^/]+)/ ]] || continue
  exp="${BASH_REMATCH[1]}"
  [[ -n "${seen[$exp]:-}" ]] && continue
  seen[$exp]=1

  prereg="experiments/${exp}/prereg.md"
  # Does the prereg ALREADY exist at the merge-base (an earlier merged PR)?
  if git cat-file -e "${BASE_SHA}:${prereg}" 2>/dev/null; then
    echo "  OK   ${exp}: ${prereg} present at merge-base (${BASE_SHA:0:8})."
  else
    echo "  FAIL ${exp}: ${prereg} is NOT in history at the merge-base."
    echo "       Pre-registration must merge in an EARLIER PR than results (PLAN §11.2)."
    echo "       Open a prereg-only PR for ${exp} first, then add results in a follow-up PR."
    fail=1
  fi
done

if [[ $fail -ne 0 ]]; then
  echo "prereg-gate: FAILED."
  exit 1
fi
echo "prereg-gate: PASSED."
