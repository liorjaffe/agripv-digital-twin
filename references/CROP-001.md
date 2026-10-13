# CROP-001 — Project crop-ground irradiance approximation

## Citation

- Authors / organization: AgriPV Digital Twin Prototype project
- Year: 2026
- Full title: Crop-ground irradiance approximation used by the prototype
- Journal / publisher / report: Project method note
- Volume, issue, pages: Not applicable
- DOI or stable URL: Not applicable
- Local source file (if retained): [`project/models/radiation.py`](../project/models/radiation.py)
- Access date: 2026-10-13

## Source and scope

- Source type: Project-specific model approximation
- Site, cultivar, equipment, and study scale: One idealized tracker row-to-row
  ground cross-section; site-scale validation is pending
- What was measured or derived: Crop-ground GHI is approximated as
  `unshaded_ground_fraction × DNI × cos(zenith) + vf_ground_sky_2d_integ × DHI`.
- Relevant page, table, figure, equation, or dataset fields: Code equation in
  `crop_and_pv_irradiance`, `project/models/radiation.py`.

## Evidence extracted

| Claim or value | Source location | Original unit | Normalized value/unit | Uncertainty / qualification |
| --- | --- | --- | --- | --- |
| Direct-beam ground contribution | `crop_and_pv_irradiance`, `crop_ghi` assignment | W/m² | `unshaded × DNI × max(cos(zenith), 0)` | Geometric project approximation; exact ground position is represented by an average unshaded fraction |
| Diffuse-sky ground contribution | Same equation | W/m² | `vf_ground_sky_2d_integ × DHI` | Assumes the integrated view factor is adequate for the crop location |
| Total modeled crop-ground irradiance | Same equation | W/m² | Sum of the two contributions | Circumsolar diffuse is ignored; ground-reflected irradiance is not added to the crop term, although albedo is used in the PV rear-side model |

## Connection to this project

- Reference ID and evidence role: CROP-001; internal model formulation, not an
  external citation or measured result
- Code file and symbol: [`project/models/radiation.py`](../project/models/radiation.py),
  `crop_and_pv_irradiance`
- Configuration key(s): `pv.gcr`, `pv.height_m`, `pv.pitch_m`, `pv.albedo`
- Related test(s): [`project/tests/test_radiation.py`](../project/tests/test_radiation.py)
- Adaptation made for this project: Converts the resulting crop-ground
  shortwave estimate to PAR/PPFD using LIGHT-002 and LIGHT-001.
- Known differences or limitations: Circumsolar diffuse and ground-reflected
  crop irradiance are omitted. The formula is not validated against known
  bed-level irradiance measurements.

## Validation record

- Dataset identity and version: No verified site channel map or bed sensor data
- Calibration or independent validation: Pending; not performed
- Inclusion/exclusion and quality-control rules: Not applicable
- Metrics and uncertainty method: Not applicable
- Results and unresolved discrepancies: Site-channel type, unit, position, and
  calibration are not established, so comparisons cannot yet validate this
  approximation.
- Reproduction command and output: Covered by the radiation test suite; tests
  verify code behavior, not physical accuracy.

## Decision log

- Decision: Register this as a project approximation and do not present the
  equation as an established citation-based crop-light model.
- Rationale: The equation combines pvlib view/shading geometry with a
  project-selected ground-light expression.
- Date: 2026-10-13
- Follow-up needed: Obtain an authoritative channel map and calibrated
  bed-level PPFD measurements; then test the omitted diffuse/reflected terms
  and quantify model bias before using the output for calibration.
