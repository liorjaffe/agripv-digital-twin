import pandas as pd

from project.config import make_site_location
from project.scenarios.run_benchmark import (
    compare_strategies,
    run_sensitivity_sweep,
)


def test_benchmark_compares_optimized_and_sun_tracking_strategies():
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
    sun_tracking = strategies["sun_tracking_baseline"]
    assert optimized["timesteps"] == len(weather)
    assert sun_tracking["timesteps"] == len(weather)
    assert optimized["final_dry_biomass_g_m2"] > 0.0
    assert sun_tracking["final_dry_biomass_g_m2"] > 0.0
    assert optimized["covered_days"] == sun_tracking["covered_days"] == 1
    assert optimized["covered_pv_energy_kwh"] > 0.0
    assert sun_tracking["covered_pv_energy_kwh"] > 0.0
    assert sun_tracking["nonzero_tilt_fraction"] == 0.0
    assert sun_tracking["mean_absolute_tracker_angle_deg"] > 0.0


def test_sensitivity_sweep_reports_operating_point_and_pareto_metrics():
    location = make_site_location()
    times = pd.date_range(
        "2026-06-15 06:00",
        periods=48,
        freq="15min",
        tz="America/Sao_Paulo",
    )
    weather = location.get_clearsky(times, model="ineichen")
    weather["air_temp_c"] = 24.0

    rows = run_sensitivity_sweep(
        weather,
        location,
        dli_targets=(10.0, 14.0),
        dli_ceilings=(18.0,),
        pv_loss_weights=(1.0,),
        movement_weights=(0.0,),
    )

    assert len(rows) == 2
    assert {row["dli_target_mol_m2_day"] for row in rows} == {10.0, 14.0}
    assert all("covered_pv_energy_kwh" in row for row in rows)
    assert all("mean_covered_dli_mol_m2_day" in row for row in rows)
    assert all("movement_weight" in row for row in rows)
    assert all("pareto_optimal" in row for row in rows)
    assert all("dli_target_error_mol_m2_day" in row for row in rows)
