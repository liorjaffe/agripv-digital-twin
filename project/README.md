# Python package guide

For the newcomer overview, model explanations, setup, and runnable workflows,
see the [repository README](../README.md). This page is a compact reference to
the Python package boundaries and input contracts.

## Main call paths

- `project.io.service.process_weather_batch(...)` accepts a clean weather
  table with timezone-aware timestamps and `ghi`, `dhi`, `dni` columns.
- `project.io.service.process_field_export(...)` accepts native station
  exports. It maps probes, reports raw-probe faults, cleans canonical values,
  estimates missing irradiance components from PPFD, and processes each
  recognized logger/subzone.
- `project.io.service.process_period_results_export(...)` processes the
  separate `Period_Components` irradiance export and retains observed tracker
  angles separately from recommendations.
- `project.scenarios.run_timeseries.run_timeseries_pipeline(...)` performs
  solar geometry, candidate crop/PV irradiance, tracker optimization,
  wind-stow handling, DLI integration, and continuous biomass growth.

The default site location and runtime model settings come from
`project/config/site.yaml`, loaded and validated by `project.config`. Pass
explicit keyword arguments to the pipeline when a scenario needs different
geometry or operating settings.

## Input contracts and outputs

`project.io.ingestion.load_timeseries` accepts a pandas DataFrame or CSV,
JSON/JSONL, or Parquet file. It returns a sorted, timezone-aware
`DatetimeIndex`; naive times are interpreted in the configured site timezone.

Native field-export columns are mapped to canonical roles such as
`ppfd_umol_m2_s`, `module_temp_c`, `air_temp_c`, `wind_speed_ms`, and
`pressure_hpa`. Redundant probes are combined by median, with a companion
`*_n_probes` count. `project.qc.cleaning` rejects implausible readings as
missing values and interpolates only short internal gaps.

The clean-weather and field-export services return timestep results, daily
summaries, and telemetry frames. Field processing returns one such tuple per
subzone. The command sink is optional; the built-in sinks only collect
recommendations in memory or append JSON Lines.

## Testing

From the repository root:

```bash
PYTHONPATH=. .venv/bin/python -m pytest -q project/tests/
```

Add focused tests when changing conversions, sensor mappings, model inputs,
control constraints, configuration, or report-generation behavior.
