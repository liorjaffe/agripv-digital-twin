# LETTUCE-006 — Scaife (1973) lettuce relative growth rate vs temperature

## Citation

- Authors / organization: M. A. Scaife
- Year: 1973
- Full title: The early relative growth rates of six lettuce cultivars as affected by temperature
- Journal / publisher / report: Annals of Applied Biology
- Volume, issue, pages: 74(1), 119–128
- DOI or stable URL: https://doi.org/10.1111/j.1744-7348.1973.tb07730.x
- Local source file (if retained): Not retained (PDF/landing page saved in the project Anara library, folder AgriPV / Modelling)
- Access date: 2026-10-13

## Source and scope

- Source type: Peer-reviewed controlled-environment study
- Site, cultivar, equipment, and study scale: Six cultivars, growth cabinets at four constant temperatures, high light, ample nutrients; plants grown to about 0.2 g dry weight
- What was measured or derived: Relative growth rate (RGR), net assimilation rate, leaf area ratio vs temperature
- Relevant page, table, figure, equation, or dataset fields: Summary/abstract only (full text paywalled; not checked)

## Evidence extracted

| Claim or value | Source location | Original unit | Normalized value/unit | Uncertainty / qualification |
| --- | --- | --- | --- | --- |
| RGR at 10 °C | Summary | g/g/day | 0.11 g/g/day | Mean of six cultivars; early growth only (≤0.2 g DW plant⁻¹) |
| RGR at 22 °C | Summary | g/g/day | 0.35 g/g/day | Same |
| RGR–temperature relation is sigmoidal; NAR and LAR affected about equally | Summary | Not applicable | Not derived | Seedling stage; transfer to full canopy not established |

## Connection to this project

- Reference ID and evidence role: LETTUCE-006; literature evidence for the direction and approximate optimum of the temperature response (not a fitted parameter)
- Code file and symbol: `project/models/lettuce.py`, `LettuceParams.t_opt_low_c`, `get_f_temp`
- Configuration key(s): Not applicable
- Related test(s): `project/tests/test_lettuce.py::test_cool_air_no_longer_increases_daily_biomass_gain`
- Adaptation made for this project: Used qualitatively (cool air must reduce growth) and to place the lower optimum near 22 °C in the TEMP-001 trapezoid
- Known differences or limitations: Seedling-stage, UK cultivars, constant temperatures; abstract-level verification only

## Validation record (if applicable)

- Dataset identity and version: Not applicable
- Calibration or independent validation: Not performed
- Inclusion/exclusion and quality-control rules: Not applicable
- Metrics and uncertainty method: Not applicable
- Results and unresolved discrepancies: Not applicable
- Reproduction command and output: Not applicable

## Decision log

- Decision: Cite as primary evidence that the VAN-001 cold response (more growth when cooler) is physiologically wrong for lettuce
- Rationale: Threefold RGR difference between 10 and 22 °C
- Date: 2026-10-13
- Follow-up needed: Obtain full text; extract RGR at all four temperatures to fit the TEMP-001 rising limb
