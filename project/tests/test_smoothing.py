import pandas as pd

from project.control.smoothing import apply_safety


def test_missing_wind_beyond_interpolation_limit_uses_safe_fallback():
    times = pd.date_range("2026-01-01", periods=8, freq="h", tz="UTC")
    schedule = pd.Series(20.0, index=times)
    wind = pd.Series(2.0, index=times)
    wind.iloc[2:6] = float("nan")

    safe = apply_safety(
        schedule,
        wind,
        wind_stow_speed_ms=15.0,
        fallback=0.0,
        max_gap_periods=1,
    )

    assert safe.iloc[2] == 20.0
    assert safe.iloc[3:5].eq(0.0).all()
    assert safe.iloc[6] == 20.0
