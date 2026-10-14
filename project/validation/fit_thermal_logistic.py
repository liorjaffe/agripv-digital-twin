"""Report-only logistic fit of lettuce fresh mass against TC thermal time."""

from __future__ import annotations

import argparse
from datetime import date, timedelta
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import curve_fit
from scipy.special import expit

from project.io.period_results import (
    DEFAULT_TMY_AIR_TEMPERATURE_SOURCE,
    load_tmy_air_temperature,
)
from project.models.lettuce_development import (
    LettuceThermalDevelopmentParams,
    daily_gdd,
)

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_WEIGHING_CSV = ROOT / "project" / "data" / "field" / "growth_weighing_cycle1.csv"


def logistic_fresh_mass(gdd: np.ndarray, a: float, b: float, c: float) -> np.ndarray:
    """Return a / (1 + exp(-(b + c * GDD))) using a stable sigmoid."""
    return a * expit(b + c * gdd)


def _thermal_time_by_date(
    observation_dates: pd.Series,
    transplant_date: date,
    air_temperature: pd.Series,
) -> np.ndarray:
    if not isinstance(air_temperature.index, pd.DatetimeIndex):
        raise ValueError("air_temperature must use a DatetimeIndex")
    if air_temperature.index.has_duplicates:
        raise ValueError("air_temperature timestamps must be unique")

    timestamps = air_temperature.index
    local_dates = timestamps.tz_localize(None).normalize() if timestamps.tz else timestamps.normalize()
    daily_temperature = pd.Series(
        pd.to_numeric(air_temperature, errors="coerce").to_numpy(dtype=float),
        index=local_dates,
    ).groupby(level=0).mean()
    if daily_temperature.isna().any():
        raise ValueError("air_temperature daily means must be finite")

    base_temperature = LettuceThermalDevelopmentParams().lettuce_base_temperature_tc
    totals: list[float] = []
    for observed in observation_dates:
        if observed < transplant_date:
            raise ValueError("weighing dates cannot precede the transplant date")
        total_gdd = 0.0
        first_day = transplant_date + timedelta(days=1)
        if observed >= first_day:
            required_days = pd.date_range(first_day, observed, freq="D")
            missing_days = required_days.difference(daily_temperature.index)
            if len(missing_days):
                raise ValueError(
                    "air_temperature does not cover every day from transplant "
                    f"through {observed.date()}"
                )
            total_gdd = sum(
                daily_gdd(float(daily_temperature.loc[day]), base_temperature)
                for day in required_days
            )
        totals.append(total_gdd)
    return np.asarray(totals, dtype=float)


def fit_thermal_logistic(
    weighing_csv: str | Path,
    transplant_date: str | date,
    air_temperature: pd.Series,
    *,
    harvest_date: str | date | None = None,
) -> dict:
    """Fit mean plant fresh mass, requiring four dates and an observed harvest.

    The transplant date is treated as GDD zero. Daily TC GDD is accumulated
    from the day after transplant through each weighing date, inclusive.
    """
    transplant = pd.Timestamp(transplant_date).date()
    harvest = pd.Timestamp(harvest_date).date() if harvest_date is not None else None
    frame = pd.read_csv(weighing_csv)
    required = {"date", "bed_position", "fresh_mass_g", "dry_mass_g", "preliminary"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"weighing CSV is missing columns: {sorted(missing)}")

    frame["date"] = pd.to_datetime(frame["date"], errors="coerce").dt.date
    if frame["date"].isna().any():
        raise ValueError("weighing dates must be valid")
    frame["fresh_mass_g"] = pd.to_numeric(frame["fresh_mass_g"], errors="coerce")
    valid = frame["fresh_mass_g"].notna() & np.isfinite(frame["fresh_mass_g"])
    measurements = frame.loc[valid].copy()
    distinct_dates = sorted(measurements["date"].unique())

    if len(distinct_dates) < 4:
        return {
            "status": "insufficient_data",
            "reason": "fewer_than_four_distinct_weighing_dates",
            "distinct_dates": len(distinct_dates),
        }
    if harvest is None or harvest not in set(distinct_dates):
        return {
            "status": "insufficient_data",
            "reason": "no_weighing_on_harvest_date",
            "distinct_dates": len(distinct_dates),
        }

    means = measurements.groupby("date", sort=True)["fresh_mass_g"].mean()
    dates = pd.Series(means.index, dtype=object)
    x = _thermal_time_by_date(dates, transplant, air_temperature)
    y = means.to_numpy(dtype=float)
    if np.any(y <= 0.0):
        raise ValueError("mean fresh mass must be positive for logistic fitting")
    if np.unique(x).size < 4:
        raise ValueError("thermal time must have at least four distinct values")

    maximum = float(y.max())
    span = float(x.max() - x.min())
    initial_a = maximum * 1.25
    initial_fraction = min(max(float(y[0]) / initial_a, 1e-4), 1.0 - 1e-4)
    initial_b = float(np.log(initial_fraction / (1.0 - initial_fraction)))
    initial_c = 4.0 / span
    parameters, covariance = curve_fit(
        logistic_fresh_mass,
        x,
        y,
        p0=(initial_a, initial_b, initial_c),
        bounds=((maximum, -np.inf, 0.0), (np.inf, np.inf, np.inf)),
        maxfev=20000,
    )
    standard_errors = np.sqrt(np.diag(covariance))
    if not np.isfinite(standard_errors).all():
        raise RuntimeError("curve fit did not produce finite parameter standard errors")
    a, b, c = (float(value) for value in parameters)
    predictions = logistic_fresh_mass(x, *parameters)
    return {
        "status": "fit",
        "parameters": {"a": a, "b": b, "c": c},
        "standard_errors": {
            name: float(error)
            for name, error in zip(("a", "b", "c"), standard_errors)
        },
        "rmse_g_per_plant": float(np.sqrt(np.mean((predictions - y) ** 2))),
        "inflection_gdd": float(-b / c),
        "n_dates": len(distinct_dates),
        "harvest_date": harvest.isoformat(),
        "gdd": [float(value) for value in x],
        "mean_fresh_mass_g_per_plant": [float(value) for value in y],
        "preliminary_data_included": bool(measurements["preliminary"].astype(str).str.lower().eq("true").any()),
    }


def _load_default_temperature(transplant_date: str | date) -> pd.Series:
    year = pd.Timestamp(transplant_date).year
    return load_tmy_air_temperature(
        DEFAULT_TMY_AIR_TEMPERATURE_SOURCE,
        year=year,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--weighings", type=Path, default=DEFAULT_WEIGHING_CSV)
    parser.add_argument("--transplant-date", required=True)
    parser.add_argument("--harvest-date")
    parser.add_argument("--temperature-csv", type=Path)
    args = parser.parse_args()
    temperature = (
        load_tmy_air_temperature(args.temperature_csv, year=pd.Timestamp(args.transplant_date).year)
        if args.temperature_csv
        else _load_default_temperature(args.transplant_date)
    )
    result = fit_thermal_logistic(
        args.weighings,
        args.transplant_date,
        temperature,
        harvest_date=args.harvest_date,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
