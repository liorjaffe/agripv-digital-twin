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

`Period_Components.csv` also has no documented air-temperature series. The
pipeline's biomass model therefore uses the configured 26°C fallback on this
dataset. Separately generated crop-cycle and harvest markers use an
illustrative synthetic seasonal-temperature curve. Neither output should be
read as a temperature-driven site prediction until measured site temperatures
are available and the crop model has been validated.

## Public dashboard data

Run `PYTHONPATH=. python scripts/export-period-results-public.py` from the
repository root to regenerate `public/data/period-results-2026.js` from the
tracked CSV. No ignored workbook is required. The public export includes only
timestamp and GHI/DNI/DHI values; other raw channels are intentionally
excluded. The generated file records the source commit and whether the
working tree had changes.
