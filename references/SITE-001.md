# SITE-001 — Bed footprint and planting-grid layout

## Citation

- Authors / organization: AgriPV project owner; internal field-layout drawing
- Year: 2026
- Full title: *AgriPV – Planta de Identificação de Sistemas FV e Canteiros*
- Journal / publisher / report: Internal field-layout drawing, version 05
- Volume, issue, pages: One sheet; no scale
- DOI or stable URL: Not available
- Local source file (if retained): [`field-layouts/Id_canteiros_e_sistemas_fv_v5_260506.pdf`](./field-layouts/Id_canteiros_e_sistemas_fv_v5_260506.pdf)
- Access date: 2026-10-13

## Source and scope

- Source type: Internal site-layout drawing plus site dimensions supplied by
  the project owner
- Site, cultivar, equipment, and study scale: UFSC AgriPV field beds
- What was measured or derived: Bed footprint, planting grid, area, and
  plant count per bed.
- Relevant page, table, figure, or equation, or dataset fields: Single
  drawing sheet; diagram identifies 24 planting rows and four columns. Bed
  dimensions 7.5 m × 1.5 m were supplied by the project owner; the drawing is
  marked “sem escala.”

## Evidence extracted

| Claim or value | Source location | Original unit | Normalized value/unit | Uncertainty / qualification |
| --- | --- | --- | --- | --- |
| Bed footprint | Owner-provided site dimensions; not dimensioned on drawing | m | 7.5 × 1.5 m = 11.25 m² | Owner-provided geometry, not independently surveyed in the retained drawing |
| Planting grid | Drawing sheet | rows × columns | 24 × 4 = 96 plants/bed | Diagram identifies layout; plant occupancy/establishment is not measured |
| Derived density at full footprint | Arithmetic from above | plants/m² | 96 / 11.25 = 8.5333 plants/m² | Assumes full bed footprint is net planted area |

## Connection to this project

- Reference ID and evidence role: SITE-001; site-layout reference, not a
  crop-yield dataset
- Code file and symbol: [`project/config/site.yaml`](../project/config/site.yaml),
  `cultivation`; [`project/config/__init__.py`](../project/config/__init__.py),
  derived bed area and plant density
- Configuration key(s): `cultivation.bed_length_m`, `bed_width_m`,
  `rows_per_bed`, `plants_per_row`, `net_planted_area_fraction`
- Related test(s): [`project/tests/test_configuration.py`](../project/tests/test_configuration.py)
- Adaptation made for this project: Plant density and bed-area totals are
  derived from supplied dimensions and the diagrammed grid.
- Known differences or limitations: `net_planted_area_fraction = 1.0` is a
  scenario assumption. Drawing scale cannot establish bed dimensions.

## Validation record

- Dataset identity and version: Drawing v05, dated 20/02/2026
- Calibration or independent validation: Not applicable
- Inclusion/exclusion and quality-control rules: Not applicable
- Metrics and uncertainty method: Not applicable
- Results and unresolved discrepancies: No as-built survey or net-area
  measurement is retained.
- Reproduction command and output: Arithmetic shown above

## Decision log

- Decision: Attribute the planting grid to the layout and bed dimensions to
  the project owner; keep full net planting area explicitly assumed.
- Rationale: The document identifies beds and planting rows but is not a
  dimensioned survey.
- Date: 2026-10-13
- Follow-up needed: Survey bed dimensions and net planted margins, then
  update `net_planted_area_fraction` using measured bed use.
