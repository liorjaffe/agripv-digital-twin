# AgriPV Digital Twin

An open, physically grounded model of an agrivoltaic lettuce-and-solar system
at the Fotovoltaica / UFSC pilot in Florianópolis, Brazil. This guide is the
starting point for researchers, students, and developers who are new to the
project.

The current reference plant is the **8 kWp subsystem 2A–2B–2C**: PV modules
cover beds 2A and 2C, with bed 2B between them. The software combines solar
and tracker geometry, crop-level light, PV output, and lettuce growth. It can
also turn weather data into *recommended* tracker positions. It does **not**
send commands to physical tracker hardware.

The installed tracker modules move between **−55° and +55°**. That mechanical
limit is applied to modeled tracker positions and absolute manual-command
validation.

## Start here

From the repository root:

```bash
# Create an environment and install the project dependencies.
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt

# Run the project tests.
PYTHONPATH=. .venv/bin/python -m pytest -q project/tests/

# Run the complete field-export example on bundled synthetic data.
PYTHONPATH=. .venv/bin/python project/scenarios/run_sample_field_export.py
```

The sample command prints sensor-quality reports, daily model results, and the
number of recommendations collected by a **dry-run** command sink. It does not
connect to a tracker, network service, or logger.

To explore without running Python, open [`agripv_dashboard.html`](./agripv_dashboard.html)
in a browser. To understand how the Python components fit together, start with
the [project map](#project-map), then follow one of the [data paths](#how-data-moves-through-the-model).

## What the model does

The project has three main kinds of work:

1. **Turn weather or station data into model inputs.** Read clean irradiance
   files, native multi-logger station exports, or the `Period_Components`
   research export. Check timestamps and sensor plausibility before using the
   measurements.
2. **Estimate coupled crop and PV outcomes.** Use `pvlib` for the sun path,
   tracker orientation, irradiance on crops and panels, and PV power. Use the
   Van Henten-style lettuce model for dry-biomass growth.
3. **Compare tracker positions and export results.** Select a tracker-angle
   recommendation against the crop-light target, with optional PV and movement
   penalties. Summarize the time series, or export tables and standalone
   visual reports.

The project deliberately distinguishes **measured inputs**, **estimated
weather**, and **modeled outcomes**. A graph or report may combine all three;
check its source and assumptions before treating a result as an observation.

## How data moves through the model

```text
Clean weather (GHI/DNI/DHI) ───────────────────────────────┐
                                                           │
Raw station export -> identify probes -> QC -> PPFD -> estimated GHI/DNI/DHI
                                                           │
Period_Components export -> measured irradiance + observed tracker angle
                                                           │
                                                           v
         timezone-aware weather -> solar/tracker geometry
                                  -> crop light and panel irradiance
                                  -> candidate PV power and crop PPFD
                                  -> tracker schedule + safety fallback
                                  -> DLI, biomass, and daily summaries
                                  -> reports / telemetry / dry-run commands
```

The three input routes are intentionally separate:

### 1. Already-clean weather

`process_weather_batch` accepts a time series with timezone-aware timestamps
and `ghi`, `dhi`, and `dni` columns. These are global, diffuse, and direct
horizontal irradiance in W/m². This route is for weather that has already been
mapped and quality-checked.

### 2. Raw multi-logger station export

`process_field_export` understands the station's Campbell Scientific-style
column names, such as `CR1Kx-TempMod1`, `CR310-04-Par`, and `CR310_01-Ws`.
Columns for the same logger and sensor role are grouped; redundant probes are
combined using their median. The raw-probe report is calculated before this
aggregation so an individual failed probe does not disappear behind healthy
neighbors.

Recognized readings are checked against broad physical bounds. Implausible
values are marked missing rather than clipped to plausible-looking numbers.
Short gaps can be interpolated, but long outages stay missing. At the default
15-minute interval, the cleaner bridges at most four consecutive samples
(one hour).

The station has quantum PAR/PPFD sensors but **no pyranometer**. For this
route, PPFD is used to estimate GHI from an Ineichen clear-sky reference and a
clear-sky index; Erbs decomposition then estimates DNI and DHI. These are
**estimates, not irradiance measurements**. A PPFD-derived diffuse/direct
split cannot reproduce every cloud geometry. Validate it against a
pyranometer or trusted field reference before using results for operational
decisions.

### 3. `Period_Components` research export

`project/data/raw/Period_Components.csv` contains GHI, DNI, DHI, and observed
tracker-angle data used by the report-generation scenarios. The parser also
retains other exported channels, but names such as `0A`–`5F` are not generally
assigned physical sensor roles by the ingestion layer without supporting
metadata. A specialized timeline-export scenario groups selected channels
for a comparison; treat those labels and the resulting crop comparisons as
scenario assumptions, not as universally established sensor mappings.

## The science, in plain language

### Solar radiation and tracker geometry

[`project/models/radiation.py`](./project/models/radiation.py) wraps `pvlib`
for solar position, single-axis tracker geometry and backtracking, irradiance
on the ground and modules, and DC power. The ground-light calculation uses
the infinite-sheds geometry; the panel calculation uses a bifacial model.
Measured module temperature can be used directly for PV power. Otherwise,
cell temperature is estimated with the Faiman model using air temperature
and wind speed when available.

### Light units and daily light integral

[`project/models/conversions.py`](./project/models/conversions.py) keeps
commonly confused light quantities explicit:

| Quantity | Meaning | Project unit |
| --- | --- | --- |
| GHI | Total shortwave sunlight on a horizontal surface | W/m² |
| PAR | Approximate photosynthetically active part of that energy | W/m² |
| PPFD | Instantaneous photosynthetic photon flux | µmol photons/m²/s |
| DLI | PPFD accumulated over a day | mol photons/m²/day |

The conversion uses a PAR fraction of **0.45** and an approximate conversion
of **4.57 µmol/m²/s per W/m² of PAR**. DLI from a time series integrates the
actual elapsed time between samples rather than assuming a fixed number of
samples per day. Missing PPFD samples are treated as zero by that integration;
this can undercount DLI on days with missing daytime data. The pipeline's
`input_data_complete_fraction` is the fraction of input GHI samples present
before resampling and interpolation. It does not measure PPFD completeness or
the completeness of every weather variable, so use it as a GHI availability
indicator rather than a general validation score.

### Lettuce growth and development

The project has two different lettuce models; they answer different questions:

- [`project/models/lettuce.py`](./project/models/lettuce.py) is the
  Van Henten-style biomass model. Its state tracks structural and
  non-structural dry biomass. Photosynthesis, respiration, growth, and
  temperature responses determine how those stores change over time.
- [`project/models/lettuce_development.py`](./project/models/lettuce_development.py)
  is a thermal-time clock. It accumulates growing degree days (GDD) to track
  sowing-to-transplant and transplant-to-harvest stages. It does not calculate
  biomass and does not account for light or humidity.

The two models are not interchangeable, and a predicted biomass or GDD-based
harvest date is not a measured crop yield. Calibration and field validation
need appropriate biomass and sensor observations; when those are missing, the
validation code reports that explicitly instead of fabricating a fit.

### Field bed geometry and biomass units

The project’s bed dimensions are **7.5 m × 1.5 m**, as supplied by the
project user; the retained field-layout diagram shows the **24-row × 4-column**
planting grid, or **96 plants per bed**. The resulting geometric area is
**11.25 m² per bed**, and the implied density is **96 / 11.25 = 8.53
plants/m²**. These values are held in [`project/config/site.yaml`](./project/config/site.yaml)
under `cultivation`. The configurable net planted-area fraction defaults to
`1.0`, which assumes the full footprint is planted.

The lettuce model reports **modeled dry biomass per ground area** in g/m².
For net planted area `A_net = 11.25 × net_planted_area_fraction` m², the
following conversions are arithmetic scaling only; they do not mean that all
modeled biomass is edible or harvestable. For a reported value `B`:

| Quantity | Conversion for this field layout |
| --- | --- |
| Total modeled dry biomass per bed | `B × A_net` g/bed |
| Total modeled dry biomass per plant (area-average equivalent) | `B × A_net / 96` g/plant |
| New dry biomass since the model's 11 g/m² initial state | `max(B − 11, 0)` g/m² |
| Estimated fresh mass per bed | `max(B − 11, 0) × A_net / f` g/bed |
| Estimated fresh mass per plant | `max(B − 11, 0) × A_net / (96 × f)` g/plant |

Here `f` is the dry-matter fraction of fresh mass. The dashboard's default
`f = 0.05` (5%) is an **assumption**, not a measured site value. The
conversion additionally assumes **all modeled dry-biomass gain is harvestable
fresh crop**, with no losses or unmarketable fraction. The initial 11 g/m² is
the model's starting state, not new harvest growth, and is excluded from this
illustrative conversion. For example, **3,000 g/m²** total dry biomass corresponds to
**33,750 g/bed** and **351.6 g/plant** as area-average total dry biomass. Its
net growth above the initial state is **2,989 g/m²**; at the assumed 5% dry
matter this implies **672.5 kg/bed** fresh-mass equivalent. That large value
is a mathematical unit conversion, **not a predicted or validated lettuce
yield**. It illustrates the sensitivity to the 5% dry-matter and 100%
harvestability assumptions (about **7.0 kg/plant** under the same assumptions).
The model does not predict individual-plant variation or marketable-head
fraction and has not been calibrated against these site harvest weights.

The dashboard's net-planted-area control scales bed and system totals and
derives the reference density as `96 / A_net`; it does not change modeled
biomass per m² or the 96-plant count. Its plant-density control is a separate
**what-if conversion** for the per-plant estimate in the growth-cycle readout.
The economics area control remains a user-selected scenario area, not an
assertion about the physical reference-bed size.

The Python configuration exposes `cultivation.net_planted_area_fraction` as
derived net planted area and plant density. The standalone browser dashboard
does not load the YAML; its net-area control starts at the mirrored default
`1.0` and can be adjusted independently. If the configured default changes,
update the dashboard's mirrored cultivation default as well. Neither value is
a field measurement until net planted area is measured on site.
The PDF source and the project’s evidence/methods register are in
[`references/`](./references/README.md).

### Tracker recommendations

[`project/scenarios/run_timeseries.py`](./project/scenarios/run_timeseries.py)
evaluates a set of offsets from the sun-following tracker position. At each
time step, it scores candidates using a light-deficit-first objective plus PV
and movement penalties:

```text
light score:
  below target: target PPFD − crop PPFD
  at or above target: −crop PPFD / target PPFD
  at night (zero target): −crop PPFD
+ PV-power loss penalty (relative to the best candidate at that time)
+ movement penalty
```

The instantaneous light target is derived separately for each date by dividing
the configured DLI target by the daylight duration represented in that date's
samples, using apparent solar zenith below 90° to identify daylight. It is set
to zero at night. Below the target, candidates that reduce the deficit score
better; at or above it, candidates providing more crop PPFD score better. The
reported daily DLI is integrated from the selected crop PPFD time series; it
is not the same thing as that instantaneous target. Candidate offsets are
applied to the signed tracker rotation and limited to the installed ±55°
travel; module-facing geometry is then recalculated from that rotation. Wind
stow can replace a selected position with the configured fallback.

These are model recommendations, not actuator commands. The available
`DryRunCommandSink` and `JsonlCommandSink` only collect or record messages.
There is no physical hardware adapter, commissioning procedure, or
site-approved interlock in this repository.

## Project map

| Path | Purpose |
| --- | --- |
| `project/models/` | Radiation, unit conversions, and the two lettuce models |
| `project/control/` | Candidate tracker-angle optimization and safety fallback |
| `project/io/` | Input parsing, station mapping, orchestration, and telemetry/command outputs |
| `project/qc/` | Sensor-role definitions, physical limits, rejection, gap handling, and quality reports |
| `project/validation/` | Radiation validation and lettuce-parameter calibration |
| `project/scenarios/` | Runnable pipelines and report/export entry points |
| `project/config/site.yaml` | Site and model settings used by the Python pipeline |
| `references/` | Field-layout source document, evidence register, and methods/code traceability |
| `project/data/raw/` | Bundled inputs, including the synthetic station example |
| `project/data/crop_targets/` | Crop target reference data |
| `project/tests/` | Regression tests for conversions, ingestion, validation, and GDD development |
| `agripv_dashboard.html` | Browser-based parameter sandbox |
| `standalone/` | Generated or self-contained HTML/data visualizations |
| `public/` | Static-site assets and published data |
| `scripts/` | Static-site build and public-data export helpers |
| `Agrivoltaic system modeling.py` | Older, standalone exploration; not the canonical pipeline |

The main Python flow is `project.io.service` → `project.scenarios.run_timeseries`
→ `project.models` and `project.control` → daily/telemetry/command outputs.
The `service` functions are the convenient boundaries for applications;
the model and control modules contain the reusable calculations.

## Running the main workflows

### Process the bundled raw station example

```bash
PYTHONPATH=. .venv/bin/python project/scenarios/run_sample_field_export.py
```

The bundled `station_export.csv` is **synthetic**. It imitates the station's
column naming and representative sensor faults for a repeatable end-to-end
example; it is not raw field evidence.

### Generate the model explorer

```bash
PYTHONPATH=. .venv/bin/python project/scenarios/generate_model_explorer.py
```

This uses the `Period_Components` irradiance export and writes
`standalone/lettuce-pv-model-report.html` by default.

### Generate the simpler report

```bash
PYTHONPATH=. .venv/bin/python project/scenarios/generate_simple_report.py
```

This writes a separate report, `standalone/lettuce-pv-summary-report.html`,
by default. Both report commands accept `--input` and `--output` paths. Keeping
their default destinations distinct prevents one report from silently
replacing the other.

### Generate the simulation timeline

```bash
PYTHONPATH=. .venv/bin/python project/scenarios/export_model_timeline.py
```

This writes `standalone/our_simulations_timeline.json` and
`standalone/our_simulations_timeline.html`. The timeline is a standalone
visualization generated from the research export and scenario assumptions;
it is not the same interface as `agripv_dashboard.html`.

### Build the static-site copy

```bash
sh scripts/build-pages.sh
```

This copies the dashboard and static assets into the generated `public-site/`
directory. That directory is build output and is ignored by Git.

## Configuration

[`project/config/site.yaml`](./project/config/site.yaml) is the source for the
runtime site location, PV geometry and ratings, crop-light target, and tracker
movement/wind-stow settings. The Python pipeline loads those settings through
`project.config`. Runtime values should be changed there rather than copied
into individual scenario scripts.

The same YAML also contains descriptive site/crop fields that are not yet
inputs to every model (for example, bed labels and some crop thresholds).
Changing a reference field does not make an unimplemented process part of the
simulation. Check the call path and tests before treating a setting as active.

## Data quality and limits to keep in mind

- All model timestamps must be timezone-aware. Naive input timestamps are
  interpreted in the configured site timezone by the ingestion helpers.
- Quality-control bounds are broad plausibility checks, not sensor calibration.
  Rejected values become missing; they are not evidence of what the true value
  was.
- Interpolation is limited to short internal gaps. Long outages remain missing.
  Daily output includes `input_data_complete_fraction`, computed from
  non-missing GHI samples before resampling and interpolation. It does not
  summarize DHI, DNI, or other weather-variable completeness; remaining missing
  PPFD contributes zero to integrated DLI and can make incomplete days appear
  lower.
- The crop model's dry biomass is modeled state. Any conversion to fresh mass
  or assumptions about crop cycles in a report are additional assumptions and
  should be checked in that report's generator.
- The project is not a substitute for field validation, agronomic advice, or
  hardware safety review.

## Tests and making changes

Run all project tests with:

```bash
PYTHONPATH=. .venv/bin/python -m pytest -q project/tests/
```

When changing a formula, sensor mapping, unit, configuration setting, or
control rule:

1. State the input/output units and the physical assumption.
2. Add or update a focused test with a measurable expected result.
3. Keep estimated and measured values distinguishable in names and reports.
4. Run the focused test, then the full project suite if the shared pipeline is
   affected.
5. Update this guide if an input, command, output location, or modeling
   boundary changes.

For details on the Python contracts and supported input shapes, see
[`project/README.md`](./project/README.md).
