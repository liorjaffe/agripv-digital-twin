# Research references and methods register

This folder is the project’s evidence base for reproducible methods and later
paper writing. Keep source documents unchanged in `field-layouts/` or
`literature/`; record how each source supports (or does not yet support) model
inputs and assumptions here. Do not describe a model assumption as a field
measurement or validation result.

## Site reference

### SITE-001 — Field beds and PV-system layout

- **Source file:** [`field-layouts/Id_canteiros_e_sistemas_fv_v5_260506.pdf`](./field-layouts/Id_canteiros_e_sistemas_fv_v5_260506.pdf)
- **Document title:** *AgriPV – Planta de Identificação de Sistemas FV e Canteiros*.
- **Document metadata:** title block shows date 20/02/2026 and version 05; the uploaded filename is retained as a normalized local filename.
- **Source provided:** project user. The 7.5 m × 1.5 m bed dimensions were supplied by the user; the diagram shows 24 numbered rows and four planting columns.
- **Field facts:** bed footprint 7.5 m × 1.5 m; planting grid 24 × 4; 96 plants per bed.
- **Derived geometry:** 11.25 m²/bed; 8.5333 plants/m².
- **Implemented configuration:** [`project/config/site.yaml`](../project/config/site.yaml), `cultivation` section.
- **Implementation/use:** [`project/config/__init__.py`](../project/config/__init__.py) validates the dimensions and exposes derived area and plant density; [`agripv_dashboard.html`](../agripv_dashboard.html) presents the reference-bed comparison.
- **Evidence status:** site-layout reference; it is not a crop-yield dataset and does not validate the growth model.
- **Open measurement note:** current area conversion uses the full stated footprint as planted area. Confirm or replace this with net planted area if paths, margins, or gaps are within the 7.5 m × 1.5 m dimensions.

## Methods and code map

| Research-method element | Current implementation | Interpretation / evidence boundary |
| --- | --- | --- |
| Site, PV and bed configuration | [`project/config/site.yaml`](../project/config/site.yaml) | Runtime geometry and settings; descriptions are not measurements unless supported by a cited field source. |
| Solar and tracker geometry | [`project/models/radiation.py`](../project/models/radiation.py) | Uses `pvlib`; tracker travel is constrained to the installed ±55°. |
| Light-unit conversions | [`project/models/conversions.py`](../project/models/conversions.py) | PAR/PPFD and DLI conversions; assumptions are documented in the root README. |
| Lettuce dry-biomass equations | [`project/models/lettuce.py`](../project/models/lettuce.py) | Van Henten-style model; parameter calibration and field validation are separate tasks. |
| Thermal development clock | [`project/models/lettuce_development.py`](../project/models/lettuce_development.py) | GDD stage timing; it does not calculate biomass. |
| Field-data ingestion and quality control | [`project/io/`](../project/io/) and [`project/qc/`](../project/qc/) | Preserve source measurements, report rejected/missing values, and distinguish estimated weather inputs. |
| Parameter calibration | [`project/validation/calibrate_lettuce.py`](../project/validation/calibrate_lettuce.py) | Requires timestamped observations; a fit is not independent validation. |
| Regression evidence | [`project/tests/`](../project/tests/) | Tests verify software behavior and equations, not empirical validity. |

The conversion from area-based model output to this bed layout is:

```text
bed_area_m2 = 7.5 m × 1.5 m = 11.25 m²
plants_per_bed = 24 rows × 4 plants/row = 96 plants
plant_density = 96 plants / 11.25 m² = 8.5333 plants/m²

dry_g_per_bed = dry_g_per_m2 × 11.25 m²
area_average_dry_g_per_plant = dry_g_per_m2 × 11.25 m² / 96 plants
```

For an estimated fresh-mass equivalent, use **net modeled dry-biomass gain**
above the model's initial state and state the assumed dry-matter fraction `f`:

```text
net_dry_g_per_m2 = max(final_dry_g_per_m2 − 11 g/m², 0)
estimated_fresh_g_per_bed = net_dry_g_per_m2 × 11.25 m² / f
estimated_fresh_g_per_plant = estimated_fresh_g_per_bed / 96 plants
```

The default `f = 0.05` is a dashboard scenario assumption, not a site
measurement. The calculation additionally assumes all modeled dry-matter gain
is harvestable crop with no losses. Do not report these fresh-mass equivalents
as predicted or validated yield without an appropriate harvest measurement
and calibration/validation protocol. The biomass model does not estimate a
marketable-head fraction or individual-plant variation.

## Add a literature or validation reference

Copy [`REFERENCE_TEMPLATE.md`](./REFERENCE_TEMPLATE.md), assign a stable ID,
and record:

1. **Full citation:** authors, year, title, journal/report, volume/pages, DOI or stable URL.
2. **Source type and scope:** peer-reviewed study, instrument documentation, field protocol, dataset, or other.
3. **What it supports:** exact equation, parameter, sensor mapping, site measurement, or validation observation; include page/table/figure/section.
4. **Units and transformations:** original units, conversions, filters, exclusions, and uncertainty.
5. **Code connection:** file and symbol implementing the method; cite the matching test where applicable.
6. **Evidence status:** measured site input, literature parameter, model assumption, calibration dataset, or independent validation dataset.
7. **Limitations and decisions:** differences in cultivar, climate, equipment, scale, and any adaptation made here.

Keep raw evidence immutable where practical; derive cleaned or analysis-ready
data into a separate, versioned location with a documented transformation.
Never replace the source or silently change a cited value. For each experiment,
record the code revision, configuration, input-data identity, software
environment, command, and output location so another researcher can recreate
the result.

## Paper-methods outline

Use this outline as a traceability checklist when preparing a manuscript:

- **Study system and site:** location, bed dimensions, plant arrangement, PV
  subsystem, instruments, and measurement periods; cite `SITE-001` and add
  instrument/protocol references.
- **Input data and quality control:** source files, timestamps/time zone,
  sensor mapping, rejected values, interpolation, and data-completeness rules.
- **Physical and crop models:** equations, parameter sources, units, boundary
  conditions, numerical integration, and assumptions.
- **Calibration and validation:** calibration data, independent validation
  data, metrics, uncertainty, and any unresolved gaps.
- **Scenarios and analysis:** configuration, candidate controls, comparison
  baselines, area/plant conversions, and statistical methods.
- **Reproducibility:** code revision, environment, exact commands, and
  generated data/report identifiers.

Do not mark an item validated merely because a unit test passes or a scenario
produces plausible-looking values.
