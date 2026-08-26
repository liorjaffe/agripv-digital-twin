import math

import pandas as pd

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
