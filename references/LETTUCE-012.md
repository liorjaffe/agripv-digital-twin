# LETTUCE-012 — Lima et al. (2018) hydroponic NFT lettuce dry-matter content

## Citation

- Authors / organization: T. J. L. Lima; R. Gazaffi; G. J. Ceccherini; L. Marchi; M. Martinez; C. G. Ferreira; F. C. Sala
- Year: 2018
- Full title: Volume of cells on trays influences hydroponic lettuce production
- Journal / publisher / report: Horticultura Brasileira
- Volume, issue, pages: 36(3) (pages not verified)
- DOI or stable URL: https://doi.org/10.1590/S0102-053620180320
- Local source file (if retained): Not retained (PDF/landing page saved in the project Anara library, folder AgriPV / Modelling)
- Access date: 2026-10-13

## Source and scope

- Source type: Peer-reviewed hydroponic NFT experiment (Brazil)
- Site, cultivar, equipment, and study scale: NFT; seedlings from trays of 10–50 cm³ per cell; harvests 22 and 29 days after transplant
- What was measured or derived: Shoot fresh and dry mass, productivity
- Relevant page, table, figure, equation, or dataset fields: Results text (SciELO full text)

## Evidence extracted

| Claim or value | Source location | Original unit | Normalized value/unit | Uncertainty / qualification |
| --- | --- | --- | --- | --- |
| Shoot dry-matter content at 22 DAT | Results | % | 4.0–4.9 % | By tray volume |
| Nursery stage can be skipped with ≥20 cm³ cells | Abstract | Not applicable | Not derived | Seedling size at transplant depends on tray/nursery protocol |

## Connection to this project

- Reference ID and evidence role: LETTUCE-012; Brazilian hydroponic evidence for the CROP-002 dry-matter fraction
- Code file and symbol: `project/scenarios/crop_cycles.py`, `DRY_MATTER_FRACTION_OF_FRESH_MASS`
- Configuration key(s): Not applicable
- Related test(s): None
- Adaptation made for this project: None (0.05 retained; sits at the top of 4.0–4.9 %)
- Known differences or limitations: Different cultivar; shoot only

## Validation record (if applicable)

- Dataset identity and version: Not applicable
- Calibration or independent validation: Not performed
- Inclusion/exclusion and quality-control rules: Not applicable
- Metrics and uncertainty method: Not applicable
- Results and unresolved discrepancies: Not applicable
- Reproduction command and output: Not applicable

## Decision log

- Decision: Retain 0.05 as a disclosed assumption; record that published hydroponic values are 2.6–4.9 %
- Rationale: A lower DMF would RAISE fresh-mass estimates (fresh = dry / DMF)
- Date: 2026-10-13
- Follow-up needed: Measure site dry-matter content
