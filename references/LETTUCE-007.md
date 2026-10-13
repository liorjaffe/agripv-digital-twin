# LETTUCE-007 — Brunini et al. (1976) base temperature for lettuce, Bragantia

## Citation

- Authors / organization: O. Brunini; R. S. Lisbão; J. B. Bernardi; J. B. Fornasier; M. J. Pedro Júnior
- Year: 1976
- Full title: Temperatura-base para alface cultivar "White Boston", em um sistema de unidades térmicas
- Journal / publisher / report: Bragantia (Instituto Agronômico de Campinas)
- Volume, issue, pages: 35(1), 213–219
- DOI or stable URL: https://doi.org/10.1590/S0006-87051976000100019
- Local source file (if retained): Not retained (PDF/landing page saved in the project Anara library, folder AgriPV / Modelling)
- Access date: 2026-10-13

## Source and scope

- Source type: Peer-reviewed field phenology study (Brazil)
- Site, cultivar, equipment, and study scale: Campinas, SP; cv. White Boston; 15–17 historical plantings
- What was measured or derived: Base temperatures and thermal sums for emergence–transplant and transplant–harvest
- Relevant page, table, figure, equation, or dataset fields: English abstract (SciELO record); figures 1–2 not checked

## Evidence extracted

| Claim or value | Source location | Original unit | Normalized value/unit | Uncertainty / qualification |
| --- | --- | --- | --- | --- |
| Base temperature emergence–transplant | Abstract | °C | 6 °C | Different cultivar and soil system |
| Base temperature transplant–harvest | Abstract | °C | 10 °C | Conflicts with GDD-001 6.1 °C; kept as sensitivity case |
| Growth rate maximum at 22 °C, decreasing above | Abstract | °C | 22 °C | Development-rate observation, not dry-mass rate |

## Connection to this project

- Reference ID and evidence role: LETTUCE-007; peer-reviewed Brazilian context for TEMP-001 lower optimum and for GDD-001 base temperatures
- Code file and symbol: `project/models/lettuce.py`, `LettuceParams.t_opt_low_c` (22 °C), comment on `t_min_growth_c`
- Configuration key(s): Not applicable
- Related test(s): None
- Adaptation made for this project: 22 °C used as lower bound of the TEMP-001 optimum plateau; 10 °C base documented as alternative to GDD-001
- Known differences or limitations: Soil-grown head lettuce, 1970s cultivar; development, not biomass

## Validation record (if applicable)

- Dataset identity and version: Not applicable
- Calibration or independent validation: Not performed
- Inclusion/exclusion and quality-control rules: Not applicable
- Metrics and uncertainty method: Not applicable
- Results and unresolved discrepancies: Not applicable
- Reproduction command and output: Not applicable

## Decision log

- Decision: Retain GDD-001 6.1 °C (site-region hydroponic crespa) as default; document 10 °C as sensitivity
- Rationale: Sensitivity run (CROP-003) changes completed-cycle fresh mass by 0 to −17%
- Date: 2026-10-13
- Follow-up needed: None until site data are available
