# LETTUCE-002 — van Holsteijn saturation-growth-rate attribution

## Citation

- Authors / organization: van Holsteijn; full author name not verified
- Year: 1981 (attributed in project notes)
- Full title: Not assessed
- Journal / publisher / report: Not assessed
- Volume, issue, pages: Not assessed
- DOI or stable URL: Not available
- Local source file (if retained): Not retained
- Access date: 2026-10-13

## Source and scope

- Source type: Attributed literature source; primary document not obtained
- Site, cultivar, equipment, and study scale: Not assessed
- What was measured or derived: The code's maximum growth-rate coefficient is
  attributed to van Holsteijn (1981).
- Relevant page, table, figure, equation, or dataset fields: Not assessed.

## Evidence extracted

| Claim or value | Source location | Original unit | Normalized value/unit | Uncertainty / qualification |
| --- | --- | --- | --- | --- |
| Saturation growth rate `c_gr_max` at 20 °C | No primary page/table/equation verified | s⁻¹ | 5e-6 s⁻¹ | Attribution and reference temperature unverified |

## Connection to this project

- Reference ID and evidence role: LETTUCE-002; attributed literature parameter
- Code file and symbol: [`project/models/lettuce.py`](../project/models/lettuce.py), `LettuceParams.c_gr_max`
- Configuration key(s): Not applicable
- Related test(s): [`project/tests/test_validation.py`](../project/tests/test_validation.py)
- Adaptation made for this project: None documented
- Known differences or limitations: The bibliographic identity and parameter
  location have not been established.

## Validation record

- Dataset identity and version: Not applicable
- Calibration or independent validation: Not performed
- Inclusion/exclusion and quality-control rules: Not applicable
- Metrics and uncertainty method: Not applicable
- Results and unresolved discrepancies: Parameter remains an attribution.
- Reproduction command and output: Not applicable

## Decision log

- Decision: Preserve the current value as attributed-unverified.
- Rationale: No primary-source evidence was available to support changing it.
- Date: 2026-10-13
- Follow-up needed: Identify the full van Holsteijn (1981) bibliographic
  record and verify the value, unit, temperature, and exact source location.
