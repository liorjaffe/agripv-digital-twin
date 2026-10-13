# AgriPV Digital Twin Prototype

A research-oriented model of an agrivoltaic lettuce-and-solar system at the
Fotovoltaica / UFSC pilot in Florianópolis, Brazil. This guide is the starting
point for researchers, students, and developers who are new to the project.

The project describes its reference configuration as an **8 kWp subsystem
2A–2B–2C**: PV modules cover beds 2A and 2C, with bed 2B between them. The
model's use of `pdc0_w = 8000` for that whole subsystem versus one tracker row
is unverified, so PV energy is conditional on that scope. The software
combines solar and tracker geometry, crop-level light, PV output, and lettuce
growth. It can also turn weather data into *recommended* tracker positions.
It does **not** send commands to physical tracker hardware.

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

To build and explore the browser dashboard, run `sh scripts/build-pages.sh`
and open `public-site/index.html` in a browser. To understand how the Python
components fit together, start with the [project map](#project-map), then
follow one of the [data paths](#how-data-moves-through-the-model).

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
See the [raw-data dictionary](./project/data/raw/README.md) for documented
gaps in instrument identity, units, averaging, and tracker-angle convention.

## The science, in plain language

### Solar radiation and tracker geometry

[`project/models/radiation.py`](./project/models/radiation.py) wraps `pvlib`
for solar position, single-axis tracker geometry and backtracking, irradiance
on the ground and modules, and AC power after the configured PVWatts losses
and inverter model. The ground-light calculation uses
the infinite-sheds geometry; the panel calculation uses a bifacial model.
Measured module temperature can be used directly for PV power. Otherwise,
cell temperature is estimated with the Faiman model using air temperature
and wind speed when available.

### Units and geometry glossary

[`project/models/conversions.py`](./project/models/conversions.py) keeps
commonly confused light quantities explicit:

| Quantity | Meaning | Project unit |
| --- | --- | --- |
| GHI | Total shortwave sunlight on a horizontal surface | W/m² |
| PAR | Approximate photosynthetically active part of that energy | W/m² |
| PPFD | Instantaneous photosynthetic photon flux | µmol photons/m²/s |
| DLI | PPFD accumulated over a day | mol photons/m²/day |

The pipeline assumes a fixed PAR fraction of **0.45** and an approximate
conversion of **4.57 µmol/m²/s per W/m² of PAR**. Both are scenario
conversions, not site-specific sensor calibration; see
[`LIGHT-002`](./references/LIGHT-002.md) and
[`LIGHT-001`](./references/LIGHT-001.md). The fixed fraction omits spectral
variation with sky and atmospheric conditions. DLI and PV energy are trapezoidally
integrated across adjacent finite samples; missing intervals are not filled
with zero, and daily metrics are withheld below 80% pre-interpolation daylight
coverage. See the [references and methods register](./references/README.md)
for the conversion assumptions and a worked biomass-units example.

**Tracker angles:** an *offset* is relative to the sun-following baseline. An
*absolute tracker angle* is the mechanical rotation. Wind stow uses an absolute
angle; the configured value is an unverified scenario pending manufacturer
confirmation.

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
harvest date is not a measured crop yield. On the bundled field dataset, the
biomass model uses its configured 26°C air-temperature fallback; report
crop-cycle/harvest markers use a separate illustrative seasonal-temperature
curve. Both are scenario outputs, not temperature-informed site predictions.
Calibration and field validation
need appropriate biomass and sensor observations; when those are missing, the
validation code reports that explicitly instead of fabricating a fit.

### Bed geometry and biomass units

The internal layout drawing supports 7.5 m × 1.5 m beds and a 24 × 4 planting
grid. The resulting 11.25 m² and 96 plants are layout-derived, not net planted
area or yield measurements. The initial modeled biomass state (11 g/m²), 5%
fresh-mass dry-matter fraction, and all-harvestable assumption are scenario
values. Conversion equations and a worked example are in the
[references and methods register](./references/README.md).

### Tracker recommendations

[`project/scenarios/run_timeseries.py`](./project/scenarios/run_timeseries.py)
evaluates a set of offsets from the sun-following tracker position. At each
time step, it uses accumulated daily DLI and remaining daylight to compute a
target-to-maximum PPFD band, then prioritizes light-band compliance and uses
normalized PV and movement preferences to choose among equally compliant
candidates:

```text
light score:
  below the remaining-light target: target PPFD − crop PPFD
  above the remaining-light ceiling: crop PPFD − ceiling PPFD
  inside the band: 0
+ dimensionless PV-power loss preference (loss divided by best candidate power)
+ dimensionless movement preference (movement divided by the allowed move)
```

The daily bounds come from the configured DLI target and maximum, updating as
light accumulates and the day's remaining daylight changes. Candidate offsets
are evaluated at reachable increments so the per-step movement limit does not
make every non-zero move impossible. Offsets are applied to signed tracker
rotation and limited to installed ±55° travel. On wind-stow threshold, the
controller instead commands the configured **absolute tracker rotation**
(`wind_stow_tracker_theta_deg`, currently 0°), not an offset from sun-following.
That park-angle assumption has not been confirmed against a manufacturer
specification and must be verified before connecting any hardware. The reported
daily DLI is computed from the selected crop PPFD series; it can exceed the
maximum where no evaluated tracker position can shade enough light. When the
lowest-light candidate envelope already exceeds the configured DLI ceiling,
the controller disables that unreachable ceiling and prioritizes the
remaining minimum-light target; among equally acceptable candidates, its
normalized secondary preferences trade PV output against movement. Daily
reports show the modeled candidate DLI range and whether the configured target
band intersects that range. This per-timestep candidate envelope is an ideal
model bound: it does not enforce movement or wind-stow constraints, so it is
not proof that a complete physical schedule can attain the band. The DLI values
and band remain provisional until the site channel map and sensor units support
light-model calibration. The available export cannot yet distinguish a
site-specific DLI target/ceiling that is inappropriate for this system from a
crop-light model that overpredicts ground PPFD: the comparison channels have
unverified sensor types and units. Obtain the channel map before interpreting
the positive exploratory model-to-channel bias as calibration evidence or
changing the 14/18 mol/m²/day target/ceiling.
When a wind channel is present, only gaps up to `max_gap_periods` are
interpolated; a longer unresolved gap is treated as unknown wind and triggers
the configured absolute stow angle. This is a conservative model fallback,
not a commissioned hardware-safety function.
Daily DLI and PV energy use trapezoidal integration over finite adjacent
samples. The pipeline reports pre-interpolation daylight source coverage and
suppresses those daily metrics below 80% coverage rather than treating missing
intervals as zero. `pv_power_w` is now modeled AC output after the generic
PVWatts V5 loss-factor defaults (14.0757%) and 96% nominal inverter efficiency.
The `pdc0_w = 8000 W` rating scope (single tracker row versus the full
2A-2B-2C subsystem) is not documented by the field data, so PV energy remains
conditional on this unverified system scope. `gamma_pdc = -0.004 °C⁻¹` is a
generic PVWatts coefficient, not a value from a module datasheet; see
[`PV-001`](./references/PV-001.md).

These are model recommendations, not actuator commands. The available
`DryRunCommandSink` and `JsonlCommandSink` only collect or record messages.
There is no physical hardware adapter, commissioning procedure, or
site-approved interlock in this repository.

## Project map

| Path | Purpose | Representative tests |
| --- | --- | --- |
| `project/models/` | Radiation, unit conversions, and the two lettuce models | `test_conversions.py`, `test_validation.py` |
| `project/control/` | Candidate tracker-angle optimization and safety fallback | `test_optimizer.py` |
| `project/io/` | Input parsing, station mapping, orchestration, and telemetry/command outputs | `test_field_ingestion.py`, `test_commands.py`, `test_grafana.py` |
| `project/qc/` | Sensor-role definitions, physical limits, rejection, gap handling, and quality reports | `test_field_ingestion.py` |
| `project/validation/` | Radiation validation and lettuce-parameter calibration | `test_validation.py`, `test_report_validation.py` |
| `project/scenarios/` | Runnable pipelines and report/export entry points | `test_benchmark.py`, `test_crop_cycles.py`, `test_timeline_export.py` |
| `project/config/site.yaml` | Site and model settings used by the Python pipeline | `test_configuration.py` |
| `references/` | Field-layout source document, evidence register, and methods/code traceability | — |
| `project/data/raw/` | Bundled inputs, including the synthetic station example | `test_field_ingestion.py`, `test_public_export.py` |
| `project/data/crop_targets/` | Crop target reference data | `test_lettuce_development.py` |
| `project/tests/` | Project regression suite | all files under this path |
| `agripv_dashboard.html` | Browser-based parameter sandbox | manual/browser checks |
| `standalone/` | Viewer source template; generated reports are release artifacts | `test_timeline_export.py` |
| `public/` | Static-site source assets; generated data is rebuilt from tracked input | `test_public_export.py` |
| `scripts/` | Static-site build and public-data export helpers | `test_public_export.py` |
| `archive/legacy/` | Superseded exploration scripts; not part of the canonical pipeline | — |

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
`standalone/our_simulations_timeline.html` from the tracked
`standalone/timeline_viewer.html` source template. The generated timeline
contains an in-report synthetic-inputs warning and is a release artifact, not
a checked-in source file.

Pushing a version tag matching `v*` runs the
[`release-artifacts.yml`](./.github/workflows/release-artifacts.yml) workflow.
It tests the tagged revision, generates the reports and public-data file, and
attaches them to the GitHub release with the source commit recorded in each
artifact.

### Build the static-site copy

```bash
sh scripts/build-pages.sh
```

This regenerates public data from the tracked
`project/data/raw/Period_Components.csv`, then copies the dashboard and static
assets into `public-site/`. Generated dashboard data and `public-site/` are
ignored by Git. No ignored workbook is required; see the
[data dictionary](./project/data/raw/README.md).

## Configuration

[`project/config/site.yaml`](./project/config/site.yaml) is the source for the
runtime site location, PV geometry and ratings, crop-light target, and tracker
movement/wind-stow settings. The Python pipeline loads those settings through
`project.config`. Runtime values should be changed there rather than copied
into individual scenario scripts.

The YAML's `descriptive_metadata` section is documentation-only: system/bed
labels, nominal row width, crop temperature thresholds, and tracker control
mode are not inputs to current model calculations. The DLI minimum acts as a
floor for the controller target; the DLI
target and ceiling define its light band. Missing air temperature uses the
explicit, logged `site.fallback_air_temp_c` scenario value, recorded in each
time-series result with its source.

## Data quality and limits to keep in mind

- All model timestamps must be timezone-aware. Naive input timestamps are
  interpreted in the configured site timezone by the ingestion helpers.
- Quality-control bounds are broad plausibility checks, not sensor calibration.
  Rejected values become missing; they are not evidence of what the true value
  was.
- Interpolation is limited to short internal gaps. Long outages remain missing.
  Daily output reports pre-interpolation daylight source coverage; DLI and PV
  energy are `NaN` below 80% coverage. The measure is based on GHI availability,
  not every weather variable or a general sensor-quality score.
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

## License and reuse

The project's original software and documentation are released under the
[MIT License](./LICENSE). Third-party code, data, and other materials retain
their respective rights and terms; the repository license does not grant
permission to reuse material the project does not own. In particular, see the
provenance note for the [archived pvlib gallery adaptation](./archive/README.md).
