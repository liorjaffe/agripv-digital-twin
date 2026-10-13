import pandas as pd

from project.config import make_site_location
from project.scenarios.run_benchmark import (
    compare_strategies,
    run_benchmark,
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


def test_benchmark_excludes_future_timestamp_rows(tmp_path, monkeypatch):
    source = tmp_path / "period-results.csv"
    tmy_source = tmp_path / "tmy-temperature.csv"
    tmy_times = pd.date_range("1990-01-01T00:00:00Z", periods=365 * 24, freq="h")
    pd.DataFrame({"time_utc": tmy_times, "temp_air_c": 20.0}).to_csv(
        tmy_source,
        index=False,
    )
    pd.DataFrame(
        {
            "datetime": [
                "2026-10-13T08:00:00-03:00",
                "2026-10-13T09:00:00-03:00",
                "2026-10-13T10:00:00-03:00",
            ],
            "GHI": [50.0, 60.0, 70.0],
            "DNI": [0.0, 10.0, 20.0],
            "DHI": [50.0, 50.0, 50.0],
            "Solar_Azimuth": [0.0, 0.0, 0.0],
            "Solar_Zenith": [90.0, 80.0, 70.0],
            "Solar_Elevation": [0.0, 10.0, 20.0],
            "Tracker_Angle": [0.0, 1.0, 2.0],
        }
    ).to_csv(source, index=False)
    compared_weather = []

    def fake_compare(weather, location, **options):
        compared_weather.append(weather)
        return {}

    monkeypatch.setattr("project.scenarios.run_benchmark.compare_strategies", fake_compare)

    result = run_benchmark(
        source,
        make_site_location(),
        as_of="2026-10-13T09:00:00-03:00",
        air_temperature_source=tmy_source,
    )

    assert len(compared_weather) == 1
    assert compared_weather[0].index.max() == pd.Timestamp(
        "2026-10-13T09:00:00-03:00"
    )
    assert compared_weather[0]["ghi"].notna().sum() == 2
    assert compared_weather[0]["air_temp_c"].notna().all()
    assert len(compared_weather[0]) > 2
    assert result["observed_rows"] == 2
    assert result["future_timestamp_unverified_rows_excluded"] == 1
    assert result["data_as_of"] == "2026-10-13T09:00:00-03:00"


def test_benchmark_movement_metric_uses_absolute_tracker_angles():
    from project.scenarios.run_benchmark import summarize_strategy

    index = pd.date_range(
        "2026-06-15 12:00",
        periods=3,
        freq="15min",
        tz="America/Sao_Paulo",
    )
    results = pd.DataFrame(
        {
            "tilt_offset_deg": [0.0, 0.0, 0.0],
            "tracker_theta_deg": [0.0, 2.0, 5.0],
            "total_dry_biomass": [1.0, 1.1, 1.2],
        },
        index=index,
    )
    daily = pd.DataFrame(
        {
            "daylight_coverage_sufficient": [True],
            "dli_mol_m2_day": [10.0],
            "pv_energy_kwh": [2.0],
            "candidate_dli_target_band_reachable": [True],
            "candidate_dli_minimum_reachable": [True],
            "candidate_dli_ceiling_reachable": [True],
            "candidate_min_dli_mol_m2_day": [10.0],
            "candidate_max_dli_mol_m2_day": [15.0],
        },
        index=pd.DatetimeIndex([index[0].normalize()]),
    )

    metrics = summarize_strategy(results, daily)

    assert metrics["mean_tracker_angle_movement_deg_per_timestep"] == 2.5


def test_benchmark_does_not_count_unknown_reachability_as_unreachable():
    from project.scenarios.run_benchmark import summarize_strategy

    index = pd.date_range(
        "2026-06-15 12:00",
        periods=3,
        freq="15min",
        tz="America/Sao_Paulo",
    )
    results = pd.DataFrame(
        {
            "tilt_offset_deg": [0.0, 0.0, 0.0],
            "tracker_theta_deg": [0.0, 0.0, 0.0],
            "total_dry_biomass": [1.0, 1.0, 1.0],
        },
        index=index,
    )
    daily = pd.DataFrame(
        {
            "daylight_coverage_sufficient": [True, True, True],
            "dli_mol_m2_day": [10.0, 12.0, 14.0],
            "pv_energy_kwh": [1.0, 1.0, 1.0],
            "candidate_dli_target_band_reachable": pd.array(
                [True, False, pd.NA], dtype="boolean"
            ),
            "candidate_dli_minimum_reachable": pd.array(
                [True, False, pd.NA], dtype="boolean"
            ),
            "candidate_dli_ceiling_reachable": pd.array(
                [True, True, pd.NA], dtype="boolean"
            ),
            "candidate_min_dli_mol_m2_day": [10.0, 20.0, float("nan")],
            "candidate_max_dli_mol_m2_day": [15.0, 25.0, float("nan")],
        },
        index=pd.date_range(
            index[0].normalize(), periods=3, freq="1D", tz=index.tz
        ),
    )

    metrics = summarize_strategy(results, daily)

    assert metrics["candidate_target_band_reachable_days"] == 1
    assert metrics["candidate_target_band_reachability_unknown_days"] == 1
    assert metrics["candidate_target_unreachable_days"] == 1
    assert metrics["candidate_target_reachability_unknown_days"] == 1
    assert metrics["candidate_ceiling_unreachable_days"] == 0
    assert metrics["candidate_ceiling_reachability_unknown_days"] == 1
