"""Validation and calibration regression tests."""

from __future__ import annotations

import numpy as np
import pandas as pd

from project.models.lettuce import LettuceParams, simulate_growth_timeseries
from project.validation.calibrate_lettuce import calibrate_lettuce
from project.validation.validate_radiation import validate_radiation


def test_calibrate_lettuce_reports_no_data_without_fabricating_a_fit():
    result = calibrate_lettuce()
    assert result["status"] == "no_data"
    assert result["c_gr_max"] is None
    assert result["c_epsilon"] is None


def test_calibrate_lettuce_recovers_known_parameters():
    times = pd.date_range("2026-01-01", periods=12, freq="15min", tz="America/Sao_Paulo")
    par = np.full(len(times), 100.0)
    temp = np.full(len(times), 24.0)
    expected = LettuceParams(c_gr_max=5e-6, c_epsilon=17e-6)
    growth = simulate_growth_timeseries(times, par, temp, params=expected)
    observations = pd.DataFrame(
        {
            "time": times,
            "par_wm2": par,
            "temp_air_c": temp,
            "observed_total_dry_biomass": growth["total_dry_biomass"].to_numpy(),
        }
    )
    result = calibrate_lettuce(observations)
    assert result["status"] == "ok"
    assert result["converged"]
    assert np.isclose(result["c_gr_max"], expected.c_gr_max, rtol=1e-6)
    assert np.isclose(result["c_epsilon"], expected.c_epsilon, rtol=1e-6)
    assert result["rmse_total_dry_biomass"] < 1e-9


def test_validate_radiation_requires_timezone_aware_observations():
    times = pd.date_range("2026-01-01", periods=2, freq="15min")
    values = pd.Series([100.0, 100.0], index=times)
    try:
        validate_radiation(values, values)
    except ValueError:
        pass
    else:
        raise AssertionError("naive timestamps should be rejected")


def test_validate_radiation_aligns_mixed_timezones_before_comparison():
    utc_times = pd.date_range("2026-01-01T00:00:00", periods=4, freq="15min", tz="UTC")
    sao_times = utc_times.tz_convert("America/Sao_Paulo")
    measured = pd.Series([100.0, 200.0, 300.0, 400.0], index=sao_times)
    modeled = pd.Series([110.0, 205.0, 290.0, 410.0], index=utc_times)

    result = validate_radiation(measured, modeled)

    assert result["status"] == "ok"
    assert result["samples"] == 4
    assert result["validated_days"] == 1
