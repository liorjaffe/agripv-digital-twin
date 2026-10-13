"""Compare the configured tracker controller with a sun-tracking baseline."""

from __future__ import annotations

import argparse
from itertools import product
import logging
import math
from pathlib import Path
from typing import Union

import pandas as pd
import pvlib

from project.config import make_site_location
from project.io.period_results import (
    DEFAULT_TMY_AIR_TEMPERATURE_SOURCE,
    period_results_data_source,
    period_results_weather,
)
from project.scenarios.run_timeseries import run_timeseries_pipeline

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE = ROOT / "project" / "data" / "raw" / "Period_Components.csv"
MetricValue = Union[float, int, str]


def summarize_strategy(
    results: pd.DataFrame, daily: pd.DataFrame
) -> dict[str, MetricValue]:
    covered = daily["daylight_coverage_sufficient"].fillna(False)
    valid_dli = daily.loc[covered, "dli_mol_m2_day"].dropna()
    valid_energy = daily.loc[covered, "pv_energy_kwh"].dropna()
    valid_diagnostics = daily.loc[covered]
    band_reachability = valid_diagnostics[
        "candidate_dli_target_band_reachable"
    ].dropna()
    target_reachability = valid_diagnostics[
        "candidate_dli_minimum_reachable"
    ].dropna()
    ceiling_reachability = valid_diagnostics[
        "candidate_dli_ceiling_reachable"
    ].dropna()
    air_temperature = pd.to_numeric(
        results.get("model_air_temp_c", pd.Series(dtype=float)),
        errors="coerce",
    ).dropna()
    temperature_source = results.get(
        "model_air_temp_source", pd.Series(dtype=object)
    ).dropna()
    valid_biomass = pd.to_numeric(
        results.get("total_dry_biomass", pd.Series(dtype=float)),
        errors="coerce",
    ).dropna()
    return {
        "timesteps": int(len(results)),
        "covered_days": int(covered.sum()),
        "mean_covered_dli_mol_m2_day": (
            float(valid_dli.mean()) if not valid_dli.empty else float("nan")
        ),
        "covered_pv_energy_kwh": (
            float(valid_energy.sum()) if not valid_energy.empty else float("nan")
        ),
        "final_dry_biomass_g_m2": float(results["total_dry_biomass"].iloc[-1]),
        "last_valid_dry_biomass_g_m2": (
            float(valid_biomass.iloc[-1])
            if not valid_biomass.empty
            else float("nan")
        ),
        "last_valid_dry_biomass_timestamp": (
            valid_biomass.index[-1].isoformat()
            if not valid_biomass.empty
            else "unavailable"
        ),
        "biomass_valid_timestep_count": int(len(valid_biomass)),
        "nonzero_tilt_fraction": float(
            results["tilt_offset_deg"].abs().gt(1e-9).mean()
        ),
        "mean_absolute_tracker_angle_deg": float(
            results["tracker_theta_deg"].abs().mean()
        ),
        "model_air_temp_source": (
            str(temperature_source.iloc[0])
            if not temperature_source.empty
            else "unavailable"
        ),
        "mean_model_air_temp_c": (
            float(air_temperature.mean())
            if not air_temperature.empty
            else float("nan")
        ),
        "minimum_model_air_temp_c": (
            float(air_temperature.min())
            if not air_temperature.empty
            else float("nan")
        ),
        "maximum_model_air_temp_c": (
            float(air_temperature.max())
            if not air_temperature.empty
            else float("nan")
        ),
        "mean_tracker_angle_movement_deg_per_timestep": float(
            results["tracker_theta_deg"].diff().abs().mean()
        ),
        "candidate_target_band_reachable_days": int(
            band_reachability.eq(True).sum()
        ),
        "candidate_target_band_reachability_unknown_days": int(
            covered.sum() - len(band_reachability)
        ),
        "candidate_target_unreachable_days": int(
            target_reachability.eq(False).sum()
        ),
        "candidate_target_reachability_unknown_days": int(
            covered.sum() - len(target_reachability)
        ),
        "candidate_ceiling_unreachable_days": int(
            ceiling_reachability.eq(False).sum()
        ),
        "candidate_ceiling_reachability_unknown_days": int(
            covered.sum() - len(ceiling_reachability)
        ),
        "mean_candidate_min_dli_mol_m2_day": (
            float(valid_diagnostics["candidate_min_dli_mol_m2_day"].mean())
            if valid_diagnostics["candidate_min_dli_mol_m2_day"].notna().any()
            else float("nan")
        ),
        "mean_candidate_max_dli_mol_m2_day": (
            float(valid_diagnostics["candidate_max_dli_mol_m2_day"].mean())
            if valid_diagnostics["candidate_max_dli_mol_m2_day"].notna().any()
            else float("nan")
        ),
    }


def compare_strategies(
    weather: pd.DataFrame,
    location: pvlib.location.Location,
    **pipeline_options,
) -> dict[str, dict[str, MetricValue]]:
    """Compare the optimizer with an always-zero-offset sun-tracking schedule."""
    optimized, optimized_daily = run_timeseries_pipeline(
        weather, location, **pipeline_options
    )
    sun_tracking_options = {
        **pipeline_options,
        "tilt_offsets_deg": (0.0,),
        "move_limit_deg_per_hour": 0.0,
        "enforce_absolute_slew_limit": False,
    }
    sun_tracking, sun_tracking_daily = run_timeseries_pipeline(
        weather, location, **sun_tracking_options
    )
    return {
        "optimized": summarize_strategy(optimized, optimized_daily),
        "sun_tracking_baseline": summarize_strategy(
            sun_tracking, sun_tracking_daily
        ),
    }


def run_sensitivity_sweep(
    weather: pd.DataFrame,
    location: pvlib.location.Location,
    *,
    dli_targets: tuple[float, ...] = (10.0, 14.0),
    dli_ceilings: tuple[float, ...] = (18.0, 24.0),
    pv_loss_weights: tuple[float, ...] = (0.5, 1.0),
    movement_weights: tuple[float, ...] = (0.0, 0.05),
) -> list[dict[str, MetricValue]]:
    """Run an explicit grid of target, ceiling, PV, and movement settings.

    Output rows retain DLI, PV energy, biomass, and schedule movement metrics
    together so users can inspect the operating-point trade rather than infer a
    universally optimal set of weights.
    """
    axes = {
        "dli_target_mol_m2_day": dli_targets,
        "dli_max_mol_m2_day": dli_ceilings,
        "pv_loss_weight": pv_loss_weights,
        "movement_weight": movement_weights,
    }
    if any(not values for values in axes.values()):
        raise ValueError("every sensitivity axis must contain at least one value")

    rows = []
    for target, ceiling, pv_weight, movement_weight in product(
        dli_targets, dli_ceilings, pv_loss_weights, movement_weights
    ):
        if ceiling < target:
            continue
        results, daily = run_timeseries_pipeline(
            weather,
            location,
            dli_target_mol_m2_day=target,
            dli_max_mol_m2_day=ceiling,
            pv_loss_weight=pv_weight,
            movement_weight=movement_weight,
        )
        rows.append(
            {
                "dli_target_mol_m2_day": target,
                "dli_max_mol_m2_day": ceiling,
                "pv_loss_weight": pv_weight,
                "movement_weight": movement_weight,
                **summarize_strategy(results, daily),
            }
        )
    if not rows:
        raise ValueError("sensitivity grid has no cases where DLI ceiling >= target")
    for row in rows:
        target_error = abs(
            float(row["mean_covered_dli_mol_m2_day"])
            - float(row["dli_target_mol_m2_day"])
        )
        row["dli_target_error_mol_m2_day"] = target_error
    for row in rows:
        row["pareto_optimal"] = not any(
            _dominates(other, row) for other in rows if other is not row
        )
    return rows


def _dominates(
    candidate: dict[str, MetricValue],
    other: dict[str, MetricValue],
) -> bool:
    """Return whether candidate is no worse on all three sensitivity objectives."""
    candidate_energy = float(candidate["covered_pv_energy_kwh"])
    other_energy = float(other["covered_pv_energy_kwh"])
    candidate_error = float(candidate["dli_target_error_mol_m2_day"])
    other_error = float(other["dli_target_error_mol_m2_day"])
    candidate_movement = float(
        candidate["mean_tracker_angle_movement_deg_per_timestep"]
    )
    other_movement = float(other["mean_tracker_angle_movement_deg_per_timestep"])
    if not all(
        math.isfinite(value)
        for value in (
            candidate_energy,
            other_energy,
            candidate_error,
            other_error,
            candidate_movement,
            other_movement,
        )
    ):
        return False
    no_worse = (
        candidate_energy >= other_energy
        and candidate_error <= other_error
        and candidate_movement <= other_movement
    )
    strictly_better = (
        candidate_energy > other_energy
        or candidate_error < other_error
        or candidate_movement < other_movement
    )
    return no_worse and strictly_better


def _observed_period_weather(
    source: str | Path,
    *,
    as_of: str | pd.Timestamp | None = None,
    air_temperature_source: str | Path | None = DEFAULT_TMY_AIR_TEMPERATURE_SOURCE,
) -> tuple[pd.DataFrame, pd.Timestamp, int, int]:
    weather, tracker_observed, _ = period_results_weather(
        source,
        air_temperature_source=air_temperature_source,
    )
    cutoff = pd.Timestamp.now(tz=weather.index.tz) if as_of is None else pd.Timestamp(as_of)
    source_status = period_results_data_source(
        tracker_observed.index,
        as_of=cutoff,
    )
    observed_rows = int(source_status.eq("observed_field_data").sum())
    if observed_rows == 0:
        raise ValueError("No Period_Results rows exist at or before the as-of cutoff")
    return (
        weather.loc[weather.index <= cutoff],
        cutoff.tz_convert(weather.index.tz),
        observed_rows,
        int(source_status.eq("future_timestamp_unverified").sum()),
    )


def run_benchmark(
    source: str | Path = DEFAULT_SOURCE,
    location: pvlib.location.Location | None = None,
    *,
    as_of: str | pd.Timestamp | None = None,
    air_temperature_source: str | Path | None = DEFAULT_TMY_AIR_TEMPERATURE_SOURCE,
    **pipeline_options,
) -> dict[str, object]:
    """Benchmark strategies using only rows not later than the as-of cutoff."""
    source_path = Path(source)
    weather, cutoff, observed_rows, excluded_future_rows = _observed_period_weather(
        source_path,
        as_of=as_of,
        air_temperature_source=air_temperature_source,
    )
    strategies = compare_strategies(
        weather, location or make_site_location(), **pipeline_options
    )
    logging.info(
        "Benchmark used %d observed rows at or before %s from %s; excluded %d "
        "later timestamps with unverified provenance",
        observed_rows,
        cutoff.isoformat(),
        source_path,
        excluded_future_rows,
    )
    return {
        "source": str(source_path),
        "data_as_of": cutoff.isoformat(),
        "observed_rows": observed_rows,
        "future_timestamp_unverified_rows_excluded": excluded_future_rows,
        "strategies": strategies,
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sensitivity",
        action="store_true",
        help="run the default 16-case DLI/PV/movement sensitivity grid",
    )
    args = parser.parse_args()
    if args.sensitivity:
        weather, cutoff, observed_rows, excluded_future_rows = _observed_period_weather(
            DEFAULT_SOURCE,
            air_temperature_source=DEFAULT_TMY_AIR_TEMPERATURE_SOURCE,
        )
        logging.info(
            "Sensitivity uses %d rows at or before %s; excluded %d later timestamps "
            "with unverified provenance",
            observed_rows,
            cutoff.isoformat(),
            excluded_future_rows,
        )
        sweep = run_sensitivity_sweep(weather, make_site_location())
        for row in sweep:
            logging.info("sensitivity case: %s", row)
    else:
        benchmark = run_benchmark()
        for name, metrics in benchmark["strategies"].items():
            logging.info("%s: %s", name, metrics)
