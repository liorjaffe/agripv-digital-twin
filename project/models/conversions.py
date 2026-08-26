"""Radiation conversion utilities for the AgriPV project.

Conventions used here:
- GHI and POA are in W/m²
- PAR is in W/m² equivalent shortwave energy, not photon flux
- PPFD is in µmol photons / m² / s
- DLI is in mol photons / m² / day

This intentionally keeps the units explicit to avoid a common factor-of-two bug.
"""

from __future__ import annotations

from typing import Union

import numpy as np
import pandas as pd

PAR_FRACTION = 0.45
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

    Integration uses the actual elapsed seconds between samples, so irregular
    timestamps and later 15-minute field data are handled without assuming a
    fixed daylight length.
    """
    if not isinstance(ppfd_umol_m2_s.index, pd.DatetimeIndex):
        raise TypeError("PPFD series must use a DatetimeIndex")
    if ppfd_umol_m2_s.index.tz is None:
        raise ValueError("PPFD timestamps must be timezone-aware")
    ordered = ppfd_umol_m2_s.sort_index().astype(float).clip(lower=0.0).fillna(0.0)
    seconds = ordered.index.to_series().diff().dt.total_seconds().fillna(0.0)
    contribution = ordered * seconds / 1_000_000.0
    return contribution.groupby(ordered.index.normalize()).sum().rename("dli_mol_m2_day")
