# LETTUCE-013 — Logistic growth models for lettuce in spring

## Citation

- Authors / organization: Carini et al.
- Year: 2019
- Full title: Growth Models for Lettuce Cultivars Growing in Spring
- Journal / publisher / report: *Journal of Agricultural Science*
- Volume, issue, pages: 11(6), 147
- DOI or stable URL: https://doi.org/10.5539/jas.v11n6p147
- Local source file (if retained): Not retained
- Access date: Not recorded

## Source and scope

- Source type: Peer-reviewed lettuce growth-model study
- Site, cultivar, equipment, and study scale: Spring-grown lettuce cultivars; details not assessed beyond the abstract
- What was measured or derived: Growth models for fresh and dry lettuce mass as a function of accumulated thermal sum
- Relevant page, table, figure, equation, or dataset fields: Abstract

## Evidence extracted

| Claim or value | Source location | Original unit | Normalized value/unit | Uncertainty / qualification |
| --- | --- | --- | --- | --- |
| Logistic model fit to fresh- and dry-mass growth versus accumulated thermal sum | Abstract | Not reported here | Logistic models were reported as the best fit among models assessed | Abstract-level evidence only; cultivar, coefficient, and full methods details not evaluated |

## Connection to this project

- Reference ID and evidence role: LETTUCE-013; literature support for evaluating a logistic thermal-time curve, not a source of project fit coefficients
- Code file and symbol: `project/validation/fit_thermal_logistic.py`
- Configuration key(s): Not applicable
- Related test(s): `project/tests/test_fit_thermal_logistic.py`
- Adaptation made for this project: The source motivates a report-only fit of mean fresh mass per plant against TC accumulated GDD after sufficient field measurements and a harvest-date weighing are available.
- Known differences or limitations: The study was assessed at abstract level only. No cultivar-specific parameters or functional coefficients are transferred to this project.

## Validation record (if applicable)

- Dataset identity and version: Not applicable
- Calibration or independent validation: Not applicable
- Inclusion/exclusion and quality-control rules: Not applicable
- Metrics and uncertainty method: Not assessed
- Results and unresolved discrepancies: Not assessed beyond the abstract-level model comparison
- Reproduction command and output: Not applicable

## Decision log

- Decision: Treat the paper as a rationale for a future report-only fit, not as evidence to tune or replace the current biomass model.
- Rationale: Abstract-level evidence does not provide enough detail to transfer coefficients, and local cycle-1 data do not yet include a harvest weighing.
- Date: Not recorded
- Follow-up needed: Review the full paper before interpreting its model choices or applying any reported parameterization.
