# LIGHT-002 — Meek et al. PAR-to-solar-radiation relationship

## Citation

- Authors / organization: D. W. Meek, J. L. Hatfield, T. J. Howell,
  S. B. Idso, and R. J. Reginato
- Year: 1984
- Full title: *A Generalized Relationship between Photosynthetically Active Radiation and Solar Radiation*
- Journal / publisher / report: *Agronomy Journal*
- Volume, issue, pages: 76(6), 939–945
- DOI or stable URL: <https://doi.org/10.2134/agronj1984.00021962007600060018x>
- Local source file (if retained): Not retained
- Access date: 2026-10-13

## Source and scope

- Source type: Peer-reviewed primary study
- Site, cultivar, equipment, and study scale: Solar/PAR radiation
  observations and comparisons across western U.S. sites; not the UFSC site
- What was measured or derived: Generalized relationship between PAR
  irradiance and solar irradiance.
- Relevant page, table, figure, equation, or dataset fields: Article abstract
  reports a 45% estimate for PAR (0.4–0.7 µm) relative to daily solar
  irradiance and a separate 41% filtered-pyranometer measurement over
  0.285–0.63 µm at Fresno; exact internal table/figure was not verified.

## Evidence extracted

| Claim or value | Source location | Original unit | Normalized value/unit | Uncertainty / qualification |
| --- | --- | --- | --- | --- |
| Daily PAR fraction estimate | Article abstract | Fraction of daily solar irradiance | 0.45 | Supports 0.45 as a study-specific estimate; not a universal constant or a UFSC site measurement |
| Fresno filtered-pyranometer measurement | Article abstract | 0.285–0.63 µm band relative to solar irradiance | 0.41 | Not the same spectral band as PAR (0.4–0.7 µm); do not treat as a direct PAR fraction |
| Project fixed PAR fraction | Project simplification | Fraction | `PAR_FRACTION = 0.45` | Source-informed approximation; condition-specific variation is not represented |

## Connection to this project

- Reference ID and evidence role: LIGHT-002; literature support for an
  approximate PAR fraction
- Code file and symbol: [`project/models/conversions.py`](../project/models/conversions.py),
  `PAR_FRACTION`, `ghi_to_par`
- Configuration key(s): Not applicable
- Related test(s): [`project/tests/test_conversions.py`](../project/tests/test_conversions.py)
- Adaptation made for this project: Uses the study's 0.45 estimate as a
  constant multiplier from total shortwave GHI to PAR-equivalent energy.
- Known differences or limitations: The measurement band and local sky/
  atmospheric spectrum may differ; one source estimate does not establish
  the full 0.40–0.50 range for all conditions.

## Validation record

- Dataset identity and version: Meek et al. (1984) study; local input data
  not used
- Calibration or independent validation: Not calibrated against site
  co-located PAR and pyranometer measurements
- Inclusion/exclusion and quality-control rules: Not assessed from full text
- Metrics and uncertainty method: Not extracted from full text
- Results and unresolved discrepancies: The abstract supports the 0.45
  estimate, but the exact table/figure and the review-noted 0.40–0.50 range
  remain unverified.
- Reproduction command and output: Project conversion is
  `ghi_to_par(ghi) = ghi * PAR_FRACTION`.

## Decision log

- Decision: Keep 0.45 as a fixed source-informed scenario approximation,
  explicitly not a measured site value or universal ratio.
- Rationale: The primary article abstract supports 0.45 as an estimate and
  also demonstrates that spectral band definition affects the ratio.
- Date: 2026-10-13
- Follow-up needed: Inspect the full article for exact methods/table/figure
  and quantified variability; obtain co-located site PAR/GHI measurements
  before calibration.
