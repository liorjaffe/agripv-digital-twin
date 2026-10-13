# CHEM-001 — Carbon dioxide to carbohydrate stoichiometric mass ratio

## Citation

- Authors / organization: IUPAC; standard atomic-weight tables
- Year: Current standard atomic weights; edition not fixed
- Full title: *Standard Atomic Weights*
- Journal / publisher / report: International Union of Pure and Applied Chemistry
- Volume, issue, pages: Not applicable
- DOI or stable URL: <https://iupac.org/what-we-do/periodic-table-of-elements/>
- Local source file (if retained): Not retained
- Access date: 2026-10-13

## Source and scope

- Source type: Reference data / chemical stoichiometry
- Site, cultivar, equipment, and study scale: Not applicable
- What was measured or derived: Molar masses used for the project's
  CO₂-to-CH₂O mass conversion.
- Relevant page, table, figure, equation, or dataset fields: Standard atomic
  weights for C, H, and O; conversion is calculated from the formulae CO₂ and
  CH₂O.

## Evidence extracted

| Claim or value | Source location | Original unit | Normalized value/unit | Uncertainty / qualification |
| --- | --- | --- | --- | --- |
| `c_ch2o = M(CH₂O)/M(CO₂) ≈ 30/44` | Molecular formulas and standard atomic weights | g/mol | 0.6818 g CH₂O per g CO₂ | Rounded integer molar masses; this arithmetic coefficient is not a fitted crop parameter |

## Connection to this project

- Reference ID and evidence role: CHEM-001; stoichiometric conversion
- Code file and symbol: [`project/models/lettuce.py`](../project/models/lettuce.py), `LettuceParams.c_ch2o`
- Configuration key(s): Not applicable
- Related test(s): [`project/tests/test_validation.py`](../project/tests/test_validation.py)
- Adaptation made for this project: Uses rounded molar masses in the
  historical model equation.
- Known differences or limitations: The original model's exact biochemical
  interpretation of the conversion remains to be checked against VAN-001.

## Validation record

- Dataset identity and version: Not applicable
- Calibration or independent validation: Not applicable
- Inclusion/exclusion and quality-control rules: Not applicable
- Metrics and uncertainty method: Not applicable
- Results and unresolved discrepancies: Arithmetic can be checked directly;
  model-equation usage is a separate verification item.
- Reproduction command and output: Not applicable

## Decision log

- Decision: Keep the stoichiometric coefficient explicit and cite its source.
- Rationale: The molecular-weight ratio is a chemical identity, not a
  site-specific measurement.
- Date: 2026-10-13
- Follow-up needed: Confirm the model paper uses this ratio in the same state
  equation and verify whether greater precision changes any material output.
