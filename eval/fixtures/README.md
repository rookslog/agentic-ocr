# eval/fixtures — status labels (ADR-0002 plank 5, Phase-0 half)

Labels recorded 2026-08-07 per the accepted schema-evolution policy
(`docs/adr/0002-schema-evolution-policy.md`). Consumer status was measured by
grep sweep (D-228 audit, corrected D-231): "consumer-free" = zero `.py`
references in the repo at audit time.

| Path | Status | Notes |
|---|---|---|
| `validation_set.json` | **LEGACY, consumer-free** | scholardoc-era error pairs (130 error / 77 correct). Kept as reference data; no code reads it. Remove-option stays open per plank 5. |
| `classified/` | **LEGACY, consumer-free** | 75 OCR-quality batch files, scholardoc-era. Same disposition. |
| `candidates/` | **LEGACY, consumer-free** | 4 candidate files (<1MB each), scholardoc-era. Same disposition. |
| `test_yaml/` | **LIVE-legacy — frozen seam** | scholardoc-YAML 1.1.0 fixtures consumed by `tests/test_normalize.py` via `eval/lib/normalize.py`. The loader is a frozen legacy seam (ADR-0002 plank 4): kept for this consumer, closed to new consumers. |

The E1-gate migration (`migrate_v2_v3()` + golden before/after fixtures) ships
in the same PR that bumps the schema pin — deferred by design (plank 5, E1 half).
