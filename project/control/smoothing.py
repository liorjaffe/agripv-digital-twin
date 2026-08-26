"""Tracker schedule constraints and safety fallbacks."""

from __future__ import annotations

import pandas as pd


def apply_safety(schedule: pd.Series, wind_speed_ms: pd.Series | None, wind_stow_speed_ms: float, fallback: pd.Series | float) -> pd.Series:
    """Use fallback positions for missing commands or wind-stow conditions."""
    result = schedule.astype(float).copy()
    fallback_series = pd.Series(fallback, index=result.index, dtype=float)
    result = result.where(result.notna(), fallback_series)
    if wind_speed_ms is not None:
        wind = wind_speed_ms.reindex(result.index).interpolate(limit_direction="both")
        result = result.where(wind < wind_stow_speed_ms, fallback_series)
    return result
