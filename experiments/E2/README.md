# E2 — Baseline ladder

**Status:** prereg pending · run order: after E1.

**Hypothesis (one line).** A local small VLM + checker suite (C0) lands within
usable distance of frontier-model transcription on clean and mid-difficulty strata,
and establishes **B\*** (the baseline every contender must beat) with measured
cost/throughput on real hardware.

**Pre-registered disconfirmer** (for the "small VLMs suffice" prior). B\* CER on the
**rough-scan stratum > 2× frontier reference** ⇒ the cascade must escalate more than
budgeted ⇒ revisit the §7 cost model.

Contenders: PyMuPDF tier-0; olmOCR-2; PaddleOCR-VL; Marker; Docling; raw
Haiku-vision (reference point); fm-assisted variants. Output: B\*, measured
cost/throughput (validates §7), stratified error profile.

Full pre-registration → `prereg.md`. Derived from PLAN.md §9 E2.
