# SITE-002 — PV geometry and optical assumptions

## Citation

- Authors / organization: AgriPV project; internal design drawing supplied by
  the project owner
- Year: 2026
- Full title: *AgriPV – Planta de Identificação de Sistemas FV e Canteiros*
- Journal / publisher / report: Internal site-layout drawing, version 05
- Volume, issue, pages: One sheet; explicitly marked “sem escala”
- DOI or stable URL: Not available
- Local source file (if retained): [`field-layouts/Id_canteiros_e_sistemas_fv_v5_260506.pdf`](./field-layouts/Id_canteiros_e_sistemas_fv_v5_260506.pdf)
- Access date: 2026-10-13

## Source and scope

- Source type: Internal site-layout drawing and project scenario metadata
- Site, cultivar, equipment, and study scale: UFSC AgriPV site; drawing labels
  beds and system types, but is not a dimensioned engineering drawing.
- What was measured or derived: Candidate tracker geometry and optical
  parameters currently used by the radiation/PV simulation.
- Relevant page, table, figure, or dataset fields: Single drawing sheet;
  title block reports 20/02/2026, version 05, scale “sem escala.” The image
  shows a north arrow and bed/system layout but no verified dimensions for
  tracker pitch, row width, height, tilt stops, module bifaciality, or albedo.

## Evidence extracted

| Claim or value | Source location | Original unit | Normalized value/unit | Uncertainty / qualification |
| --- | --- | --- | --- | --- |
| Tracker pitch | Site YAML `pv.pitch_m` | m | 12.0 m | Scenario value; not dimensioned in retained drawing |
| Row width | `descriptive_metadata.pv.row_width_m` | m | 4.768 m | Scenario value; source drawing has no verified callout |
| Tracker height | `pv.height_m` | m | 2.6 m | Scenario value; drawing does not dimension it |
| Axis azimuth | `pv.axis_azimuth_deg` | degrees east of north | 0° (interpreted as north–south) | Direction inferred from scenario/drawing orientation; no survey or tracker datasheet verified |
| Maximum tilt | `pv.max_tilt_deg` | degrees | 55° | Configuration value; controller/manufacturer specification not retained |
| Ground albedo | `pv.albedo` | Unitless | 0.18 | Assumption; no ground reflectance measurement |
| Module bifaciality | `pv.bifaciality` | Unitless | 0.7 | Gallery-pattern assumption; not verified against a module datasheet |
| Ground coverage ratio | `pv.gcr` | Unitless | 0.3973 | Derived approximately as 4.768/12; inherits unresolved width and pitch |

## Connection to this project

- Reference ID and evidence role: SITE-002; site-layout reference plus
  unverified scenario inputs, not a source for the numerical PV geometry
- Code file and symbol: [`project/config/site.yaml`](../project/config/site.yaml),
  `pv` keys; [`project/models/radiation.py`](../project/models/radiation.py),
  `tracker_orientation`, `crop_and_pv_irradiance`
- Configuration key(s): `pv.pitch_m`, `pv.height_m`, `pv.axis_azimuth_deg`,
  `pv.max_tilt_deg`, `pv.bifaciality`, `pv.albedo`, `pv.gcr`
- Related test(s): [`project/tests/test_configuration.py`](../project/tests/test_configuration.py),
  [`project/tests/test_optimizer.py`](../project/tests/test_optimizer.py)
- Adaptation made for this project: `gcr` is calculated from the configured
  row width and pitch.
- Known differences or limitations: The drawing is not to scale. It cannot
  substantiate the listed tracker dimensions or material properties.

## Validation record

- Dataset identity and version: Drawing v05, dated 20/02/2026
- Calibration or independent validation: Not applicable
- Inclusion/exclusion and quality-control rules: Not applicable
- Metrics and uncertainty method: Not applicable
- Results and unresolved discrepancies: No dimensions or module datasheet
  callouts supporting the numerical row geometry, bifaciality, or albedo were
  found on the retained sheet.
- Reproduction command and output: Not applicable

## Decision log

- Decision: Keep the values labeled as scenario assumptions; do not attribute
  them to the field drawing as measured or dimensioned facts.
- Rationale: Visual inspection of the retained one-sheet drawing confirms that
  it is marked not to scale and contains no applicable dimension callouts.
- Date: 2026-10-13
- Follow-up needed: Obtain a dimensioned tracker/site drawing, module
  datasheet, tracker controller specification, and local surface-albedo
  measurement; then update the YAML and this record.
