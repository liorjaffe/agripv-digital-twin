# AgriPV Digital Twin

Physically grounded AgriPV simulation and tracker-control pipeline for the Fotovoltaica / UFSC pilot in Florianopolis, Brazil. The current modeled plant is 2 x 16 kWp = 32 kWp DC across four equivalent tracker rows: two for system 2 and two for system 3.

## Start here

- Interactive dashboard: `agripv_dashboard.html`
- Python project documentation: `project/README.md`
- Install dependencies: `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`
- Run tests: `PYTHONPATH=. .venv/bin/python3 -m pytest -q project/tests/`
- Run the sample station export: `PYTHONPATH=. .venv/bin/python3 project/scenarios/run_sample_field_export.py`

## Scientific and software foundations

- **pvlib-python** (`pvlib==0.13.0` in the tested environment): solar position, single-axis tracker geometry, backtracking, bifacial/crop irradiance, Faiman temperature, and PVWatts DC power for the 32 kWp modeled plant.
- **Van Henten lettuce growth model**: structural/non-structural dry biomass, photosynthesis, respiration, temperature response, and growth integration. The implementation in `project/models/lettuce.py` is an adaptation of the scientific model, not a verbatim copy of an original software implementation.
- **Campbell Scientific / Grafana field exports**: native logger columns are mapped, checked against physical bounds, and aggregated in `project/io/field_data.py` and `project/qc/cleaning.py`.

## Important modeling boundary

The station export contains quantum PAR/PPFD sensors but no pyranometer. GHI, DNI, and DHI are therefore estimated from PPFD using a clear-sky index and Erbs decomposition. These values are estimates, not direct irradiance measurements, and should be validated against a pyranometer or calibrated field reference before operational decisions.

The current command sinks are dry-run/JSONL adapters. No physical tracker is controlled automatically by this repository until a site-specific hardware protocol adapter, limits, interlocks, and commissioning procedure are added and approved.

See `project/README.md` for the complete data contract, architecture, validation workflow, and team handoff instructions.
