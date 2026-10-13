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
    assert (
        results.loc[
            ~results["wind_stow_slew_override"],
            "tracker_angle_movement_deg",
        ].max()
        <= 3.75
    )
    assert daily["dli_mol_m2_day"].iloc[0] < 14.0
    assert schedule.diff().abs().gt(0.0).any()
    assert abs(
        results["controller_dli_mol_m2_day"].iloc[-1]
        - daily["dli_mol_m2_day"].iloc[0]
    ) < 1e-10


def test_unreachable_dli_ceilings_do_not_change_the_control_schedule():
    location, weather = _clear_sky_weather()

    _, daily = run_timeseries_pipeline(weather, location)

    assert bool(daily["candidate_dli_ceiling_reachable"].iloc[0])


def test_bright_day_reports_unreachable_dli_ceiling():
    location = make_site_location()
    times = pd.date_range(
        "2026-01-15 05:00",
        "2026-01-15 20:00",
        freq="15min",
        tz="America/Sao_Paulo",
    )
    weather = location.get_clearsky(times, model="ineichen")
    weather["air_temp_c"] = 24.0
    weather["wind_speed_ms"] = 2.0

    _, daily = run_timeseries_pipeline(weather, location)

    assert daily["candidate_min_dli_mol_m2_day"].iloc[0] > 18.0
    assert bool(daily["candidate_dli_minimum_reachable"].iloc[0])
    assert not bool(daily["candidate_dli_ceiling_reachable"].iloc[0])
    assert not bool(daily["candidate_dli_target_band_reachable"].iloc[0])
    assert not bool(daily["dli_ceiling_enforced"].iloc[0])


def test_unreachable_dli_ceiling_is_ignored_when_tuning_operating_point():
    location = make_site_location()
    times = pd.date_range(
        "2026-01-15 05:00",
        "2026-01-15 20:00",
        freq="15min",
        tz="America/Sao_Paulo",
    )
    weather = location.get_clearsky(times, model="ineichen")
    weather["air_temp_c"] = 24.0
    weather["wind_speed_ms"] = 2.0

    lower_ceiling, lower_daily = run_timeseries_pipeline(
        weather, location, dli_max_mol_m2_day=14.0
    )
    higher_ceiling, higher_daily = run_timeseries_pipeline(
        weather, location, dli_max_mol_m2_day=18.0
    )

    assert not bool(lower_daily["candidate_dli_ceiling_reachable"].iloc[0])
    assert not bool(higher_daily["candidate_dli_ceiling_reachable"].iloc[0])
    assert lower_ceiling["tilt_offset_deg"].equals(
        higher_ceiling["tilt_offset_deg"]
    )
    assert lower_daily["candidate_min_dli_mol_m2_day"].iloc[0] > 18.0


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


def test_wind_stow_overrides_entry_slew_but_tracker_respects_limit_after_stow():
    location, weather = _clear_sky_weather()
    stow_start = weather.index[28]
    stow_end = weather.index[32]
    weather.loc[stow_start:stow_end, "wind_speed_ms"] = 20.0

    results, daily = run_timeseries_pipeline(weather, location)

    assert results.loc[stow_start:stow_end, "tracker_theta_deg"].eq(0.0).all()
    assert results.loc[stow_start, "wind_stow_slew_override"]
    after_stow = results.loc[stow_end + pd.Timedelta(minutes=15) :]
    assert not after_stow["wind_stow_slew_override"].any()
    assert not after_stow["tracker_slew_limit_exceeded"].any()
    assert (
        after_stow["tracker_angle_movement_deg"]
        <= after_stow["tracker_slew_limit_deg"]
    ).all()
    assert abs(
        results["controller_dli_mol_m2_day"].iloc[-1]
        - daily["dli_mol_m2_day"].iloc[0]
    ) < 1e-10


def test_unknown_wind_after_long_outage_defaults_to_absolute_stow():
    location, weather = _clear_sky_weather()
    weather.loc[weather.index[:8], "wind_speed_ms"] = float("nan")

    results, _ = run_timeseries_pipeline(weather, location, max_gap_periods=4)

    assert results["tracker_theta_deg"].iloc[:4].eq(0.0).all()


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
    assert pd.isna(daily["candidate_dli_target_band_reachable"].iloc[0])
