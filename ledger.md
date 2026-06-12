# Decision-observability ledger

Append-only. Per PLAN.md §8 item 4: *every significant pipeline change logs
predicted impact before, verdict after.* Rows are immutable once written — never
edit a past row; append a new one (with a back-reference) to correct or update it.

Verdict vocabulary (PLAN §8 item 1): `Corroborated` · `Reported` · `Resolved` ·
`Concordant` · `Survived current tests` · `Partially supported` · `Proxy support` ·
`Underdetermined` · `Not tested` · `Normative judgment`.

| # | Date | Change | Prediction (before) | Verdict (after) | Provenance |
|---|------|--------|---------------------|-----------------|------------|
| 1 | 2026-06-12 | Scaffold the `agentic-ocr` repo: port `eval/lib` scoring core from scholardoc `ground_truth/lib`, set up uv + pytest + ruff + mypy + CI, seed experiments E1–E7 preregs, runner skeleton, process files. | Ported metrics harness runs unchanged after import rebase (`ground_truth.lib` → `eval.lib`); the only code that breaks is the `scholardoc.models`-dependent adapter, which is deferred. CI lint/typecheck/test go green; no PDFs or >1MB blobs enter history. | **Survived current tests** — 44/44 ported unit tests pass; ruff + mypy clean; size/PDF guard finds nothing. `scholar_doc_to_elements` deferred as predicted (untested, `# pragma: no cover`). One scholardoc test left behind (regression test needs the rotted pipeline). | Commit `d4fd205` (PLAN/LICENSE/.gitignore) + scaffolding commit; `eval/lib/` ported from `./scholardoc@revival/2026-05-audit-and-reset`. |
