"""Shared seasonal-temperature and repeated-crop calculations for reports."""

from __future__ import annotations

import math

import pandas as pd

from project.models.lettuce import (
    DEFAULT_INITIAL_NONSTRUCTURAL_DRY_BIOMASS_G_M2,
    DEFAULT_INITIAL_STRUCTURAL_DRY_BIOMASS_G_M2,
    simulate_growth_timeseries,
)
from project.models.lettuce_development import LettuceThermalDevelopment

INITIAL_DRY_BIOMASS_G_M2 = (
    DEFAULT_INITIAL_STRUCTURAL_DRY_BIOMASS_G_M2
    + DEFAULT_INITIAL_NONSTRUCTURAL_DRY_BIOMASS_G_M2
)
DRY_MATTER_FRACTION_OF_FRESH_MASS = 0.05


def seasonal_mean_temp_c(day_of_year: int) -> float:
    """Return the report's illustrative seasonal canopy-temperature curve."""
    return 20.5 + 5.0 * math.cos(2.0 * math.pi * (day_of_year - 34.0) / 365.25)


def seasonal_canopy_temperature(
    times: pd.DatetimeIndex,
    planting_temp_c: float = 24.0,
) -> pd.Series:
    """Build the seasonal curve with its first day shifted to planting temperature."""
    if times.empty:
        return pd.Series(index=times, dtype=float)
    planting_offset = planting_temp_c - seasonal_mean_temp_c(int(times[0].dayofyear))
    return pd.Series(
        [seasonal_mean_temp_c(int(timestamp.dayofyear)) + planting_offset for timestamp in times],
        index=times,
    )


def simulate_repeated_crops(
    results: pd.DataFrame,
    light_column: str,
    max_cycle_days: int = 120,
    *,
    mark_cycle_window_end_as_harvest: bool = False,
) -> pd.DataFrame:
    """Simulate report crop cycles from hourly light and thermal-time development.

    The report's fresh-mass equivalent is a model estimate derived from dry-biomass
    gain using a fixed 5% dry-matter assumption. It is not a measured crop yield and
    should be labelled as such in any reporting or monetization layer.
    ``mark_cycle_window_end_as_harvest`` preserves the timeline export's historical
    convention of marking the end of its final, incomplete data window as a harvest.
    """
    if max_cycle_days < 1:
        raise ValueError("max_cycle_days must be at least 1")
    if light_column not in results.columns:
        raise ValueError(f"results are missing light column {light_column!r}")

    columns = [
        "cycle_id",
        "cycle_dry_biomass_g_m2",
        "cycle_fresh_biomass_g_m2",
        "cycle_model_fresh_biomass_g_m2",
        "harvest",
    ]
    if results.empty:
        return pd.DataFrame(columns=columns, index=results.index)

    records = []
    start = 0
    cycle_number = 1
    while start < len(results):
        candidate = results.iloc[start : start + max_cycle_days * 24]
        if candidate.empty:
            break

        temperatures = seasonal_canopy_temperature(candidate.index)
        thermal = LettuceThermalDevelopment()
        harvest_position = len(candidate) - 1
        matured = False
        for date, day_temperature in temperatures.groupby(temperatures.index.normalize()).mean().items():
            if thermal.update(float(day_temperature))["harvest_ready"]:
                day_positions = [
                    position
                    for position, timestamp in enumerate(candidate.index)
                    if timestamp.normalize() == date
                ]
                if day_positions:
                    harvest_position = day_positions[-1]
                    matured = True
                    break

        crop = candidate.iloc[: harvest_position + 1]
        growth = simulate_growth_timeseries(
            crop.index,
            crop[light_column] * 0.45,
            seasonal_canopy_temperature(crop.index),
            x_sdw0=DEFAULT_INITIAL_STRUCTURAL_DRY_BIOMASS_G_M2,
            x_nsdw0=DEFAULT_INITIAL_NONSTRUCTURAL_DRY_BIOMASS_G_M2,
        )
        cycle = pd.DataFrame(index=crop.index)
        cycle["cycle_id"] = cycle_number
        cycle["cycle_dry_biomass_g_m2"] = growth["total_dry_biomass"]
        cycle["cycle_model_fresh_biomass_g_m2"] = (
            (growth["total_dry_biomass"] - INITIAL_DRY_BIOMASS_G_M2).clip(lower=0.0)
            / DRY_MATTER_FRACTION_OF_FRESH_MASS
        )
        cycle["cycle_fresh_biomass_g_m2"] = cycle["cycle_model_fresh_biomass_g_m2"]
        cycle["harvest"] = False
        if matured or mark_cycle_window_end_as_harvest:
            cycle.iloc[-1, cycle.columns.get_loc("harvest")] = True

        records.append(cycle)
        start += len(crop)
        cycle_number += 1
    return pd.concat(records, ignore_index=False)
