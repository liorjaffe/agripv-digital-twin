# Raw and public-data sources

## `Period_Components.csv`

This is the tracked CSV source used by the Python simulation, standalone model
timeline, and public dashboard-data exporter. It contains 3,992 timestamped
rows spanning 2026-01-01 through 2026-12-31, with one calendar date absent
(2026-10-16). Most observations are one hour apart during daylight, with
overnight and occasional longer gaps. Timestamps include the `-03:00` offset.

The model consumes `GHI`, `DNI`, and `DHI` as global, direct-normal, and
diffuse-horizontal irradiance in W/m². The export itself does not document the
instrument models, calibration, interval averaging method, or whether each
component is a direct measurement or a derived value. Those unit/measurement
interpretations are model input assumptions pending the original data
dictionary.

The grid columns such as `0A_AVG`, `2A_AVG`, and `2B_AVG`, as well as the
`FIX*` and `TRK*` columns, have export labels but no source-provided units,
sensor types, or physical placement in the available file. They remain
unclassified in the processing pipeline. Their use in public scenario plots
does not establish a bed mapping or independent validation. Tracker-angle
sign convention is also not documented here.

**Open item:** obtain the instrument/channel map and measurement protocol from
the site, then update this dictionary and the references register before
presenting channel-derived values as measured bed-level light. Until then,
do not use the exploratory channel-comparison metrics to calibrate crop-light
conversion or revise the DLI target/ceiling; the comparison's assumed units
could change the apparent error substantially.

## `tmy_air_temperature.csv`

This temperature-only extract was made from the user-supplied Apple Numbers
workbook `tmy_-27.6000_-48.5000 .numbers`. It contains 8,760 hourly
`temp_air` values and UTC timestamps from a non-leap typical meteorological year.
Only its timestamp and air-temperature columns are retained: its GHI, DNI, DHI,
and other weather columns are not used. The original `Period_Components.csv`
irradiance values remain unchanged.

For the 2026 field-export timestamps, typical-year temperatures are mapped by
UTC month, day, and hour onto the matching local-standard-time hours, then
included across the full local calendar year so nighttime crop respiration is
temperature-dependent too. The TMY coordinates in its filename
(-27.6000, -48.5000) differ slightly from the configured site coordinates
(-27.5949, -48.5480). This is therefore a nearby climatological scenario, not
measured air temperature during the irradiance year or at the exact site.

The simulation keeps all supplied GHI/DNI/DHI measurements as they are. Missing
nighttime model inputs are set to zero based on solar zenith. For this
daytime-only export, any other unrecorded irradiance timestamps are also
assumed to have zero light, per the user's modeling instruction; this is an
explicit assumption, not an inferred measurement. Explicit source readings
remain unchanged. The TMY source is recorded in each model output. The
configured 26°C value remains only a logged fallback for runs with no
temperature series. Biomass and crop-cycle results remain provisional because
some daytime gaps may be treated as zero and the crop model has not been
validated against site biomass data.

The irradiance export has 3,992 timestamped data rows, not a complete set of
8,760 hourly observations; some gaps extend to 49 hours. Joining the hourly TMY
temperature series expands the model's time index but does not add observed
irradiance records. Benchmark observation counts are based on the original
field-export timestamps, while TMY-only hours remain in the model input so
temperature can still drive nighttime respiration.

## Public dashboard data

Run `PYTHONPATH=. python scripts/export-period-results-public.py` from the
repository root to regenerate `public/data/period-results-2026.js` from the
tracked CSV. No ignored workbook is required. The public export includes
timestamp, GHI/DNI/DHI values, and timestamp-based source status; other raw
channels are intentionally excluded. The generated file records the source
commit and whether the working tree had changes.

At export time, rows later than the current timestamp in the record timezone
are tagged `future_timestamp_unverified`, not forecast or simulation; the
available source does not establish what they represent. The dashboard's
observational view excludes these rows, while generated research outputs retain
them with that explicit status. Pass an explicit timezone-aware `as_of` when
calling the export or service function to reproduce a cutoff in tests or other
code.
