import math

import pandas as pd

from project.control.optimizer import optimize_tilt_schedule
from project.models.conversions import dli_from_ghi, dli_from_timeseries, ghi_to_par, par_to_ppfd


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


def test_optimize_tilt_schedule_prefers_more_crop_light_when_every_candidate_exceeds_target():
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

    assert schedule["tilt_deg"].tolist() == [55.0, 55.0, 55.0]


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
