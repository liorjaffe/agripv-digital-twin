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
| Solar and tracker geometry | [`project/models/radiation.py`](../project/models/radiation.py) | pvlib methods are cross-referenced in PV-002–PV-008; site geometry remains provisional under SITE-002. |
| Light-unit conversions | [`project/models/conversions.py`](../project/models/conversions.py) | 4.57 PAR-band conversion is LIGHT-001; the fixed 0.45 PAR fraction is LIGHT-002. |
| Lettuce dry-biomass equations | [`project/models/lettuce.py`](../project/models/lettuce.py) | Coefficients link to VAN-001 and source-specific LETTUCE-001–005 entries; unresolved primary-source locations are marked. |
| Thermal development clock | [`project/models/lettuce_development.py`](../project/models/lettuce_development.py) | GDD-001 records the thesis evidence status; it does not calculate biomass. |
| Field-data ingestion and quality control | [`project/io/`](../project/io/) and [`project/qc/`](../project/qc/) | Preserve source measurements, report rejected/missing values, and distinguish estimated weather inputs. |
| Parameter calibration | [`project/validation/calibrate_lettuce.py`](../project/validation/calibrate_lettuce.py) | Requires timestamped observations; a fit is not independent validation. |
| Regression evidence | [`project/tests/`](../project/tests/) | Tests verify software behavior and equations, not empirical validity. |

## Stable reference register

Each entry follows [`REFERENCE_TEMPLATE.md`](./REFERENCE_TEMPLATE.md).
References document evidence status as well as positive support; an
“attributed-unverified” entry is not a verified parameter source.

| ID | Source or method | Code connection / role |
| --- | --- | --- |
| [SITE-001](./SITE-001.md) | Bed layout and planting-grid source | Bed footprint/grid; drawing version 05 |
| [SITE-002](./SITE-002.md) | PV geometry and optical assumptions | Tracker row geometry, axis, albedo, bifaciality; retained drawing is not to scale |
| [VAN-001](./VAN-001.md) | Van Henten (1994) lettuce model | Coefficient-by-coefficient primary-source reconciliation remains open |
| [LETTUCE-001](./LETTUCE-001.md) | Sweeney et al. (1981) attribution | `c_yf` |
| [LETTUCE-002](./LETTUCE-002.md) | van Holsteijn (1981) attribution | `c_gr_max` |
| [LETTUCE-003](./LETTUCE-003.md) | Lorenz and Wiebe (1980) attribution | Soil-origin `c_tau` attribution, `c_k`, `c_lar`; transfer unverified |
| [LETTUCE-004](./LETTUCE-004.md) | Goudriaan and Monteith (1990) attribution | Canopy light-interception equation |
| [LETTUCE-005](./LETTUCE-005.md) | Sakamoto and Suzuki (2015) | Derived hydroponic root-share proxy; current `c_tau = 0.14` |
| [CHEM-001](./CHEM-001.md) | IUPAC standard atomic weights | `c_ch2o = 30/44` stoichiometric ratio |
| [GDD-001](./GDD-001.md) | Silva (2022) UFSC thesis | ST/TC GDD values; thesis metadata/pages must be verified |
| [LIGHT-001](./LIGHT-001.md) | Plant Growth Chamber Handbook, chapter 1 | 4.57 µmol/J conversion within PAR spectral band |
| [LIGHT-002](./LIGHT-002.md) | Meek et al. (1984) PAR/global-solar study | Primary abstract supports a study-specific 0.45 estimate |
| [LIGHT-003](./LIGHT-003.md) | Pashiardis (2022) Cyprus PAR study | Candidate context for variability; exact ratios not verified |
| [LIGHT-004](./LIGHT-004.md) | Thimijan and Heins (1983) interconversion review | Candidate conversion reference; 4.57 table not verified |
| [DLI-001](./DLI-001.md) | Virginia Cooperative Extension SPES-720 | General lettuce DLI range attribution |
| [DLI-002](./DLI-002.md) | Michigan State Extension / Runkle attribution | Crop-type guidance; exact publication pending |
| [PV-001](./PV-001.md) | PVWatts V5 manual | DC temperature coefficient, generic loss factors, inverter |
| [PV-002](./PV-002.md) | pvlib-python implementation | Software/API version range; not an exact version pin |
| [PV-003](./PV-003.md) | Erbs et al. (1982) | GHI-to-DNI/DHI decomposition |
| [PV-004](./PV-004.md) | Ineichen and Perez (2002) | Clear-sky irradiance |
| [PV-005](./PV-005.md) | Hay and Davies (1980) attribution | Tilted-surface sky diffuse model |
| [PV-006](./PV-006.md) | Faiman (2008) | PV module temperature |
| [PV-007](./PV-007.md) | Mikofski et al. (2019) | Infinite-sheds bifacial irradiance |
| [PV-008](./PV-008.md) | Anderson and Mikofski (2020) | Single-axis tracker/backtracking |
| [CROP-001](./CROP-001.md) | Project crop-ground irradiance method | Formula, omitted terms, pending field validation |
| [CROP-002](./CROP-002.md) | Project biomass and temperature assumptions | Dry matter, initial state, synthetic seasonal curve |
| [CTRL-001](./CTRL-001.md) | Controller tuning and sensitivity design | Current defaults and reproducibility status of the reported trade-off |

## Unit conversions and open evidence

The light conversions used by the simulation are arithmetic assumptions:

| Conversion | Project value | Evidence status |
| --- | --- | --- |
| Global shortwave to PAR | `PAR_FRACTION = 0.45` | [LIGHT-002](./LIGHT-002.md): constant model assumption; primary evidence and expected site error remain unverified |
| PAR-band energy to PPFD | `4.57 µmol photons/m²/s` per `W/m² PAR` | [LIGHT-001](./LIGHT-001.md): conversion applies to PAR-band radiant energy, not total shortwave; handbook edition/page pending |
| Lettuce DLI target / bounds | target `14`, min `10`, max `18 mol/m²/day` | [DLI-001](./DLI-001.md) and [DLI-002](./DLI-002.md): general guidance attributed; no cultivar-specific justification for Crespa |
| GDD stage bases/requirements | ST: `4.1°C`, `398.67 GDD`; TC: `6.1°C`, `472.79 GDD` | [GDD-001](./GDD-001.md): thesis values attributed; PDF, page/table, and four-cycle mean claim need verification |

The following values are active inputs but are not substantiated by a source
in the repository:

| Input | Current value | Implementation | Evidence status / follow-up |
| --- | --- | --- | --- |
| Ground albedo | `0.18` | `pv.albedo` | SITE-002 assumption; obtain a site reflectance measurement |
| Module bifaciality | `0.7` | `pv.bifaciality` | SITE-002 gallery-pattern assumption; verify against module datasheet |
| Tracker pitch / row width / height | `12 m / 4.768 m / 2.6 m` | `pv.pitch_m`, `row_width_m`, `pv.height_m` | SITE-002 scenario values; the retained drawing is marked “sem escala” and has no dimension callouts for them |
| Ground coverage ratio | `0.3973` | `pv.gcr` | SITE-002 derived value, approximately `4.768 / 12`; inherits unresolved geometry |
| Optimizer weights | current defaults PV `1.0`; movement `0.0`; sweep includes PV `0.5/1.0`, movement `0/0.05` | `project/scenarios/run_timeseries.py`, `run_benchmark.py` | [CTRL-001](./CTRL-001.md): provisional objective settings. Previously reported `0.001/0.05` do not match current code; claimed PV −12% / DLI +10% trade not reproduced from a retained output |
| Initial lettuce state | Structural `8`, non-structural `3 g/m²` | `project/models/lettuce.py`, `simulate_growth_timeseries` | [CROP-002](./CROP-002.md): unmeasured scenario initialization; it is not a 30/70 structural/non-structural split |
| Fresh-mass conversion | dry-matter fraction `0.05` | `project/scenarios/crop_cycles.py` | [CROP-002](./CROP-002.md): unverified for curly/hydroponic lettuce |
| Crop-ground irradiance | `unshaded × DNI × cos(zenith) + view_factor × DHI` | `project/models/radiation.py` | [CROP-001](./CROP-001.md): project approximation; circumsolar and ground-reflected crop irradiance omitted; field validation pending |

Do not treat an incomplete citation as a verified source. Unverified values
remain explicitly marked in their entries. Sensor-channel identity and the
scope of the 8,000 W PV rating are separate open site-data questions; see
[`project/data/raw/README.md`](../project/data/raw/README.md) and
[PV-001](./PV-001.md).

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
