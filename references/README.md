# Research references and methods register

This folder is the project’s evidence base for reproducible methods and later
paper writing. Keep source documents unchanged in `field-layouts/` or
`literature/`; record how each source supports (or does not yet support) model
inputs and assumptions here. Do not describe a model assumption as a field
measurement or validation result.

## Site reference

### SITE-001 — Field beds and PV-system layout

- **Citation:**
  - **Authors / organization:** AgriPV project user; internal field-layout drawing for the AgriPV site.
  - **Year:** 2026.
  - **Full title:** *AgriPV – Planta de Identificação de Sistemas FV e Canteiros*.
  - **Journal / publisher / report:** Internal design drawing / project site layout document.
  - **Volume, issue, pages:** Not applicable; project drawing sheet, no journal citation.
  - **DOI or stable URL:** Not available.
  - **Local source file:** [`field-layouts/Id_canteiros_e_sistemas_fv_v5_260506.pdf`](./field-layouts/Id_canteiros_e_sistemas_fv_v5_260506.pdf)
  - **Access date:** not recorded; internal source provided by the project user.
- **Source file:** [`field-layouts/Id_canteiros_e_sistemas_fv_v5_260506.pdf`](./field-layouts/Id_canteiros_e_sistemas_fv_v5_260506.pdf)
- **Document title:** *AgriPV – Planta de Identificação de Sistemas FV e Canteiros*.
- **Document metadata:** title block shows date 20/02/2026 and version 05; the uploaded filename is retained as a normalized local filename.
- **Source provided:** project user. The 7.5 m × 1.5 m bed dimensions were supplied by the user; the diagram shows 24 numbered rows and four planting columns.
- **Field facts:** bed footprint 7.5 m × 1.5 m; planting grid 24 × 4; 96 plants per bed.
- **Derived geometry:** 11.25 m²/bed; 8.5333 plants/m².
- **Implemented configuration:** [`project/config/site.yaml`](../project/config/site.yaml), `cultivation` section.
- **Implementation/use:** [`project/config/__init__.py`](../project/config/__init__.py) validates the dimensions and exposes gross area, net area, and derived plant density. The standalone [`agripv_dashboard.html`](../agripv_dashboard.html) provides a net planted-area what-if control that scales bed/system conversions; it mirrors the YAML default and does not load the file.
- **Evidence status:** site-layout reference; it is not a crop-yield dataset and does not validate the growth model.
- **Open measurement note:** `net_planted_area_fraction` is currently set to `1.0`, so derived configuration and the dashboard default assume the full 7.5 m × 1.5 m footprint is net planted area. This is not a field measurement. The dashboard control is independent of the YAML value; update its mirrored default if the configured default changes.

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

### VAN-001 — Dynamic lettuce growth model

The citation metadata for E. J. Van Henten's 1994 lettuce-model validation
article is registered in [`VAN-001.md`](./VAN-001.md). It is model context,
not evidence that this repository's coefficients or initial state have been
validated. The coefficients in [`project/models/lettuce.py`](../project/models/lettuce.py)
still need a line-by-line reconciliation against the paper before being called
verified.

### GDD-001 — Hydroponic curly lettuce thermal development

[`GDD-001.md`](./GDD-001.md) records the Silva (2022) UFSC thesis attribution
and the GDD values used in
[`project/models/lettuce_development.py`](../project/models/lettuce_development.py).
The code source note identifies the author, title, and university, but the
thesis URL and supporting page/table have not been verified; the values remain
provisionally attributed rather than fully sourced.

### LIGHT-001 — PAR-to-PPFD conversion

[`LIGHT-001.md`](./LIGHT-001.md) records the Plant Growth Chamber Handbook
attribution for the approximate 4.57 conversion factor. The intended handbook
edition and page/table have not been supplied; the citation is explicitly
incomplete.

### DLI-001 — Lettuce light target

[`DLI-001.md`](./DLI-001.md) records the configured 14 mol/m²/day target and
the reported 12–17 guidance range. The exact Runkle / extension publication
and relevant table remain unidentified.

### PV-001 — PVWatts Version 5 system and inverter model

- **Citation:** Dobos, A. P. (2014). *PVWatts Version 5 Manual*. NREL/TP-6A20-62641. National Renewable Energy Laboratory. <https://pvwatts.nrel.gov/downloads/pvwattsv5.pdf>.
- **Supports:** PVWatts DC temperature coefficient range, aggregate standard system-loss factors, and the nominal-efficiency inverter model used by `pvlib`.
- **Implementation:** [`project/models/radiation.py`](../project/models/radiation.py), `pvwatts_power`; [`project/config/site.yaml`](../project/config/site.yaml).
- **Configured assumptions:** `gamma_pdc_per_c = -0.004 °C⁻¹`, aggregate standard PVWatts V5 system losses `14.0756606883%` (soiling 2%, shading 3%, snow 0%, mismatch 2%, wiring 2%, connections 0.5%, LID 1.5%, nameplate 1%, age 0%, availability 3%), and inverter nominal efficiency `0.96`. These are generic model defaults, not site measurements or module/inverter datasheet values.
- **Open scope item:** `pdc0_w = 8000 W` is used as both the DC array reference rating and inverter DC input limit. The repository does not establish whether this is one tracker row or the full `2A-2B-2C` subsystem; the resulting energy must be treated as conditional on that unverified scope.

## Unit conversions and open evidence

The light conversions used by the simulation are arithmetic assumptions:

| Conversion | Project value | Evidence status |
| --- | --- | --- |
| Shortwave energy to PAR | PAR fraction `0.45` | Common project assumption; exact source edition/page not recorded |
| PAR energy to PPFD | `4.57 µmol photons/m²/s` per `W/m² PAR` | The Plant Growth Chamber Handbook was identified as the intended reference, but its edition/page and exact table were not recorded |
| Lettuce DLI target | `14 mol/m²/day` (range listed as 12–17) | The reviewer identified Runkle/extension tables; exact publication/table remains unverified |
| GDD stage bases/requirements | ST: `4.1°C`, `398.67 GDD`; TC: `6.1°C`, `472.79 GDD` | Attributed to a 2022 UFSC thesis in `GDD-001`; source URL and page/table remain missing |

The following values are active inputs but are not substantiated by a source
in the repository:

| Input | Current value | Implementation | Evidence status / follow-up |
| --- | --- | --- | --- |
| Ground albedo | `0.18` | `pv.albedo` | Assumption; obtain a site surface measurement or documented source |
| Module bifaciality | `0.7` | `pv.bifaciality` | Assumption; verify against the module datasheet |
| Tracker pitch / row width / height | `12 m / 4.768 m / 2.6 m` | `pv.pitch_m`, `pv.row_width_m`, `pv.height_m` | Site geometry values; exact drawing callout and measurement status need a source citation |
| Ground coverage ratio | `0.3973` | `pv.gcr` | Derived from row width / pitch (`4.768 / 12`); inherits their unresolved provenance |
| Optimizer weights | PV `0.001`; movement `0.05` | `project/scenarios/run_timeseries.py` | Engineering heuristics; not calibrated or optimized against field outcomes |
| Initial lettuce state | Structural `8`, non-structural `3 g/m²` | `project/models/lettuce.py`, `simulate_growth_timeseries` | Uncalibrated scenario initialization; literature split and total have not been reconciled |

Do not treat an incomplete citation as a verified source. Keep these values
visible as assumptions until the exact source, location, units, and
adaptation are documented. Sensor-channel identity and the scope of the
8,000 W PV rating are separate open site-data questions; see
[`project/data/raw/README.md`](../project/data/raw/README.md) and `PV-001`.

## Biomass conversion table and worked example

The retained layout source supports 7.5 m × 1.5 m geometric beds and a 24-row
× 4-plant arrangement (96 plants). The `net_planted_area_fraction` is a
scenario assumption; at the default 1.0, `A_net = 11.25 m²`.

For a modeled final dry biomass `B` in g/m²:

| Quantity | Conversion |
| --- | --- |
| Total modeled dry biomass per bed | `B × A_net` g/bed |
| Area-average dry biomass per plant | `B × A_net / 96` g/plant |
| Dry biomass gain above the initial 11 g/m² state | `max(B − 11, 0)` g/m² |
| Fresh-mass equivalent per bed | `max(B − 11, 0) × A_net / f` g/bed |
| Fresh-mass equivalent per plant | `max(B − 11, 0) × A_net / (96 × f)` g/plant |

Here `f = 0.05` is an assumed dry-matter fraction, not a field measurement.
The conversion also assumes that all modeled dry-biomass gain is harvestable,
with no losses or unmarketable fraction.

For example, `B = 3,000 g/m²` gives `33,750 g/bed` and about `351.6 g/plant`
as area-average total dry biomass. Gain above the initial state is
`2,989 g/m²`; dividing by the assumed 5% dry-matter fraction yields
`672.5 kg/bed` fresh-mass equivalent. This large value is a unit conversion,
not a predicted or validated yield. It illustrates the sensitivity to the
assumed dry-matter fraction and 100% harvestability. Individual-plant
variation and marketable-head fraction are not modeled.

Let `A_net = 11.25 m² × net_planted_area_fraction`. The dashboard scales
area-based model output to this bed layout as follows:

```text
gross_bed_area_m2 = 7.5 m × 1.5 m = 11.25 m²
net_planted_area_m2 = gross_bed_area_m2 × net_planted_area_fraction
plants_per_bed = 24 rows × 4 plants/row = 96 plants
plant_density = 96 plants / net_planted_area_m2

dry_g_per_bed = dry_g_per_m2 × net_planted_area_m2
area_average_dry_g_per_plant = dry_g_per_bed / 96 plants
```

For an estimated fresh-mass equivalent, use **net modeled dry-biomass gain**
above the model's initial state and state the assumed dry-matter fraction `f`:

```text
net_dry_g_per_m2 = max(final_dry_g_per_m2 − 11 g/m², 0)
estimated_fresh_g_per_bed = net_dry_g_per_m2 × net_planted_area_m2 / f
estimated_fresh_g_per_plant = estimated_fresh_g_per_bed / 96 plants
```

At the current default fraction of `1.0`, `net_planted_area_m2` is 11.25 m²;
other fractions scale bed totals accordingly.

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
