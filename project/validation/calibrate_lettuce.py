"""Fit selected lettuce-model parameters to timestamped biomass observations."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import least_squares

from project.models.lettuce import LettuceParams, simulate_growth_timeseries


REQUIRED_COLUMNS = {"time", "par_wm2", "temp_air_c", "observed_total_dry_biomass"}


def calibrate_lettuce(
    observations: pd.DataFrame | None = None,
    *,
    x_sdw0: float = 8.0,
    x_nsdw0: float = 3.0,
    co2_ppm: float = 420.0,
) -> dict:
    """Fit ``c_gr_max`` and ``c_epsilon`` against observed dry biomass.

    ``observations`` must contain timezone-aware ``time``, ``par_wm2``,
    ``temp_air_c``, and ``observed_total_dry_biomass`` columns. ``par_wm2`` is
    PAR energy, not PPFD; this matches ``simulate_growth_timeseries``. Optional
    ``co2_ppm`` may be supplied per row, otherwise the scalar argument is used.
    The first observation defines the model's initial state, so callers should
    provide a baseline measurement at the start of the experiment. Parameters
    are fitted in log-space with bounded least squares to keep both positive.

    No-data calls return ``no_data`` explicitly. The function does not claim
    that default parameters are calibrated when observations are absent.
    """
    if observations is None:
        return {
            "status": "no_data",
            "message": "Pass timestamped biomass observations to fit lettuce parameters.",
            "samples": 0,
            "c_gr_max": None,
            "c_epsilon": None,
        }
    missing = REQUIRED_COLUMNS.difference(observations.columns)
    if missing:
        raise ValueError(f"observations are missing columns: {sorted(missing)}")

    data = observations.copy()
    data["time"] = pd.to_datetime(data["time"], errors="coerce")
    if data["time"].isna().any():
        raise ValueError("observations contain invalid timestamps")
    if data["time"].dt.tz is None:
        raise ValueError("observations time must be timezone-aware")
    data = data.sort_values("time").drop_duplicates("time")
    numeric_columns = ["par_wm2", "temp_air_c", "observed_total_dry_biomass"]
    if "co2_ppm" in data:
        numeric_columns.append("co2_ppm")
    for column in numeric_columns:
        data[column] = pd.to_numeric(data[column], errors="coerce")
    data = data.dropna(subset=numeric_columns)
    if len(data) < 2:
        raise ValueError("at least two finite biomass observations are required")
    if (data["observed_total_dry_biomass"] < 0).any() or (data["par_wm2"] < 0).any():
        raise ValueError("biomass and PAR observations must be non-negative")

    times = pd.DatetimeIndex(data["time"])
    par = data["par_wm2"].to_numpy(float)
    temp = data["temp_air_c"].to_numpy(float)
    co2 = data["co2_ppm"].to_numpy(float) if "co2_ppm" in data else float(co2_ppm)
    observed = data["observed_total_dry_biomass"].to_numpy(float)

    def residual(log_parameters: np.ndarray) -> np.ndarray:
        params = LettuceParams(
            c_gr_max=float(np.exp(log_parameters[0])),
            c_epsilon=float(np.exp(log_parameters[1])),
        )
        predicted = simulate_growth_timeseries(
            times,
            par,
            temp,
            co2_ppm=co2,
            x_sdw0=x_sdw0,
            x_nsdw0=x_nsdw0,
            params=params,
        )["total_dry_biomass"].to_numpy()
        return predicted - observed

    initial = np.log([LettuceParams().c_gr_max, LettuceParams().c_epsilon])
    result = least_squares(
        residual,
        initial,
        bounds=(np.log([1e-8, 1e-8]), np.log([1e-3, 1e-2])),
    )
    fitted = np.exp(result.x)
    errors = residual(result.x)
    return {
        "status": "ok",
        "message": "Lettuce parameters fitted with bounded least squares.",
        "samples": int(len(data)),
        "c_gr_max": float(fitted[0]),
        "c_epsilon": float(fitted[1]),
        "rmse_total_dry_biomass": float(np.sqrt(np.mean(errors**2))),
        "optimizer_cost": float(result.cost),
        "converged": bool(result.success),
    }
