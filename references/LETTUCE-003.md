# LETTUCE-003 — Lorenz and Wiebe lettuce canopy/root parameters

## Citation

- Authors / organization: Lorenz and Wiebe; full author names not verified
- Year: 1980 (attributed in project notes)
- Full title: Not assessed
- Journal / publisher / report: Not assessed
- Volume, issue, pages: Not assessed
- DOI or stable URL: Not available
- Local source file (if retained): Not retained
- Access date: 2026-10-13

## Source and scope

- Source type: Attributed literature source; primary document not obtained
- Site, cultivar, equipment, and study scale: Soil-grown lettuce is the
  reported context for the root fraction; other scope details not assessed
- What was measured or derived: Root mass fraction, extinction coefficient,
  and leaf-area ratio are attributed to this source by project parameter notes.
- Relevant page, table, figure, equation, or dataset fields: Not assessed.

## Evidence extracted

| Claim or value | Source location | Original unit | Normalized value/unit | Uncertainty / qualification |
| --- | --- | --- | --- | --- |
| Root mass fraction `c_tau` | No primary location verified | Dimensionless | 0.15 | Soil-lettuce attribution; transfer to hydroponics is not established |
| Extinction coefficient `c_k` | No primary location verified | Dimensionless | 0.9 | Planophile-lettuce attribution, not verified |
| Leaf-area ratio `c_lar` | No primary location verified | m²/g | 75e-3 m²/g | Attribution and basis (dry mass, canopy definition) unverified |

## Connection to this project

- Reference ID and evidence role: LETTUCE-003; attributed literature parameters
- Code file and symbol: [`project/models/lettuce.py`](../project/models/lettuce.py),
  `LettuceParams.c_tau`, `c_k`, `c_lar`
- Configuration key(s): Not applicable
- Related test(s): [`project/tests/test_validation.py`](../project/tests/test_validation.py)
- Adaptation made for this project: None documented
- Known differences or limitations: The site's production system is
  hydroponic; a soil-derived root fraction may not transfer directly.

## Validation record

- Dataset identity and version: Not applicable
- Calibration or independent validation: Not performed
- Inclusion/exclusion and quality-control rules: Not applicable
- Metrics and uncertainty method: Not applicable
- Results and unresolved discrepancies: No source pages or parameter
  definitions have been verified.
- Reproduction command and output: Not applicable

## Decision log

- Decision: Do not use the soil-attributed `c_tau = 0.15` as the hydroponic
  default; the project instead uses 0.14 as a provisional hydroponic proxy
  derived from LETTUCE-005.
- Rationale: Sakamoto and Suzuki's primary Table 2 supports a mean derived
  root share near 0.14 for a different hydroponic lettuce cultivar. This is
  a better context match but is not site/cultivar calibration.
- Date: 2026-10-13
- Follow-up needed: Verify the original Lorenz–Wiebe source and obtain
  site/cultivar-specific root and top dry-mass data to assess the 0.14
  proxy's transferability.
