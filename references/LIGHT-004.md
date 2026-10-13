# LIGHT-004 — Thimijan and Heins light-unit interconversion review

## Citation

- Authors / organization: R. W. Thimijan and R. D. Heins
- Year: 1983
- Full title: *Photometric, Radiometric, and Quantum Light Units of Measure: A Review of Procedures for Interconversion*
- Journal / publisher / report: *HortScience*
- Volume, issue, pages: 18(6), 818–822
- DOI or stable URL: <https://doi.org/10.21273/HORTSCI.18.6.818>
- Local source file (if retained): Not retained
- Access date: 2026-10-13

## Source and scope

- Source type: Peer-reviewed methods review
- Site, cultivar, equipment, and study scale: Interconversion procedures
  among light measurement units for sunlight and electrical light sources
- What was measured or derived: The abstract describes conversion constants
  and procedures; the specific factor used by this project was not checked.
- Relevant page, table, figure, equation, or dataset fields: Article pages
  818–822; the conversion table/page for 4.57 was not inspected.

## Evidence extracted

| Claim or value | Source location | Original unit | Normalized value/unit | Uncertainty / qualification |
| --- | --- | --- | --- | --- |
| Procedures for interconverting photometric, radiometric, and quantum units | Article abstract and title | Multiple light units | General conversion methodology | The specific 4.57 µmol/J factor has not been verified from the paper |

## Connection to this project

- Reference ID and evidence role: LIGHT-004; candidate light-unit
  interconversion reference
- Code file and symbol: [`project/models/conversions.py`](../project/models/conversions.py),
  `PPFD_PER_PAR_WM2`
- Configuration key(s): Not applicable
- Related test(s): [`project/tests/test_conversions.py`](../project/tests/test_conversions.py)
- Adaptation made for this project: None until the full paper's conversion
  table is reviewed.
- Known differences or limitations: An article abstract about conversion
  procedures does not by itself verify the project's exact scalar.

## Validation record

- Dataset identity and version: Not applicable
- Calibration or independent validation: Not applicable
- Inclusion/exclusion and quality-control rules: Not assessed
- Metrics and uncertainty method: Not assessed
- Results and unresolved discrepancies: Exact 4.57 table/condition is not
  yet identified.
- Reproduction command and output: Not applicable

## Decision log

- Decision: Register as a candidate corroborating source, not proof of the
  current conversion.
- Rationale: Bibliographic metadata and scope are available, but the primary
  conversion table has not been checked.
- Date: 2026-10-13
- Follow-up needed: Obtain the article and identify the conversion value,
  spectral band, and exact table/page before citing it for 4.57.
