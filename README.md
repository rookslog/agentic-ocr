# agentic-ocr

Pipeline, eval/checkers, experiments, and execution runner for an agentic OCR +
semantic-segmentation system targeting humanities/philosophy libraries.

This is the *system-under-test* repo of a three-repo topology (see
[`PLAN.md`](PLAN.md) §11.1); it pins the schema and corpus-generator repos and
records their pins on every eval result.

**This README holds pointers only — no claims that can go stale (PLAN §11.2).**

| Document | Authority |
|---|---|
| [`PLAN.md`](PLAN.md) | Strategy. Edited only at phase gates. |
| [`STATE.md`](STATE.md) | What is true *now*. Read this first. |
| [`ledger.md`](ledger.md) | Append-only predict→verdict log. |
| [`experiments/`](experiments/) | Pre-registrations + results, immutable once verdict-labeled. |
| [`docs/prior-findings.md`](docs/prior-findings.md) | Distilled empirical record carried from scholardoc. |

## Layout

- `eval/` — checker suite + `eval/lib/` scoring core (ported from scholardoc).
- `eval/fixtures/` — JSON eval fixtures (no PDFs ever; PLAN §11.5).
- `tests/` — pytest suite for `eval/`.
- `experiments/E1…E7/` — one pre-registered experiment each (PLAN §9).
- `runner/` — SSH-over-Tailscale + rsync execution skeleton (PLAN §7.1).
- `docs/` — prior findings + ADRs.

## Dev loop

```bash
uv sync
uv run pytest
uv run ruff check .
uv run mypy
```

Phase 0 status (apparatus, no models yet) is tracked in [`STATE.md`](STATE.md).
