import math

import pandas as pd

from project.control.optimizer import optimize_tilt_schedule
from project.models.conversions import (
    dli_from_ghi,
    dli_from_timeseries,
    energy_from_power_timeseries_kwh,
    ghi_to_par,
    par_to_ppfd,
)
from project.models.radiation import pvwatts_power


def test_ghi_to_par_uses_expected_par_fraction():
    assert math.isclose(ghi_to_par(1000.0), 450.0, rel_tol=1e-9)


def test_par_to_ppfd_uses_expected_conversion_factor():
    assert math.isclose(par_to_ppfd(450.0), 2056.5, rel_tol=1e-9)


def test_dli_from_ghi_matches_known_daily_value():
    # A constant 1,000 W/m² over a 12-hour daylight window gives a daily DLI of
    # approximately 88.8 mol m^-2 day^-1, which is a realistic crop-light target for a
    # clear-day upper bound.
    value = dli_from_ghi(1000.0, day_length_hours=12.0)
    assert 80.0 < value < 100.0


def test_dli_from_timeseries_integrates_actual_intervals():
    times = pd.date_range("2026-01-01", periods=5, freq="15min", tz="America/Sao_Paulo")
    ppfd = pd.Series(1000.0, index=times)
    value = dli_from_timeseries(ppfd).iloc[0]
    assert math.isclose(value, 3.6, rel_tol=1e-9)


def test_daily_integrators_skip_intervals_with_missing_samples():
    times = pd.date_range("2026-01-01", periods=4, freq="1h", tz="America/Sao_Paulo")
    ppfd = pd.Series([100.0, 100.0, float("nan"), 100.0], index=times)
    power = pd.Series([1000.0, 1000.0, float("nan"), 1000.0], index=times)

    assert math.isclose(dli_from_timeseries(ppfd).iloc[0], 0.36, rel_tol=1e-9)
    assert math.isclose(
        energy_from_power_timeseries_kwh(power).iloc[0], 1.0, rel_tol=1e-9
    )


def test_pvwatts_power_applies_system_losses_and_inverter_efficiency():
    times = pd.date_range("2026-01-01 12:00", periods=1, tz="UTC")
    poa = pd.Series([1000.0], index=times)
    temperature = pd.Series([25.0], index=times)

    ideal = pvwatts_power(
        poa,
        temperature,
        pdc0_w=1000.0,
        gamma_pdc=0.0,
        system_losses_percent=0.0,
        inverter_efficiency=1.0,
        module_temp_c=temperature,
    )
    derated = pvwatts_power(
        poa,
        temperature,
        pdc0_w=1000.0,
        gamma_pdc=0.0,
        system_losses_percent=14.075660688264469,
        inverter_efficiency=0.96,
        module_temp_c=temperature,
    )

    assert 0.0 < derated.iloc[0] < ideal.iloc[0]


def test_optimize_tilt_schedule_penalizes_crop_light_above_target_band():
    index = pd.date_range("2026-01-01 09:00:00", periods=3, freq="15min", tz="America/Sao_Paulo")
    candidates = {
        0.0: pd.DataFrame({"crop_ppfd_umol_m2_s": [500.0, 500.0, 500.0], "pv_power_w": [100.0, 100.0, 100.0]}, index=index),
        30.0: pd.DataFrame({"crop_ppfd_umol_m2_s": [600.0, 600.0, 600.0], "pv_power_w": [120.0, 120.0, 120.0]}, index=index),
        55.0: pd.DataFrame({"crop_ppfd_umol_m2_s": [700.0, 700.0, 700.0], "pv_power_w": [140.0, 140.0, 140.0]}, index=index),
    }
    target = pd.Series([400.0, 400.0, 400.0], index=index)

    schedule = optimize_tilt_schedule(
        candidates,
        target,
        previous_tilt=0.0,
        max_move_deg=999.0,
        pv_loss_weight=0.0,
        movement_weight=0.0,
    )

    assert schedule["tilt_deg"].tolist() == [0.0, 0.0, 0.0]


def test_optimize_tilt_schedule_uses_light_deficit_when_target_is_unreachable():
    index = pd.date_range("2026-01-01 09:00:00", periods=3, freq="15min", tz="America/Sao_Paulo")
    candidates = {
        0.0: pd.DataFrame({"crop_ppfd_umol_m2_s": [50.0, 50.0, 50.0], "pv_power_w": [100.0, 100.0, 100.0]}, index=index),
        30.0: pd.DataFrame({"crop_ppfd_umol_m2_s": [60.0, 60.0, 60.0], "pv_power_w": [110.0, 110.0, 110.0]}, index=index),
        55.0: pd.DataFrame({"crop_ppfd_umol_m2_s": [80.0, 80.0, 80.0], "pv_power_w": [150.0, 150.0, 150.0]}, index=index),
    }
    target = pd.Series([100.0, 100.0, 100.0], index=index)

    schedule = optimize_tilt_schedule(
        candidates,
        target,
        previous_tilt=0.0,
        max_move_deg=999.0,
        pv_loss_weight=0.0,
        movement_weight=0.0,
    )

    assert schedule["tilt_deg"].tolist() == [55.0, 55.0, 55.0]


def test_unreachable_dli_ceiling_prefers_pv_once_minimum_light_is_met():
    index = pd.date_range(
        "2026-01-01 09:00:00",
        periods=4,
        freq="15min",
        tz="America/Sao_Paulo",
    )
    candidates = {
        0.0: pd.DataFrame(
            {"crop_ppfd_umol_m2_s": 100.0, "pv_power_w": 100.0},
            index=index,
        ),
        30.0: pd.DataFrame(
            {"crop_ppfd_umol_m2_s": 200.0, "pv_power_w": 200.0},
            index=index,
        ),
    }
    schedule = optimize_tilt_schedule(
        candidates,
        pd.Series(0.0, index=index),
        previous_tilt=0.0,
        max_move_deg=30.0,
        pv_loss_weight=1.0,
        movement_weight=0.0,
        dli_target_mol_m2_day=0.01,
        dli_max_mol_m2_day=0.02,
        daylight_seconds=pd.Series(900.0, index=index),
    )

    assert not schedule["dli_ceiling_enforced"].any()
    assert schedule["candidate_min_dli_mol_m2_day"].iloc[0] > 0.02
    assert schedule["tilt_deg"].eq(30.0).all()
