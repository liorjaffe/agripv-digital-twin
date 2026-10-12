"""Tracker-control regressions for reachable movements and DLI bounds."""

from __future__ import annotations

import pandas as pd
import pvlib

from project.config import make_site_location
from project.models.radiation import tracker_orientation
from project.scenarios.run_timeseries import run_timeseries_pipeline


def _clear_sky_weather(scale: float = 1.0) -> tuple[pvlib.location.Location, pd.DataFrame]:
    location = make_site_location()
    times = pd.date_range(
        "2026-06-15 05:00",
        "2026-06-15 20:00",
        freq="15min",
        tz="America/Sao_Paulo",
    )
    weather = location.get_clearsky(times, model="ineichen") * scale
    weather["air_temp_c"] = 24.0
    weather["wind_speed_ms"] = 2.0
    return location, weather


def test_low_light_schedule_can_move_and_remains_light_seeking():
    location, weather = _clear_sky_weather(scale=0.1)

    results, daily = run_timeseries_pipeline(weather, location)

    schedule = results["tilt_offset_deg"]
    assert schedule.nunique() > 1
    assert schedule.diff().abs().dropna().max() <= 3.75
    assert daily["dli_mol_m2_day"].iloc[0] < 14.0
    assert schedule.diff().abs().gt(0.0).any()


def test_dli_ceiling_sensitivity_reduces_excess_light():
    location, weather = _clear_sky_weather()

    target_schedule, target_daily = run_timeseries_pipeline(
        weather, location, dli_max_mol_m2_day=14.0
    )
    capped_schedule, capped_daily = run_timeseries_pipeline(
        weather, location, dli_max_mol_m2_day=18.0
    )

    dli_at_target_ceiling = target_daily["dli_mol_m2_day"].iloc[0]
    dli_at_higher_ceiling = capped_daily["dli_mol_m2_day"].iloc[0]
    assert abs(dli_at_target_ceiling - 14.0) < abs(dli_at_higher_ceiling - 14.0)
    assert not target_schedule["tilt_offset_deg"].equals(capped_schedule["tilt_offset_deg"])
    assert dli_at_higher_ceiling <= 18.0


def test_configured_dli_minimum_is_an_active_target_floor():
    location, weather = _clear_sky_weather(scale=0.1)

    floored, _ = run_timeseries_pipeline(
        weather,
        location,
        dli_target_mol_m2_day=8.0,
        dli_min_mol_m2_day=10.0,
    )
    at_minimum, _ = run_timeseries_pipeline(
        weather,
        location,
        dli_target_mol_m2_day=10.0,
        dli_min_mol_m2_day=10.0,
    )

    pd.testing.assert_series_equal(
        floored["target_ppfd_umol_m2_s"],
        at_minimum["target_ppfd_umol_m2_s"],
    )


def test_missing_air_temperature_uses_and_reports_configured_scenario_fallback(caplog):
    location, weather = _clear_sky_weather()
    weather = weather.drop(columns="air_temp_c")

    results, _ = run_timeseries_pipeline(
        weather, location, fallback_air_temp_c=23.0
    )

    assert results["model_air_temp_c"].eq(23.0).all()
    assert results["model_air_temp_source"].eq("configured scenario fallback").all()
    assert "using configured fallback_air_temp_c=23.0 C" in caplog.text


def test_high_wind_commands_absolute_tracker_stow_angle():
    location, weather = _clear_sky_weather()
    weather["wind_speed_ms"] = 20.0
    solar = location.get_solarposition(weather.index)
    baseline = tracker_orientation(solar, axis_azimuth_deg=0.0, gcr=0.3973)

    results, _ = run_timeseries_pipeline(weather, location)

    assert results["tracker_theta_deg"].eq(0.0).all()
    assert baseline["tracker_theta"].dropna().abs().max() > 0.0


def test_daily_energy_metrics_are_suppressed_when_daylight_coverage_is_low():
    location, weather = _clear_sky_weather()
    times = weather.index
    daylight = location.get_solarposition(times)["apparent_zenith"] < 90.0
    missing = daylight & (times.hour >= 9) & (times.hour < 15)
    weather.loc[missing, ["ghi", "dni", "dhi"]] = float("nan")

    _, daily = run_timeseries_pipeline(weather, location)

    assert daily["daylight_coverage_fraction"].iloc[0] < 0.8
    assert not daily["daylight_coverage_sufficient"].iloc[0]
    assert pd.isna(daily["dli_mol_m2_day"].iloc[0])
    assert pd.isna(daily["pv_energy_kwh"].iloc[0])
