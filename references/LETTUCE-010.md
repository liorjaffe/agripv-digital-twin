# LETTUCE-010 — Pearson et al. (1997) validated lettuce growth model with temperature

## Citation

- Authors / organization: S. Pearson; T. R. Wheeler; P. Hadley; A. E. Wheldon
- Year: 1997
- Full title: A validated model to predict the effects of environment on the growth of lettuce (Lactuca sativa L.): Implications for climate change
- Journal / publisher / report: Journal of Horticultural Science
- Volume, issue, pages: 72(4), 503–517
- DOI or stable URL: https://doi.org/10.1080/14620316.1997.11515538
- Local source file (if retained): Not retained (PDF/landing page saved in the project Anara library, folder AgriPV / Modelling)
- Access date: 2026-10-13

## Source and scope

- Source type: Peer-reviewed mechanistic crop model, calibrated on 8 crops and validated on 7 independent sources
- Site, cultivar, equipment, and study scale: UK field/protected lettuce; Rothamsted weather 1984–1995 for scenarios
- What was measured or derived: Two-pool (structural/storage) carbon model with instantaneous temperature and CO2 effects, thermal-time decline of photosynthetic rate, and temperature-dependent partitioning
- Relevant page, table, figure, equation, or dataset fields: Summary only (full text paywalled; equations not checked)

## Evidence extracted

| Claim or value | Source location | Original unit | Normalized value/unit | Uncertainty / qualification |
| --- | --- | --- | --- | --- |
| Model structure: storage pool fed by photosynthesis, depleted by respiration and conversion to structure | Summary | Not applicable | Not derived | Same two-pool concept as VAN-001 |
| Long-term thermal-time effect on photosynthetic rate | Summary | Not applicable | Not implemented | This is the mechanism missing from VAN-001 in this project |
| Warming shortens cycle but has little effect on final head weight | Summary | Not applicable | Not derived | Benchmark behaviour for CROP-003 seasonal results |

## Connection to this project

- Reference ID and evidence role: LETTUCE-010; target model structure for a future replacement of the TEMP-001 trapezoid
- Code file and symbol: Not connected (planned)
- Configuration key(s): Not applicable
- Related test(s): None
- Adaptation made for this project: None yet
- Known differences or limitations: Equations not yet extracted

## Validation record (if applicable)

- Dataset identity and version: Not applicable
- Calibration or independent validation: Not performed
- Inclusion/exclusion and quality-control rules: Not applicable
- Metrics and uncertainty method: Not applicable
- Results and unresolved discrepancies: Not applicable
- Reproduction command and output: Not applicable

## Decision log

- Decision: Adopt as the preferred long-term structure; TEMP-001 is an interim approximation
- Rationale: Validated against independent data and explicitly couples development (thermal time) with growth
- Date: 2026-10-13
- Follow-up needed: Obtain full text; extract equations and parameters; implement thermal-time decline of assimilation; re-run CROP-003 comparison
