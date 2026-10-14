# LETTUCE-008 — Thompson et al. (1998) shoot and root temperature in floating hydroponics

## Citation

- Authors / organization: H. C. Thompson; R. W. Langhans; A.-J. Both; L. D. Albright
- Year: 1998
- Full title: Shoot and Root Temperature Effects on Lettuce Growth in a Floating Hydroponic System
- Journal / publisher / report: Journal of the American Society for Horticultural Science
- Volume, issue, pages: 123(3), starts p. 361 (end page not verified)
- DOI or stable URL: https://doi.org/10.21273/JASHS.123.3.361
- Local source file (if retained): Not retained (PDF/landing page saved in the project Anara library, folder AgriPV / Modelling)
- Access date: 2026-10-13

## Source and scope

- Source type: Peer-reviewed controlled-environment hydroponic study
- Site, cultivar, equipment, and study scale: cv. Ostinata (butterhead), floating hydroponics, 35 days
- What was measured or derived: Dry mass at air 17/12, 24/19, 31/26 °C (day/night) × pond 17, 24, 31 °C
- Relevant page, table, figure, equation, or dataset fields: Abstract (open access); tables not checked

## Evidence extracted

| Claim or value | Source location | Original unit | Normalized value/unit | Uncertainty / qualification |
| --- | --- | --- | --- | --- |
| Maximum dry mass | Abstract | °C | 24 °C air / 24 °C pond | Butterhead, controlled environment |
| 31 °C air with 24 °C pond not significantly different from 24/24 | Abstract | °C | Not derived | Root cooling offsets hot air; this project does not model root-zone temperature |

## Connection to this project

- Reference ID and evidence role: LETTUCE-008; literature evidence for TEMP-001 upper optimum
- Code file and symbol: `project/models/lettuce.py`, `LettuceParams.t_opt_high_c` (24 °C)
- Configuration key(s): Not applicable
- Related test(s): None
- Adaptation made for this project: 24 °C used as upper bound of the optimum plateau
- Known differences or limitations: Root-zone temperature not represented; site beds are substrate, not floating

## Validation record (if applicable)

- Dataset identity and version: Not applicable
- Calibration or independent validation: Not performed
- Inclusion/exclusion and quality-control rules: Not applicable
- Metrics and uncertainty method: Not applicable
- Results and unresolved discrepancies: Not applicable
- Reproduction command and output: Not applicable

## Decision log

- Decision: Use as upper-optimum anchor
- Rationale: Hydroponic, peer-reviewed, dry-mass endpoint
- Date: 2026-10-13
- Follow-up needed: None
