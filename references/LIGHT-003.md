# LIGHT-003 — Pashiardis PAR measurement and modeling study

## Citation

- Authors / organization: S. Pashiardis
- Year: 2022
- Full title: *Measurements and Modeling of Photosynthetic Active Radiation (PAR) at a Semi-Mountainous Site in Cyprus*
- Journal / publisher / report: *Biomedical Journal of Scientific & Technical Research*
- Volume, issue, pages: 47(3), article 007502; page range not verified
- DOI or stable URL: <https://doi.org/10.26717/bjstr.2022.47.007502>;
  <https://biomedres.us/fulltexts/BJSTR.MS.ID.007502.php>
- Local source file (if retained): Not retained
- Access date: 2026-10-13

## Source and scope

- Source type: Peer-reviewed journal article; full text not inspected in this
  review
- Site, cultivar, equipment, and study scale: Semi-mountainous site in Cyprus,
  according to the title; not the UFSC site
- What was measured or derived: PAR measurements and modeling. It is noted
  as a source summarizing prior studies on PAR/global ratios.
- Relevant page, table, figure, equation, or dataset fields: Not verified;
  no numeric range from the article is claimed in this register.

## Evidence extracted

| Claim or value | Source location | Original unit | Normalized value/unit | Uncertainty / qualification |
| --- | --- | --- | --- | --- |
| PAR/global-solar variability and related literature | Full-text location not inspected | Ratio | No range extracted | Review notes attribute a 0.40–0.50 range and environmental dependence; this entry does not verify those claims |
| Reported PPFD/GHI ratio range | No source location verified | µmol/J | 1.7–2.9 as reported in supplied review notes | Not independently confirmed; may reflect both fPAR and spectral-conversion changes |

## Connection to this project

- Reference ID and evidence role: LIGHT-003; candidate supporting study for
  spectral/atmospheric variation
- Code file and symbol: [`project/models/conversions.py`](../project/models/conversions.py),
  `PAR_FRACTION`, `PPFD_PER_PAR_WM2`
- Configuration key(s): Not applicable
- Related test(s): [`project/tests/test_conversions.py`](../project/tests/test_conversions.py)
- Adaptation made for this project: None; the full article's numerical
  results have not been checked.
- Known differences or limitations: Cyprus study conditions do not define
  the UFSC site's conversion ratio.

## Validation record

- Dataset identity and version: Not applicable to project inputs
- Calibration or independent validation: Not performed against UFSC data
- Inclusion/exclusion and quality-control rules: Not assessed
- Metrics and uncertainty method: Not assessed
- Results and unresolved discrepancies: No extracted data substantiate
  the claimed 0.40–0.50 fraction or 1.7–2.9 µmol/J range.
- Reproduction command and output: Not applicable

## Decision log

- Decision: Treat the reported broad ranges as unverified context, not as a
  quantified confidence interval for this project's conversion.
- Rationale: Article metadata is identified, but its full text and cited
  primary numeric sources were not inspected.
- Date: 2026-10-13
- Follow-up needed: Inspect the full article and its cited Papaioannou/
  Alados primary studies, record exact tables/conditions and verify whether
  the 0.40–0.50 and 1.7–2.9 claims are supported.
