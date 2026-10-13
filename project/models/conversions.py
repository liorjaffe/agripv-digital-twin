"""Radiation conversion utilities for the AgriPV project.

Conventions used here:
- GHI and POA are in W/m²
- PAR is in W/m² equivalent shortwave energy, not photon flux
- PPFD is in µmol photons / m² / s
- DLI is in mol photons / m² / day

This intentionally keeps the units explicit to avoid a common factor-of-two bug.
"""

from __future__ import annotations

import math
from typing import Union

import numpy as np
import pandas as pd

# LIGHT-002: constant-fraction scenario approximation; site-specific spectral conversion is unavailable.
PAR_FRACTION = 0.45
# LIGHT-001: the handbook's exact edition/page remains unverified.
PPFD_PER_PAR_WM2 = 4.57
PA_PER_HPA = 100.0
SECONDS_PER_HOUR = 3600.0
DEFAULT_DAY_LENGTH_HOURS = 12.0


def _as_array(values):
    # Preserve Series/DataFrame so callers keep their index and can still chain
    # pandas-style methods (e.g. .clip(lower=...)); plain array-likes/scalars
    # still get a clean ndarray.
    if isinstance(values, (pd.Series, pd.DataFrame)):
        return values.astype(float)
    return np.asarray(values, dtype=float)


def ghi_to_par(ghi_wm2: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
    """Convert global horizontal irradiance (W/m²) to PAR-equivalent (W/m²).

    The common crop-physiology approximation uses 45% of shortwave energy as usable PAR.
    """
    return _as_array(ghi_wm2) * PAR_FRACTION


def par_to_ppfd(par_wm2: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
    """Convert PAR-equivalent irradiance to PPFD in µmol photons m^-2 s^-1.

    Approximate conversion: 1 W/m² of PAR ≈ 4.57 µmol photons m^-2 s^-1.
    """
    return _as_array(par_wm2) * PPFD_PER_PAR_WM2


def ppfd_to_par(ppfd_umol_m2_s: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
    """Inverse of :func:`par_to_ppfd`: PPFD (µmol m^-2 s^-1) -> PAR-equivalent (W/m²)."""
    return _as_array(ppfd_umol_m2_s) / PPFD_PER_PAR_WM2


def hpa_to_pa(pressure_hpa: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
    """Convert barometric pressure from hPa (field sensor units) to Pa (pvlib units).

    pvlib's solar position functions expect pressure in pascals; field stations
    and weather reports conventionally use hectopascals, so mixing them up
    silently is a realistic unit bug worth guarding against explicitly.
    """
    return _as_array(pressure_hpa) * PA_PER_HPA


def ppfd_to_dli(
    ppfd_umol_m2_s: Union[float, np.ndarray],
    day_length_hours: float = DEFAULT_DAY_LENGTH_HOURS,
) -> Union[float, np.ndarray]:
    """Convert PPFD to DLI in mol photons m^-2 day^-1.

    DLI = PPFD * seconds_per_hour * day_length_hours / 1_000_000.

    The conversion is intentionally tied to a representative daylight window; for
    the UFSC pilot, 12 h is a reasonable default for summer/winter daily light
    integration unless a site-specific day length is provided.
    """
    ppfd = _as_array(ppfd_umol_m2_s)
    return ppfd * SECONDS_PER_HOUR * day_length_hours / 1_000_000.0


def dli_from_ghi(
    ghi_wm2: Union[float, np.ndarray],
    day_length_hours: float = DEFAULT_DAY_LENGTH_HOURS,
) -> Union[float, np.ndarray]:
    """Convenience function: GHI W/m² -> DLI mol photons m^-2 day^-1.

    This calculates the DLI implied by a constant GHI over the specified daylight
    window. For example, 1000 W/m² over 12 h gives roughly 88.8 mol m^-2 day^-1.
    """
    par = ghi_to_par(ghi_wm2)
    ppfd = par_to_ppfd(par)
    return ppfd_to_dli(ppfd, day_length_hours=day_length_hours)


def dli_from_timeseries(ppfd_umol_m2_s: pd.Series) -> pd.Series:
    """Integrate a timezone-aware PPFD series into daily DLI values.

    Adjacent finite samples are integrated trapezoidally over their actual
    elapsed time. Intervals containing missing data and intervals crossing
    local midnight are excluded rather than treated as zero-light periods.
    """
    return _daily_trapezoid_integral(ppfd_umol_m2_s, scale=1_000_000.0).rename(
        "dli_mol_m2_day"
    )


def dli_interval_contribution(
    previous_ppfd_umol_m2_s: float | None,
    current_ppfd_umol_m2_s: float,
    elapsed_seconds: float | None,
) -> float | None:
    """Return one finite adjacent-sample trapezoid contribution in mol/m²."""
    if (
        previous_ppfd_umol_m2_s is None
        or elapsed_seconds is None
        or not math.isfinite(previous_ppfd_umol_m2_s)
        or not math.isfinite(current_ppfd_umol_m2_s)
        or not math.isfinite(elapsed_seconds)
        or elapsed_seconds <= 0.0
    ):
        return None
    previous = max(0.0, previous_ppfd_umol_m2_s)
    current = max(0.0, current_ppfd_umol_m2_s)
    return (previous + current) * 0.5 * elapsed_seconds / 1_000_000.0


def energy_from_power_timeseries_kwh(power_w: pd.Series) -> pd.Series:
    """Integrate finite adjacent power samples into daily AC/DC energy in kWh."""
    return _daily_trapezoid_integral(power_w, scale=3_600_000.0).rename(
        "pv_energy_kwh"
    )


def _daily_trapezoid_integral(values: pd.Series, *, scale: float) -> pd.Series:
    if not isinstance(values.index, pd.DatetimeIndex):
        raise TypeError("Time-series values must use a DatetimeIndex")
    if values.index.tz is None:
        raise ValueError("Time-series timestamps must be timezone-aware")

    ordered = (
        values.sort_index()
        .astype(float)
        .replace([np.inf, -np.inf], np.nan)
        .clip(lower=0.0)
    )
    elapsed_seconds = ordered.index.to_series().diff().dt.total_seconds()
    previous_values = ordered.shift(1)
    same_local_day = pd.Series(
        ordered.index.normalize(), index=ordered.index
    ).eq(pd.Series(ordered.index.normalize(), index=ordered.index).shift(1))
    valid_intervals = (
        ordered.notna()
        & previous_values.notna()
        & same_local_day
        & elapsed_seconds.gt(0.0)
    )
    if scale == 1_000_000.0:
        contributions = pd.Series(
            [
                dli_interval_contribution(previous, current, elapsed)
                if same_day and valid
                else None
                for previous, current, elapsed, same_day, valid in zip(
                    previous_values,
                    ordered,
                    elapsed_seconds,
                    same_local_day,
                    valid_intervals,
                )
            ],
            index=ordered.index,
            dtype=float,
        )
    else:
        contributions = (
            (ordered + previous_values) / 2.0 * elapsed_seconds / scale
        ).where(valid_intervals)
    daily = contributions.groupby(ordered.index.normalize()).sum(min_count=1)
    return daily
