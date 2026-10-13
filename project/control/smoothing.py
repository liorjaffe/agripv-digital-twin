"""Tracker schedule constraints and safety fallbacks."""

from __future__ import annotations

import pandas as pd


def apply_safety(
    schedule: pd.Series,
    wind_speed_ms: pd.Series | None,
    wind_stow_speed_ms: float,
    fallback: pd.Series | float,
    *,
    max_gap_periods: int = 4,
) -> pd.Series:
    """Use fallback positions for missing commands or wind-stow conditions."""
    result = schedule.astype(float).copy()
    fallback_series = pd.Series(fallback, index=result.index, dtype=float)
    result = result.where(result.notna(), fallback_series)
    if max_gap_periods < 1:
        raise ValueError("max_gap_periods must be at least one")
    if wind_speed_ms is not None:
        wind = wind_speed_ms.reindex(result.index).interpolate(
            method="time",
            limit=max_gap_periods,
            limit_area="inside",
        )
        safe_wind = wind.lt(wind_stow_speed_ms) & wind.notna()
        result = result.where(safe_wind, fallback_series)
    return result
