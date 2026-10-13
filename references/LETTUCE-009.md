# LETTUCE-009 — Carotti et al. (2021) light × air × root-zone temperature in lettuce

## Citation

- Authors / organization: L. Carotti; L. Graamans; F. Puksic; M. Butturini; E. Meinen; E. Heuvelink; C. Stanghellini
- Year: 2021
- Full title: Plant Factories Are Heating Up: Hunting for the Best Combination of Light Intensity, Air Temperature and Root-Zone Temperature in Lettuce Production
- Journal / publisher / report: Frontiers in Plant Science
- Volume, issue, pages: 11, 592171
- DOI or stable URL: https://doi.org/10.3389/fpls.2020.592171
- Local source file (if retained): Not retained (PDF/landing page saved in the project Anara library, folder AgriPV / Modelling)
- Access date: 2026-10-13

## Source and scope

- Source type: Peer-reviewed controlled-environment study (open access, full text in library)
- Site, cultivar, equipment, and study scale: cv. Batavia Othilie; 48 combinations of PPFD 200/400/750, air and root-zone 20/24/28/32 °C; 29 days after transplant
- What was measured or derived: Fresh/dry mass, SLA, dry-matter content, light-use efficiency
- Relevant page, table, figure, equation, or dataset fields: Abstract; Introduction p. 2

## Evidence extracted

| Claim or value | Source location | Original unit | Normalized value/unit | Uncertainty / qualification |
| --- | --- | --- | --- | --- |
| SLA, shoot mass allocation and leaf water content peak near 24 °C air | Abstract | °C | 24 °C | Plant factory, non-limiting CO2 |
| Shoot dry-matter content at market size | Abstract | % | 2.6–4.2 % | Decreases with lower PPFD; relevant to the 5% DMF assumption |
| "Crop photosynthesis does not depend much on temperature" within a reasonable range; temperature drives organ development | Introduction, p. 2 | Not applicable | Not derived | Supports applying temperature to growth rather than claiming a photosynthesis mechanism |
| Highest air temperature tested | Methods/abstract | °C | 32 °C | Tip-burn at high air + low root temperature |

## Connection to this project

- Reference ID and evidence role: LETTUCE-009; literature evidence for TEMP-001 upper optimum/maximum and for the CROP-002 dry-matter range
- Code file and symbol: `project/models/lettuce.py`, `t_opt_high_c`, `t_max_growth_c`; `project/scenarios/crop_cycles.py`, `DRY_MATTER_FRACTION_OF_FRESH_MASS`
- Configuration key(s): Not applicable
- Related test(s): None
- Adaptation made for this project: TEMP-001 factor multiplies assimilation as a lumped growth-rate limitation, not as a claimed photosynthetic mechanism
- Known differences or limitations: Indoor, high-CO2, different cultivar

## Validation record (if applicable)

- Dataset identity and version: Not applicable
- Calibration or independent validation: Not performed
- Inclusion/exclusion and quality-control rules: Not applicable
- Metrics and uncertainty method: Not applicable
- Results and unresolved discrepancies: Not applicable
- Reproduction command and output: Not applicable

## Decision log

- Decision: Use for upper optimum (24 °C) and maximum (32 °C, highest tested); flag 5% DMF as at or above the published range
- Rationale: Full-text, peer-reviewed, factorial design
- Date: 2026-10-13
- Follow-up needed: Measure site dry-matter content at harvest
