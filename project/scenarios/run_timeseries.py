"""Run the short-interval AgriPV simulation and daily summaries."""

from __future__ import annotations

import math

import pandas as pd
import pvlib

from project.config import MAX_TRACKER_TILT_DEG, load_runtime_config
from project.control.optimizer import optimize_tilt_schedule
from project.control.smoothing import apply_safety
from project.models.conversions import dli_from_timeseries, ghi_to_par
from project.models.lettuce import simulate_growth_timeseries
from project.models.radiation import (
    crop_and_pv_irradiance,
    pvwatts_power,
    offset_tracker_orientation,
    solar_position_and_clearsky,
    tracker_orientation,
)

_DEFAULT_CONFIG = load_runtime_config()


def run_timeseries_pipeline(
    weather: pd.DataFrame,
    location: pvlib.location.Location,
    *,
    axis_azimuth_deg: float = _DEFAULT_CONFIG.axis_azimuth_deg,
    gcr: float = _DEFAULT_CONFIG.gcr,
    height_m: float = _DEFAULT_CONFIG.height_m,
    pitch_m: float = _DEFAULT_CONFIG.pitch_m,
    pdc0_w: float = _DEFAULT_CONFIG.pdc0_w,
    temperature_c: float | pd.Series | None = None,
    dli_target_mol_m2_day: float = _DEFAULT_CONFIG.dli_target_mol_m2_day,
    control_interval: str = "15min",
    tilt_offsets_deg: tuple[float, ...] = (-55.0, -30.0, 0.0, 30.0, 55.0),
    max_gap_periods: int = 4,
    max_tilt_deg: float = _DEFAULT_CONFIG.max_tilt_deg,
    albedo: float = _DEFAULT_CONFIG.albedo,
    bifaciality: float = _DEFAULT_CONFIG.bifaciality,
    co2_ppm: float = _DEFAULT_CONFIG.co2_ppm,
    move_limit_deg_per_hour: float = _DEFAULT_CONFIG.move_limit_deg_per_hour,
    wind_stow_speed_ms: float = _DEFAULT_CONFIG.wind_stow_speed_ms,
    fallback_tilt_offset_deg: float = _DEFAULT_CONFIG.fallback_tilt_offset_deg,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Run radiation, control, DLI, PV, and growth over any weather duration.

    The controller makes a decision at ``control_interval`` while all outputs retain
    the same short time resolution. Daily summaries are derived afterward; the
    biomass state is never reset at midnight or month boundaries.

    ``weather`` may optionally include ``air_temp_c``, ``module_temp_c``,
    ``wind_speed_ms`` (or ``wind_speed``), and ``pressure_hpa`` columns, e.g. from
    :func:`project.io.field_data.to_canonical_frames`. When present these feed the
    PV thermal model, the wind-stow safety fallback, and refraction-corrected
    solar position instead of falling back to fixed defaults. ``temperature_c``
    (module thermal input) still takes precedence when explicitly provided.

    Only up to ``max_gap_periods`` consecutive missing samples are bridged by
    interpolation; longer comms outages are left as ``NaN`` rather than invented,
    and ``daily['input_data_complete_fraction']`` reports how much of each day's
    input was actually measured (pre-interpolation) so low-quality days can be
    identified instead of silently trusted.
    """
    if weather.index.tz is None:
        raise ValueError("weather must use timezone-aware timestamps")
    raw_valid_fraction = weather["ghi"].notna().astype(float) if "ghi" in weather.columns else None
    weather = weather.sort_index().resample(control_interval).mean()
    weather = weather.interpolate(method="time", limit=max_gap_periods, limit_area="inside")
    required = {"ghi", "dhi", "dni"}
    missing = required.difference(weather.columns)
    if missing:
        raise ValueError(f"weather is missing columns: {sorted(missing)}")

    wind_column = next((column for column in ("wind_speed_ms", "wind_speed") if column in weather.columns), None)
    wind_speed_ms = weather[wind_column] if wind_column is not None else 1.0
    if temperature_c is None:
        temperature_c = weather["air_temp_c"] if "air_temp_c" in weather.columns else 26.0
    module_temp_c = weather["module_temp_c"] if "module_temp_c" in weather.columns else None
    pressure_hpa = weather["pressure_hpa"] if "pressure_hpa" in weather.columns else None
    refraction_temp_c = weather["air_temp_c"] if "air_temp_c" in weather.columns else None

    solar, _ = solar_position_and_clearsky(
        location, weather.index, pressure_hpa=pressure_hpa, temp_air_c=refraction_temp_c
    )
    baseline = tracker_orientation(solar, axis_azimuth_deg, gcr, max_tilt_deg=max_tilt_deg)

    candidates = {}
    if not tilt_offsets_deg:
        raise ValueError("tilt_offsets_deg must contain at least one candidate")
    if any(
        not math.isfinite(offset) or abs(offset) > MAX_TRACKER_TILT_DEG
        for offset in tilt_offsets_deg
    ):
        raise ValueError(
            f"tilt_offsets_deg candidates must be finite and between "
            f"-{MAX_TRACKER_TILT_DEG:g} and {MAX_TRACKER_TILT_DEG:g} degrees"
        )

    for offset in tilt_offsets_deg:
        orientation = offset_tracker_orientation(
            baseline,
            offset,
            axis_azimuth_deg,
            max_tilt_deg=max_tilt_deg,
        )
        evaluated = crop_and_pv_irradiance(
            solar,
            weather,
            orientation,
            gcr=gcr,
            height_m=height_m,
            pitch_m=pitch_m,
            albedo=albedo,
            bifaciality=bifaciality,
        )
        evaluated["pv_power_w"] = pvwatts_power(
            evaluated["poa_global_w_m2"],
            temperature_c,
            pdc0_w,
            wind_speed_ms=wind_speed_ms,
            module_temp_c=module_temp_c,
        )
        candidates[float(offset)] = evaluated

    target_ppfd = pd.Series(0.0, index=weather.index, dtype=float)
    for day in pd.date_range(weather.index.min().normalize(), weather.index.max().normalize(), freq="D"):
        day_mask = weather.index.normalize() == day
        if not day_mask.any():
            continue
        daylight = solar.loc[day_mask, "apparent_zenith"] < 90.0
        daylight_seconds = float(daylight.astype(float).sum() * pd.Timedelta(control_interval).total_seconds())
        if daylight_seconds <= 0.0:
            continue
        target_ppfd.loc[day_mask] = dli_target_mol_m2_day * 1_000_000.0 / daylight_seconds
    target_ppfd = target_ppfd.where(solar["apparent_zenith"] < 90.0, 0.0)
    schedule = optimize_tilt_schedule(
        candidates,
        target_ppfd,
        previous_tilt=0.0,
        max_move_deg=move_limit_deg_per_hour * (pd.Timedelta(control_interval).total_seconds() / 3600.0),
        pv_loss_weight=0.001,
        movement_weight=0.05,
    )
    if wind_column is not None:
        schedule["tilt_deg"] = apply_safety(
            schedule["tilt_deg"],
            weather[wind_column],
            wind_stow_speed_ms=wind_stow_speed_ms,
            fallback=fallback_tilt_offset_deg,
        )

    selected = pd.DataFrame(index=weather.index)
    selected["tilt_offset_deg"] = schedule["tilt_deg"]
    selected["crop_ghi_w_m2"] = [candidates[tilt].loc[t, "crop_ghi_w_m2"] for t, tilt in schedule["tilt_deg"].items()]
    selected["crop_ppfd_umol_m2_s"] = [candidates[tilt].loc[t, "crop_ppfd_umol_m2_s"] for t, tilt in schedule["tilt_deg"].items()]
    selected["pv_power_w"] = [candidates[tilt].loc[t, "pv_power_w"] for t, tilt in schedule["tilt_deg"].items()]
    selected["target_ppfd_umol_m2_s"] = target_ppfd
    selected["dli_mol_m2_day"] = dli_from_timeseries(selected["crop_ppfd_umol_m2_s"]).reindex(selected.index.normalize()).to_numpy()
    growth = simulate_growth_timeseries(
        selected.index,
        ghi_to_par(selected["crop_ghi_w_m2"]),
        temperature_c,
        co2_ppm=co2_ppm,
    )
    selected = selected.join(growth[["total_dry_biomass"]])

    daily = pd.DataFrame(index=selected.resample("1D").first().index)
    daily["dli_mol_m2_day"] = dli_from_timeseries(selected["crop_ppfd_umol_m2_s"])
    daily["pv_energy_kwh"] = selected["pv_power_w"].resample("1D").sum() * pd.Timedelta(control_interval).total_seconds() / 3_600_000.0
    daily["final_dry_biomass"] = selected["total_dry_biomass"].resample("1D").last()
    if raw_valid_fraction is not None:
        daily["input_data_complete_fraction"] = raw_valid_fraction.resample("1D").mean().reindex(daily.index)
    return selected, daily
