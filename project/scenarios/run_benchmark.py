"""Compare the configured tracker controller with a flat-angle baseline."""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd
import pvlib

from project.config import make_site_location
from project.io.period_results import period_results_weather
from project.scenarios.run_timeseries import run_timeseries_pipeline

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE = ROOT / "project" / "data" / "raw" / "Period_Components.csv"


def summarize_strategy(results: pd.DataFrame, daily: pd.DataFrame) -> dict[str, float | int]:
    covered = daily["daylight_coverage_sufficient"].fillna(False)
    valid_dli = daily.loc[covered, "dli_mol_m2_day"].dropna()
    valid_energy = daily.loc[covered, "pv_energy_kwh"].dropna()
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
        "nonzero_tilt_fraction": float(
            results["tilt_offset_deg"].abs().gt(1e-9).mean()
        ),
    }


def compare_strategies(
    weather: pd.DataFrame,
    location: pvlib.location.Location,
    **pipeline_options,
) -> dict[str, dict[str, float | int]]:
    """Run the optimizer and an always-zero-offset baseline on the same data."""
    optimized, optimized_daily = run_timeseries_pipeline(
        weather, location, **pipeline_options
    )
    flat_options = {
        **pipeline_options,
        "tilt_offsets_deg": (0.0,),
        "move_limit_deg_per_hour": 0.0,
    }
    flat, flat_daily = run_timeseries_pipeline(weather, location, **flat_options)
    return {
        "optimized": summarize_strategy(optimized, optimized_daily),
        "flat_baseline": summarize_strategy(flat, flat_daily),
    }


def run_benchmark(
    source: str | Path = DEFAULT_SOURCE,
    location: pvlib.location.Location | None = None,
    **pipeline_options,
) -> dict[str, object]:
    """Benchmark model strategies against the supplied irradiance time series."""
    source_path = Path(source)
    weather, _, _ = period_results_weather(source_path)
    strategies = compare_strategies(
        weather, location or make_site_location(), **pipeline_options
    )
    logging.info(
        "Benchmark completed for %s rows from %s",
        len(weather),
        source_path,
    )
    return {
        "source": str(source_path),
        "strategies": strategies,
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    benchmark = run_benchmark()
    for name, metrics in benchmark["strategies"].items():
        logging.info("%s: %s", name, metrics)
