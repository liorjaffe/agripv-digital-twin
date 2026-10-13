# LIGHT-001 — PAR-band energy to PPFD conversion

## Citation

- Authors / organization: R. W. Langhans and T. W. Tibbitts (editors);
  John C. Sager and J. Craig McFarlane (chapter authors)
- Year: Not confirmed from the retrieved chapter scan
- Full title: *Plant Growth Chamber Handbook*, chapter 1, “Radiation”
- Journal / publisher / report: North Central Regional Research Publication
  No. 340; Iowa Agriculture and Home Economics Experiment Station Special
  Report No. 99
- Volume, issue, pages: Chapter 1, “Radiation”; internal page/table not
  verified from the image-based scan
- DOI or stable URL: [Official handbook page](https://www.controlledenvironments.org/growth-chamber-handbook/);
  [Chapter 1 page](https://www.controlledenvironments.org/growth-chamber-handbook-chapter-1-radiationjohn-c-sager-and-j-craig-mcfarlane/);
  [Chapter PDF](https://www.controlledenvironments.org/wp-content/uploads/sites/6/2017/06/Ch01.pdf)
- Local source file (if retained): Not retained
- Access date: 2026-10-13

## Source and scope

- Source type: Plant growth chamber handbook chapter
- Site, cultivar, equipment, and study scale: General radiation conversion
- What was measured or derived: Approximate conversion of PAR-band radiant
  energy to photon flux.
- Relevant page, table, figure, equation, or dataset fields: Chapter 1,
  “Radiation”; the PDF copy is image-based, so exact printed page/table and
  the 4.57 value were not verified.

## Evidence extracted

| Claim or value | Source location | Original unit | Normalized value/unit | Uncertainty / qualification |
| --- | --- | --- | --- | --- |
| PAR-band radiant energy to photon flux | Exact handbook table/page not verified | W/m² within PAR spectral band | 4.57 µmol photons m⁻² s⁻¹ per W/m² PAR | 4.57 is the project's attributed value; the scanned chapter has not been confirmed to contain it. Applies to PAR-band energy, not total global shortwave. |

## Connection to this project

- Reference ID and evidence role: LIGHT-001; approximate unit conversion
- Code file and symbol: [`project/models/conversions.py`](../project/models/conversions.py),
  `PPFD_PER_PAR_WM2`; [`project/models/lettuce.py`](../project/models/lettuce.py),
  `simulate_growth_timeseries`
- Configuration key(s): Not applicable
- Related test(s): [`project/tests/test_conversions.py`](../project/tests/test_conversions.py)
- Adaptation made for this project: A scalar factor of 4.57 is used for PAR
  energy to PPFD.
- Known differences or limitations: This is not the global-shortwave to PPFD
  factor; the project separately assumes a PAR fraction in LIGHT-002.

## Validation record

- Dataset identity and version: Not applicable
- Calibration or independent validation: Not applicable
- Inclusion/exclusion and quality-control rules: Not applicable
- Metrics and uncertainty method: Not applicable
- Results and unresolved discrepancies: Exact handbook edition and location
  have not been extracted from the primary chapter.
- Reproduction command and output: Unit conversion tests in the project test suite

## Decision log

- Decision: Keep the 4.57 factor labeled as approximate and PAR-band-specific;
  cite the handbook only as an unverified attribution.
- Rationale: Editors, chapter authors, report series, and official chapter
  pages are identifiable, but the scanned primary chapter has not been
  confirmed to contain 4.57.
- Date: 2026-10-13
- Follow-up needed: Obtain a text-searchable copy or inspect the scan with
  OCR; confirm publication year/edition, exact printed page/table, explicit
  PAR spectral-band basis, and whether it supports 4.57.
