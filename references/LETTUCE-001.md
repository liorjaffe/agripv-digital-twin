# LETTUCE-001 — Sweeney winter-lettuce yield factor attribution

## Citation

- Authors / organization: Sweeney et al.; full author list not verified
- Year: 1981 (attributed in project notes)
- Full title: *Modelling the growth of winter lettuce* (title attribution not verified)
- Journal / publisher / report: Not assessed
- Volume, issue, pages: Not assessed
- DOI or stable URL: Not available
- Local source file (if retained): Not retained
- Access date: 2026-10-13

## Source and scope

- Source type: Attributed literature source; primary document not obtained
- Site, cultivar, equipment, and study scale: Not assessed
- What was measured or derived: `c_yf = 0.8` is attributed to this source by
  the model's historical parameter notes.
- Relevant page, table, figure, equation, or dataset fields: Not assessed.

## Evidence extracted

| Claim or value | Source location | Original unit | Normalized value/unit | Uncertainty / qualification |
| --- | --- | --- | --- | --- |
| Yield factor `c_yf` | No primary page/table/equation verified | Dimensionless | 0.8 | Attribution only; meaning and value require source confirmation |

## Connection to this project

- Reference ID and evidence role: LETTUCE-001; attributed literature parameter
- Code file and symbol: [`project/models/lettuce.py`](../project/models/lettuce.py), `LettuceParams.c_yf`
- Configuration key(s): Not applicable
- Related test(s): [`project/tests/test_validation.py`](../project/tests/test_validation.py)
- Adaptation made for this project: None documented
- Known differences or limitations: Source title, author list, and primary
  location remain unverified.

## Validation record

- Dataset identity and version: Not applicable
- Calibration or independent validation: Not performed
- Inclusion/exclusion and quality-control rules: Not applicable
- Metrics and uncertainty method: Not applicable
- Results and unresolved discrepancies: Parameter is not independently checked.
- Reproduction command and output: Not applicable

## Decision log

- Decision: Preserve the current value as attributed-unverified.
- Rationale: No primary source evidence was available to support changing it.
- Date: 2026-10-13
- Follow-up needed: Obtain the original Sweeney et al. source and record the
  complete citation plus the exact location and definition of `c_yf`.
