# LIGHT-001 — PAR-to-PPFD conversion reference

## Citation

- Authors / organization: Not reported in the project notes
- Year: Not reported
- Full title: *Plant Growth Chamber Handbook*
- Journal / publisher / report: Handbook; publisher not reported
- Volume, issue, pages: Not reported
- DOI or stable URL: Not available in the project notes
- Local source file (if retained): Not retained
- Access date: Not assessed

## Source and scope

- Source type: Handbook, as identified in the project review notes
- Site, cultivar, equipment, and study scale: Not assessed
- What was measured or derived: A PAR-energy to PPFD conversion factor is
  attributed to this handbook in the project review notes
- Relevant page, table, figure, equation, or dataset fields: Not reported

## Evidence extracted

| Claim or value | Source location | Original unit | Normalized value/unit | Uncertainty / qualification |
| --- | --- | --- | --- | --- |
| PAR energy to photon flux | Not reported | Not reported | `4.57 µmol photons/m²/s` per `W/m² PAR` | Project uses this approximate factor; the source edition and location have not been verified |

## Connection to this project

- Reference ID and evidence role: LIGHT-001; intended literature reference for
  a conversion assumption
- Code file and symbol: [`project/models/conversions.py`](../project/models/conversions.py),
  `PPFD_PER_PAR_WM2`
- Configuration key(s): Not applicable
- Related test(s): [`project/tests/test_conversions.py`](../project/tests/test_conversions.py)
- Adaptation made for this project: Approximate scalar conversion; no
  wavelength-specific sensor response is modeled.
- Known differences or limitations: Source metadata and the relevant table or
  page are missing.

## Validation record

- Dataset identity and version: Not applicable
- Calibration or independent validation: Not applicable
- Inclusion/exclusion and quality-control rules: Not applicable
- Metrics and uncertainty method: Not applicable
- Results and unresolved discrepancies: Edition, publication details, and
  exact source location remain open.
- Reproduction command and output: Not applicable

## Decision log

- Decision: Retain the factor as an explicitly approximate assumption and do
  not claim a completed citation.
- Rationale: The exact handbook edition and page/table are not present in the
  repository or supplied notes.
- Date: 2026-10-12
- Follow-up needed: Obtain the referenced edition and record bibliographic
  metadata and source location.
