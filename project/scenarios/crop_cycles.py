"""Shared seasonal-temperature and repeated-crop calculations for reports."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from project.config import load_runtime_config
from project.models.conversions import PAR_FRACTION
from project.models.lettuce import (
    DEFAULT_INITIAL_NONSTRUCTURAL_DRY_BIOMASS_G_M2,
    DEFAULT_INITIAL_STRUCTURAL_DRY_BIOMASS_G_M2,
    simulate_growth_timeseries,
)
from project.models.lettuce_development import LettuceThermalDevelopment

# Kept for backward compatibility with callers that import it; crop cycles now
# start from the transplant seedling state below instead of this value.
INITIAL_DRY_BIOMASS_G_M2 = (
    DEFAULT_INITIAL_STRUCTURAL_DRY_BIOMASS_G_M2
    + DEFAULT_INITIAL_NONSTRUCTURAL_DRY_BIOMASS_G_M2
)
# CROP-002: assumed dry-matter fraction; not measured for this cultivar/site.
DRY_MATTER_FRACTION_OF_FRESH_MASS = 0.05
# SITE-003: measured mean fresh mass per seedling at final transplant
# (2026-09-02, n = 6, SD 0.09 g; plants "a couple of weeks old"). Representative
# for every cycle until further transplant weighings are added.
TRANSPLANT_FRESH_MASS_G_PER_PLANT = 0.90
# Seedling dry mass could not be weighed reliably (below scale resolution), so it
# is derived with the same dry-matter fraction used for the fresh-mass output.
# This keeps the conversion consistent: the seedling contributes 0.90 g to the
# reported harvest fresh mass. See references/SITE-003.md for the sensitivity.
SEEDLING_DRY_MATTER_FRACTION = DRY_MATTER_FRACTION_OF_FRESH_MASS
TRANSPLANT_DRY_MASS_G_PER_PLANT = (
    TRANSPLANT_FRESH_MASS_G_PER_PLANT * SEEDLING_DRY_MATTER_FRACTION
)
# Keeps the existing 8:3 structural/non-structural split of the model default.
TRANSPLANT_STRUCTURAL_FRACTION = (
    DEFAULT_INITIAL_STRUCTURAL_DRY_BIOMASS_G_M2 / INITIAL_DRY_BIOMASS_G_M2
)


def transplant_initial_state_g_m2(plant_density_per_m2: float) -> tuple[float, float]:
    """Return (structural, non-structural) dry biomass in g/m² at transplant."""
    if not math.isfinite(plant_density_per_m2) or plant_density_per_m2 <= 0.0:
        raise ValueError("plant_density_per_m2 must be finite and positive")
    total = TRANSPLANT_DRY_MASS_G_PER_PLANT * plant_density_per_m2
    structural = total * TRANSPLANT_STRUCTURAL_FRACTION
    return structural, total - structural


def seasonal_mean_temp_c(day_of_year: int) -> float:
    """Return CROP-002's synthetic seasonal temperature assumption."""
    # CROP-002: illustrative annual mean/amplitude/phase, not site weather.
    return 20.5 + 5.0 * math.cos(2.0 * math.pi * (day_of_year - 34.0) / 365.25)


def seasonal_canopy_temperature(
    times: pd.DatetimeIndex,
    planting_temp_c: float = 24.0,  # CROP-002: assumed first-day temperature.
) -> pd.Series:
    """Build the synthetic CROP-002 curve shifted to the assumed planting temperature."""
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
    temperature_c: pd.Series | None = None,
    plant_density_per_m2: float | None = None,
) -> pd.DataFrame:
    """Simulate report crop cycles from hourly light and thermal-time development.

    Each cycle starts at sowing (CROP-003). The GDD-001 clock first runs the
    sowing-to-transplant (ST, nursery) stage; no field biomass exists during
    that stage, so field dry/fresh biomass is reported as 0 and
    ``cycle_stage`` is ``"nursery"``. At the end of the day the ST requirement
    is met, the seedling is transplanted at field density with
    ``TRANSPLANT_DRY_MASS_G_PER_PLANT`` and the biomass model runs until the
    transplant-to-harvest (TC) requirement is met (``cycle_stage == "field"``).

    The fresh-mass equivalent is total modeled field dry biomass (including the
    transplanted seedling) divided by a fixed 5% dry-matter assumption. It is
    not a measured crop yield and should be labelled as such.
    When ``temperature_c`` is supplied it is used for both crop growth and
    thermal-time development; otherwise the explicitly illustrative seasonal curve
    remains the fallback for standalone callers.
    ``mark_cycle_window_end_as_harvest`` preserves the timeline export's historical
    convention of marking the end of its final, incomplete data window as a harvest.
    """
    if max_cycle_days < 1:
        raise ValueError("max_cycle_days must be at least 1")
    if light_column not in results.columns:
        raise ValueError(f"results are missing light column {light_column!r}")
    if temperature_c is not None:
        if not temperature_c.index.equals(results.index):
            raise ValueError("temperature_c must align with results")
        if not all(math.isfinite(float(value)) for value in temperature_c):
            raise ValueError("temperature_c must contain only finite values")
    if plant_density_per_m2 is None:
        plant_density_per_m2 = load_runtime_config().plant_density_per_m2
    x_sdw0, x_nsdw0 = transplant_initial_state_g_m2(float(plant_density_per_m2))

    columns = [
        "cycle_id",
        "cycle_stage",
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

        candidate_temperature = (
            seasonal_canopy_temperature(candidate.index)
            if temperature_c is None
            else temperature_c.loc[candidate.index]
        )
        candidate_days = candidate.index.normalize()
        thermal = LettuceThermalDevelopment()
        transplant_position: int | None = None
        harvest_position = len(candidate) - 1
        matured = False
        for date, day_temperature in candidate_temperature.groupby(
            candidate_days
        ).mean().items():
            state = thermal.update(float(day_temperature))
            day_positions = np.flatnonzero(candidate_days == date)
            if len(day_positions) == 0:
                continue
            if transplant_position is None and state["stage"] != "ST":
                # ST requirement met during this day: transplant at its end.
                transplant_position = int(day_positions[-1]) + 1
            if state["harvest_ready"]:
                harvest_position = int(day_positions[-1])
                matured = True
                break

        crop = candidate.iloc[: harvest_position + 1]
        cycle = pd.DataFrame(index=crop.index)
        cycle["cycle_id"] = cycle_number
        cycle["cycle_stage"] = "nursery"
        cycle["cycle_dry_biomass_g_m2"] = 0.0
        cycle["cycle_model_fresh_biomass_g_m2"] = 0.0

        if transplant_position is not None and transplant_position < len(crop):
            field = crop.iloc[transplant_position:]
            growth = simulate_growth_timeseries(
                field.index,
                field[light_column] * PAR_FRACTION,
                (
                    seasonal_canopy_temperature(crop.index).loc[field.index]
                    if temperature_c is None
                    else temperature_c.loc[field.index]
                ),
                x_sdw0=x_sdw0,
                x_nsdw0=x_nsdw0,
            )
            cycle.loc[field.index, "cycle_stage"] = "field"
            cycle.loc[field.index, "cycle_dry_biomass_g_m2"] = growth[
                "total_dry_biomass"
            ].to_numpy()
            cycle.loc[field.index, "cycle_model_fresh_biomass_g_m2"] = (
                growth["total_dry_biomass"].clip(lower=0.0)
                / DRY_MATTER_FRACTION_OF_FRESH_MASS
            ).to_numpy()

        cycle["cycle_fresh_biomass_g_m2"] = cycle["cycle_model_fresh_biomass_g_m2"]
        cycle["harvest"] = False
        if matured or mark_cycle_window_end_as_harvest:
            cycle.iloc[-1, cycle.columns.get_loc("harvest")] = True

        records.append(cycle[columns])
        start += len(crop)
        cycle_number += 1
    return pd.concat(records, ignore_index=False)
