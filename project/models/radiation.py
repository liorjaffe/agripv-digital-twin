"""pvlib radiation model for one agrivoltaic subzone."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pvlib

from .conversions import ghi_to_par, hpa_to_pa, par_to_ppfd


def solar_position_and_clearsky(
    location: pvlib.location.Location,
    times: pd.DatetimeIndex,
    *,
    pressure_hpa: pd.Series | float | None = None,
    temp_air_c: pd.Series | float | None = None,
):
    """Return solar position and Ineichen clear-sky weather for timezone-aware times.

    ``pressure_hpa`` and ``temp_air_c`` are optional measured values used only to
    refraction-correct the apparent solar position (pvlib expects pressure in
    pascals, so hPa readings are converted here). Without them, pvlib falls
    back to the location's altitude-derived standard pressure and a 12 degC
    default, which is a reasonable but less accurate stand-in.
    """
    if times.tz is None:
        raise ValueError("times must be timezone-aware")
    solarposition_kwargs = {}
    if pressure_hpa is not None:
        solarposition_kwargs["pressure"] = hpa_to_pa(pressure_hpa)
    if temp_air_c is not None:
        solarposition_kwargs["temperature"] = temp_air_c
    solar_position = location.get_solarposition(times, **solarposition_kwargs)
    clearsky = location.get_clearsky(times, model="ineichen")
    return solar_position, clearsky


def estimate_ghi_dni_dhi_from_ppfd(
    location: pvlib.location.Location,
    times: pd.DatetimeIndex,
    measured_ppfd_umol_m2_s: pd.Series,
    *,
    solar_position: pd.DataFrame | None = None,
    clearsky_ghi: pd.Series | None = None,
    max_clear_sky_index: float = 1.2,
) -> pd.DataFrame:
    """Reconstruct ghi/dni/dhi from a measured quantum PAR (PPFD) sensor.

    Many field stations, including this pilot, only have quantum PAR sensors
    and no pyranometer, so ghi/dni/dhi are never directly measured. This
    estimates them physically: Ineichen clear-sky GHI is converted into the
    same PPFD units the sensor reports (using the project's PAR-fraction and
    quantum-conversion constants), compared against the measured PPFD to get a
    clear-sky index, and that index scales the clear-sky GHI back up or down.
    The resulting GHI is split into DNI/DHI with the Erbs decomposition model.

    This is an estimate, not a measurement: it assumes the diffuse/direct split
    implied by the Erbs model matches the true sky for the implied clearness,
    which is a reasonable average behavior but will not capture every cloud
    geometry. Downstream results derived from it should be labeled accordingly.
    """
    if times.tz is None:
        raise ValueError("times must be timezone-aware")
    if solar_position is None:
        solar_position = location.get_solarposition(times)
    if clearsky_ghi is None:
        clearsky_ghi = location.get_clearsky(times, model="ineichen")["ghi"]

    clearsky_ppfd = par_to_ppfd(ghi_to_par(clearsky_ghi)).clip(lower=1e-6)
    measured = measured_ppfd_umol_m2_s.reindex(times).clip(lower=0.0)
    clear_sky_index = (measured / clearsky_ppfd).clip(lower=0.0, upper=max_clear_sky_index)
    # Below the horizon the clear-sky reference is ~0, so the ratio is meaningless.
    clear_sky_index = clear_sky_index.where(solar_position["apparent_zenith"] < 87.0, 0.0)

    ghi_est = (clear_sky_index * clearsky_ghi).clip(lower=0.0)
    decomposed = pvlib.irradiance.erbs(ghi_est, solar_position["zenith"], times)
    return pd.DataFrame(
        {
            "ghi": ghi_est,
            "dni": decomposed["dni"].clip(lower=0.0),
            "dhi": decomposed["dhi"].clip(lower=0.0),
            "clear_sky_index": clear_sky_index,
        },
        index=times,
    )


def tracker_orientation(solar_position: pd.DataFrame, axis_azimuth_deg: float, gcr: float, max_tilt_deg: float = 90.0, backtrack: bool = True) -> pd.DataFrame:
    """Calculate pvlib single-axis tracker orientation."""
    return pvlib.tracking.singleaxis(
        apparent_zenith=solar_position["apparent_zenith"],
        apparent_azimuth=solar_position["azimuth"],
        axis_azimuth=axis_azimuth_deg,
        max_angle=max_tilt_deg,
        backtrack=backtrack,
        gcr=gcr,
    )


def crop_and_pv_irradiance(
    solar_position: pd.DataFrame,
    weather: pd.DataFrame,
    orientation: pd.DataFrame,
    *,
    gcr: float,
    height_m: float,
    pitch_m: float,
    albedo: float = 0.18,
    bifaciality: float = 0.7,
) -> pd.DataFrame:
    """Calculate crop-level ground irradiance and module POA irradiance.

    ``weather`` must contain ``ghi``, ``dhi`` and ``dni``. The returned frame is
    indexed like the inputs and is suitable for DLI integration or PV calculations.
    """
    required = {"ghi", "dhi", "dni"}
    missing = required.difference(weather.columns)
    if missing:
        raise ValueError(f"weather is missing columns: {sorted(missing)}")

    times = solar_position.index
    dni_extra = pvlib.irradiance.get_extra_radiation(times)
    sheds = pvlib.bifacial.infinite_sheds.get_irradiance(
        surface_tilt=orientation["surface_tilt"],
        surface_azimuth=orientation["surface_azimuth"],
        solar_zenith=solar_position["apparent_zenith"],
        solar_azimuth=solar_position["azimuth"],
        gcr=gcr,
        height=height_m,
        pitch=pitch_m,
        ghi=weather["ghi"],
        dhi=weather["dhi"],
        dni=weather["dni"],
        albedo=albedo,
        model="haydavies",
        dni_extra=dni_extra,
        bifaciality=bifaciality,
    )

    view_factor = pvlib.bifacial.utils.vf_ground_sky_2d_integ(
        surface_tilt=orientation["surface_tilt"], gcr=gcr, height=height_m, pitch=pitch_m
    )
    unshaded = pvlib.bifacial.utils._unshaded_ground_fraction(
        surface_tilt=orientation["surface_tilt"],
        surface_azimuth=orientation["surface_azimuth"],
        solar_zenith=solar_position["apparent_zenith"],
        solar_azimuth=solar_position["azimuth"],
        gcr=gcr,
    )
    cosine = np.maximum(np.cos(np.radians(solar_position["apparent_zenith"])), 0.0)
    crop_ghi = unshaded * weather["dni"] * cosine + view_factor * weather["dhi"]
    crop_ghi = crop_ghi.where(solar_position["apparent_zenith"] < 90.0, 0.0).fillna(0.0).clip(lower=0.0)
    crop_ppfd = par_to_ppfd(ghi_to_par(crop_ghi))

    # pvlib's tracker model leaves tilt/azimuth (and thus poa_global) undefined
    # (NaN) at night, since no tracker angle is meaningful without a sun
    # position. Physically the module receives zero irradiance then, so this
    # is forced to 0 here rather than left as NaN, matching crop_ghi above and
    # keeping downstream PV power well-defined (0 W) instead of NaN at night.
    poa_global = sheds["poa_global"].where(solar_position["apparent_zenith"] < 90.0, 0.0).fillna(0.0).clip(lower=0.0)

    return pd.DataFrame(
        {
            "crop_ghi_w_m2": crop_ghi,
            "crop_ppfd_umol_m2_s": crop_ppfd,
            "poa_global_w_m2": poa_global,
        },
        index=times,
    )


def pvwatts_power(
    irradiance: pd.Series,
    temp_air_c: pd.Series | float,
    pdc0_w: float,
    gamma_pdc: float = -0.004,
    *,
    wind_speed_ms: pd.Series | float = 1.0,
    module_temp_c: pd.Series | float | None = None,
) -> pd.Series:
    """Estimate DC power from POA using pvlib PVWatts.

    Cell temperature comes from a measured ``module_temp_c`` sensor when one is
    given (the most physically direct option, since it skips modeling error
    entirely), otherwise from the Faiman model driven by ``temp_air_c`` and
    ``wind_speed_ms``. Faiman's own default wind speed is a fixed 1 m/s, which
    understates cooling on a windy day, so real measured wind should be passed
    through whenever it is available.
    """
    if module_temp_c is not None:
        temp_cell = module_temp_c
    else:
        temp_cell = pvlib.temperature.faiman(poa_global=irradiance, temp_air=temp_air_c, wind_speed=wind_speed_ms)
    power = pvlib.pvsystem.pvwatts_dc(
        effective_irradiance=irradiance, temp_cell=temp_cell, pdc0=pdc0_w, gamma_pdc=gamma_pdc
    )
    return power.clip(lower=0.0, upper=pdc0_w)
