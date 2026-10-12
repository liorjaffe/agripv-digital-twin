import pandas as pd

from project.config import make_site_location
from project.scenarios.run_benchmark import compare_strategies


def test_benchmark_runs_real_optimized_and_flat_model_strategies():
    location = make_site_location()
    times = pd.date_range(
        "2026-06-15",
        periods=96,
        freq="15min",
        tz="America/Sao_Paulo",
    )
    weather = location.get_clearsky(times, model="ineichen")
    weather["air_temp_c"] = 24.0
    weather["wind_speed_ms"] = 2.0

    strategies = compare_strategies(weather, location, tilt_offsets_deg=(-15.0, 0.0, 15.0))

    optimized = strategies["optimized"]
    flat = strategies["flat_baseline"]
    assert optimized["timesteps"] == len(weather)
    assert flat["timesteps"] == len(weather)
    assert optimized["final_dry_biomass_g_m2"] > 0.0
    assert flat["final_dry_biomass_g_m2"] > 0.0
    assert optimized["covered_days"] == flat["covered_days"] == 1
    assert optimized["covered_pv_energy_kwh"] > 0.0
    assert flat["covered_pv_energy_kwh"] > 0.0
    assert flat["nonzero_tilt_fraction"] == 0.0
