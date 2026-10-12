"""Compare modeled crop PPFD against measured quantum-PAR sensor data."""

from __future__ import annotations

import numpy as np
import pandas as pd

from project.models.conversions import dli_from_timeseries


def validate_radiation(
    measured_ppfd: pd.Series | None = None,
    modeled_ppfd: pd.Series | None = None,
) -> dict:
    """Return pointwise PPFD and daily-DLI agreement metrics.

    Both series must use timezone-aware ``DatetimeIndex`` values. Samples are
    aligned on identical timestamps and non-finite pairs are excluded. With no
    data, the function reports ``no_data`` rather than returning a misleading
    zero error. This keeps the validation entry point usable now and ready for
    the real PAR export when it is provided.

    Indexes are normalized to UTC before comparison so a project using local
    timezone-aware sensor data can still be validated against model output stored
    in another timezone-aware representation.
    """
    if measured_ppfd is None or modeled_ppfd is None:
        return {
            "status": "no_data",
            "message": "Pass measured_ppfd and modeled_ppfd series to run validation.",
            "samples": 0,
            "daily_dli_error_percent": None,
        }
    if not isinstance(measured_ppfd.index, pd.DatetimeIndex) or not isinstance(modeled_ppfd.index, pd.DatetimeIndex):
        raise TypeError("measured_ppfd and modeled_ppfd must use DatetimeIndex values")
    if measured_ppfd.index.tz is None or modeled_ppfd.index.tz is None:
        raise ValueError("measured_ppfd and modeled_ppfd timestamps must be timezone-aware")

    measured = measured_ppfd.copy().sort_index().tz_convert("UTC")
    modeled = modeled_ppfd.copy().sort_index().tz_convert("UTC")

    paired = pd.concat(
        [measured.rename("measured"), modeled.rename("modeled")], axis=1, join="inner"
    ).replace([np.inf, -np.inf], np.nan).dropna()
    if paired.empty:
        return {
            "status": "no_overlap",
            "message": "The PPFD series have no finite overlapping timestamps.",
            "samples": 0,
            "daily_dli_error_percent": None,
        }
    paired = paired.clip(lower=0.0)
    error = paired["modeled"] - paired["measured"]
    measured_dli = dli_from_timeseries(paired["measured"])
    modeled_dli = dli_from_timeseries(paired["modeled"])
    dli_pairs = pd.concat([measured_dli, modeled_dli], axis=1).dropna()
    dli_error_percent = ((dli_pairs.iloc[:, 1] - dli_pairs.iloc[:, 0]) / dli_pairs.iloc[:, 0].replace(0.0, np.nan) * 100.0).replace([np.inf, -np.inf], np.nan).dropna()
    return {
        "status": "ok",
        "message": "Validation completed on finite overlapping PPFD samples.",
        "samples": int(len(paired)),
        "mae_ppfd_umol_m2_s": float(error.abs().mean()),
        "rmse_ppfd_umol_m2_s": float(np.sqrt(np.mean(error**2))),
        "bias_ppfd_umol_m2_s": float(error.mean()),
        "measured_dli_mol_m2_day": float(measured_dli.mean()),
        "modeled_dli_mol_m2_day": float(modeled_dli.mean()),
        "daily_dli_error_percent": float(dli_error_percent.mean()) if not dli_error_percent.empty else None,
        "validated_days": int(len(dli_error_percent)),
    }
