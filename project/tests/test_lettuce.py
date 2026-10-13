"""Regression tests for lettuce biomass integration and input gaps."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from project.models.lettuce import simulate_growth_timeseries


def test_zero_light_nighttime_respires_stored_dry_biomass():
    times = pd.date_range(
        "2026-06-01 18:00",
        periods=25,
        freq="1h",
        tz="America/Sao_Paulo",
    )

    result = simulate_growth_timeseries(
        times,
        pd.Series(0.0, index=times),
        pd.Series(20.0, index=times),
    )

    assert result["biomass_state_valid"].all()
    assert result["total_dry_biomass"].iloc[-1] < result["total_dry_biomass"].iloc[0]


def test_constant_input_biomass_converges_across_observation_intervals():
    final_biomass = {}
    for frequency in ("15min", "1h", "1D"):
        times = pd.date_range(
            "2026-01-01",
            "2026-01-03",
            freq=frequency,
            tz="America/Sao_Paulo",
        )
        result = simulate_growth_timeseries(
            times,
            pd.Series(100.0, index=times),
            pd.Series(25.0, index=times),
        )
        final_biomass[frequency] = result["total_dry_biomass"].iloc[-1]

    assert np.isclose(final_biomass["15min"], final_biomass["1h"], rtol=1e-8)
    assert np.isclose(final_biomass["15min"], final_biomass["1D"], rtol=1e-8)


def test_long_light_and_temperature_outage_invalidates_biomass_state():
    times = pd.date_range(
        "2026-01-01",
        periods=12,
        freq="1h",
        tz="America/Sao_Paulo",
    )
    par = pd.Series(100.0, index=times)
    temperature = pd.Series(25.0, index=times)
    par.iloc[3:9] = np.nan
    temperature.iloc[3:9] = np.nan

    result = simulate_growth_timeseries(
        times,
        par,
        temperature,
        max_gap_periods=2,
    )

    assert result["par_wm2"].iloc[5:9].isna().all()
    assert result["light_interpolated"].iloc[3:5].all()
    assert result["temperature_interpolated"].iloc[3:5].all()
    assert not result["input_data_complete"].iloc[3:9].any()
    assert not result["biomass_state_valid"].iloc[5:].any()
    assert result["total_dry_biomass"].iloc[5:].isna().all()


def test_short_internal_temperature_gap_is_interpolated():
    times = pd.date_range(
        "2026-01-01",
        periods=5,
        freq="1h",
        tz="America/Sao_Paulo",
    )
    temperature = pd.Series([20.0, 22.0, np.nan, 26.0, 28.0], index=times)

    result = simulate_growth_timeseries(
        times,
        pd.Series(100.0, index=times),
        temperature,
        max_gap_periods=1,
    )

    assert result["temperature_interpolated"].iloc[2]
    assert result["temp_air_c"].iloc[2] == 24.0
    assert result["biomass_state_valid"].all()


@pytest.mark.parametrize("integration_step_seconds", [0.0, -1.0, float("nan")])
def test_integration_step_must_be_finite_and_positive(integration_step_seconds):
    times = pd.date_range(
        "2026-01-01",
        periods=2,
        freq="1h",
        tz="America/Sao_Paulo",
    )

    with pytest.raises(ValueError, match="integration_step_seconds"):
        simulate_growth_timeseries(
            times,
            pd.Series(100.0, index=times),
            pd.Series(25.0, index=times),
            integration_step_seconds=integration_step_seconds,
        )
