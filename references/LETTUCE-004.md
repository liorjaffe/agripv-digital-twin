# LETTUCE-004 — Goudriaan and Monteith canopy light-interception equation

## Citation

- Authors / organization: J. Goudriaan and J. L. Monteith
- Year: 1990
- Full title: *A mathematical function for crop growth based on light interception and leaf area expansion* (bibliographic title attribution not yet confirmed)
- Journal / publisher / report: *Annals of Botany* (attributed)
- Volume, issue, pages: 66, 695–701 (attributed)
- DOI or stable URL: Not verified
- Local source file (if retained): Not retained
- Access date: 2026-10-13

## Source and scope

- Source type: Attributed peer-reviewed methods paper; primary full text not
  inspected
- Site, cultivar, equipment, and study scale: General crop-growth method;
  lettuce-specific scope not assessed
- What was measured or derived: The exponential canopy light-interception
  form used to scale maximum photosynthesis is attributed to this paper.
- Relevant page, table, figure, equation, or dataset fields: Exact equation
  number and page not verified.

## Evidence extracted

| Claim or value | Source location | Original unit | Normalized value/unit | Uncertainty / qualification |
| --- | --- | --- | --- | --- |
| `f_phot = (1 - exp(-k × LAR × (1 - tau) × X_sdw)) × f_phot_max` | Primary equation/page not verified | Depends on state and parameter units | Implemented as written in `get_f_phot` | Functional form and any biomass/leaf-area scaling assumptions must be confirmed in the primary source |

## Connection to this project

- Reference ID and evidence role: LETTUCE-004; attributed literature equation
- Code file and symbol: [`project/models/lettuce.py`](../project/models/lettuce.py), `get_f_phot`
- Configuration key(s): Not applicable
- Related test(s): [`project/tests/test_validation.py`](../project/tests/test_validation.py)
- Adaptation made for this project: Uses the current `c_k`, `c_lar`,
  `c_tau`, and structural dry biomass state.
- Known differences or limitations: Source equation and the equivalence of
  project state/units are not yet verified.

## Validation record

- Dataset identity and version: Not applicable
- Calibration or independent validation: Not performed
- Inclusion/exclusion and quality-control rules: Not applicable
- Metrics and uncertainty method: Not applicable
- Results and unresolved discrepancies: Equation is attributed, not confirmed.
- Reproduction command and output: Not applicable

## Decision log

- Decision: Keep the equation labeled as attributed-unverified.
- Rationale: The exact source location and title/DOI were not available in the
  evidence inspected.
- Date: 2026-10-13
- Follow-up needed: Obtain the primary paper and record the exact equation
  number/page, confirm variable definitions and units, and compare it directly
  with `get_f_phot`.
