# AgriPV Control Project

This project is organized around the brief for an agrivoltaic lettuce control pipeline for the Fotovoltaica/UFSC pilot in Florianópolis. The modeled plant is two 16 kWp systems (32 kWp DC total) represented by four equivalent tracker rows, two assigned to system 2 and two assigned to system 3.

## Structure

- `project/models/conversions.py` — unit-safe conversion utilities for GHI/PAR/PPFD/DLI/pressure.
- `project/models/radiation.py` — pvlib solar position, tracker geometry, bifacial/crop irradiance, PPFD → ghi/dni/dhi reconstruction, and PV power.
- `project/models/lettuce.py` — Van Henten style lettuce growth model in ODE form.
- `project/io/field_data.py` — recognizes real datalogger column names (e.g. `CR1Kx-TempMod1`, `CR310_01-Ws`) and aggregates redundant probes per logger/subzone; `raw_probe_quality_report` checks each raw probe individually so a single faulty sensor isn't hidden by median aggregation.
- `project/qc/cleaning.py` — canonical sensor roles, physical-plausibility bounds, spike rejection, and gap-limited cleaning for real field exports.
- `project/control/optimizer.py` — greedy tilt-schedule selection from pvlib-evaluated candidates.
- `project/control/smoothing.py` — wind-stow safety fallback.
- `project/io/ingestion.py` — DataFrame/CSV/JSON/Parquet input contract, plus `load_field_export` for raw multi-logger station exports.
- `project/io/service.py` — orchestration from incoming data to model outputs and commands (`process_weather_batch` for a clean ghi/dhi/dni contract, `process_field_export` for raw station exports).
- `project/io/commands.py` — tracker-command contract with dry-run and JSONL sinks.
- `project/io/grafana.py` — dashboard telemetry JSON and InfluxDB line protocol.
- `project/scenarios/run_benchmark.py` — seasonal strategy comparison entry point.
- `project/scenarios/run_sample_field_export.py` — runnable example that processes `project/data/raw/station_export.csv` (a synthetic export with the same logger/column naming and sensor-fault patterns as the real station) end to end and prints a quality report plus daily results.
- `project/data/raw/station_export.csv` — synthetic sample multi-logger export for the example above.
- `project/config/site.yaml` — site and control configuration.
- `project/tests/test_conversions.py` — unit tests for the conversion layer.
- `project/tests/test_field_ingestion.py` — column mapping, QC bounds/spike rejection, and PPFD → ghi/dni/dhi reconstruction tests, using the same fault patterns (temperature dropouts, PAR spikes, wind/pressure sentinel values) seen in real station exports.

## Verification

A `.venv` in this folder has the dependencies from `requirements.txt` installed
(pandas, numpy, scipy, pvlib, matplotlib, pytest). To set up from scratch:

```bash
cd "/Users/liorjaffe/Desktop/Brasil/AgriPV/AgriPV Simulations"
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Run the tests:

```bash
PYTHONPATH=. .venv/bin/python3 -m pytest -q project/tests/
```

## Time-series behavior

The radiation wrapper accepts timezone-aware `pandas` time series at 15-minute,
hourly, daily, or other regular/irregular intervals. Each timestamp may have its
own `ghi`, `dhi`, and `dni`, so cloudy periods are represented by lower direct and
diffuse irradiance rather than by a fixed clear-sky assumption.

`dli_from_timeseries` integrates the actual elapsed seconds between PPFD samples.
`simulate_growth_timeseries` carries lettuce biomass continuously across day,
month, and year boundaries using those same elapsed seconds. A long run therefore
does not reset at midnight or at the end of a month.

The current model does not yet control physical trackers; it produces
recommendations from historical or live-replayed weather. Real station data is
now supported end to end (see below), though ghi/dni/dhi are estimated from a
PAR sensor rather than measured by a pyranometer.

## External interfaces

### Already-clean ghi/dhi/dni weather

```python
from project.io.commands import DryRunCommandSink
from project.io.service import process_weather_batch

sink = DryRunCommandSink()
results, daily, grafana_rows = process_weather_batch(
	source="data/clean/weather.parquet",
	location=location,
	command_sink=sink,
	subzone_id="z01",
)
```

The minimum weather contract is timezone-aware data with `ghi`, `dhi`, and `dni`
columns. `sink` is deliberately a dry-run adapter for now. A future laboratory
protocol can implement the same `CommandSink.send()` method, while Grafana can
consume `grafana_rows`, the JSON exporter, or the InfluxDB line protocol.

### Raw multi-logger station exports (Campbell Scientific style)

The Fotovoltaica/UFSC station exports columns named after the logger and probe,
e.g. `CR1Kx-TempMod1`, `CR310-04-Par`, or `CR310_01-Ws` (a mid-deployment channel
rename can even leave two historical names, like `CR310_01-Ws` and
`CR310_01_-Ws`, for the same physical sensor). This export has **no
pyranometer** — only quantum PAR sensors — so `ghi`/`dni`/`dhi` are not measured
directly. `process_field_export` handles the whole chain automatically, per
logger/subzone:

```python
from project.io.commands import DryRunCommandSink
from project.io.service import process_field_export

sink = DryRunCommandSink()
outputs = process_field_export("data/raw/station_export.csv", location, command_sink=sink)
results, daily, grafana_rows = outputs["CR1Kx"]
```

The chain is: `project.io.field_data` recognizes and groups raw columns by
logger/subzone and aggregates redundant probes (median across e.g.
`TempMod1..4`) → `project.qc.cleaning` rejects physically-impossible or spiky
samples (temperature dropouts to roughly -300 degC, PAR spikes far above the
~2200 µmol/m²/s physical ceiling, negative wind-speed sentinels, pressure
dropouts/spikes have all been observed in real exports) as `NaN` rather than
silently clipping them, then bridges only short gaps (a few missing samples) so
a multi-day station outage is never invented as smooth data →
`project.models.radiation.estimate_ghi_dni_dhi_from_ppfd` converts the measured
PPFD into `ghi`/`dni`/`dhi` using a clear-sky index (Ineichen) and the Erbs
decomposition model — an estimate, not a measurement, and labeled as such in
code comments. Measured module temperature, wind speed, and barometric pressure
(converted from hPa to Pa) are threaded through to the PV thermal model,
wind-stow safety, and refraction-corrected solar position respectively instead
of relying on fixed defaults. `daily['input_data_complete_fraction']` reports
how much of each day's input was actually measured, so low-quality days are
visible instead of silently trusted.

Try it against the bundled synthetic sample export (same column naming and
fault patterns as the real station):

```bash
PYTHONPATH=. .venv/bin/python3 project/scenarios/run_sample_field_export.py
```

This prints per-probe and per-subzone quality reports (including faults a
single healthy majority would otherwise hide, via
`project.io.field_data.raw_probe_quality_report`) followed by the daily
results for each recognized logger/subzone.

## Interactive sandbox

Open `agripv_dashboard.html` directly in a browser for a dependency-free
parameter sandbox. Its solar position, tracker backtracking geometry, ground
shading/view-factor, clear-sky, and PPFD/DLI math are ported from the same
pvlib formulas used in `project/models/radiation.py` (see comments in the
dashboard's script for the exact source function each block mirrors), so the
sun path, sunrise/sunset, and light numbers shown are the same physics as the
Python pipeline, not an independent illustration. The bifacial PV yield number
is still a simplified isotropic-transposition stand-in for the full
`pvlib.bifacial.infinite_sheds` model used in Python, and is labeled as such in
the interface.
