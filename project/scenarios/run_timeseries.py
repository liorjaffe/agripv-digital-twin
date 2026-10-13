"""Run the short-interval AgriPV simulation and daily summaries."""

from __future__ import annotations

import math
import logging

import pandas as pd
import pvlib

from project.config import MAX_TRACKER_TILT_DEG, load_runtime_config
from project.control.optimizer import optimize_tilt_schedule
from project.models.conversions import dli_from_timeseries, ghi_to_par
from project.models.conversions import energy_from_power_timeseries_kwh
from project.models.lettuce import simulate_growth_timeseries
from project.models.radiation import (
    crop_and_pv_irradiance,
    pvwatts_power,
    offset_tracker_orientation,
    solar_position_and_clearsky,
    tracker_orientation,
)

_DEFAULT_CONFIG = load_runtime_config()
MIN_DAYLIGHT_COVERAGE_FRACTION = 0.8


def run_timeseries_pipeline(
    weather: pd.DataFrame,
    location: pvlib.location.Location,
    *,
    axis_azimuth_deg: float = _DEFAULT_CONFIG.axis_azimuth_deg,
    gcr: float = _DEFAULT_CONFIG.gcr,
    height_m: float = _DEFAULT_CONFIG.height_m,
    pitch_m: float = _DEFAULT_CONFIG.pitch_m,
    pdc0_w: float = _DEFAULT_CONFIG.pdc0_w,
    gamma_pdc: float = _DEFAULT_CONFIG.gamma_pdc_per_c,
    pv_system_losses_percent: float = _DEFAULT_CONFIG.pv_system_losses_percent,
    pv_inverter_efficiency: float = _DEFAULT_CONFIG.pv_inverter_efficiency,
    temperature_c: float | pd.Series | None = None,
    dli_target_mol_m2_day: float = _DEFAULT_CONFIG.dli_target_mol_m2_day,
    dli_min_mol_m2_day: float = _DEFAULT_CONFIG.dli_min_mol_m2_day,
    dli_max_mol_m2_day: float = _DEFAULT_CONFIG.dli_max_mol_m2_day,
    pv_loss_weight: float = 1.0,  # CTRL-001; provisional configured objective weight.
    movement_weight: float = 0.0,  # CTRL-001; movement remains unweighted by default.
    control_interval: str = "15min",
    tilt_offsets_deg: tuple[float, ...] = (-55.0, -30.0, 0.0, 30.0, 55.0),
    max_gap_periods: int = 4,
    max_tilt_deg: float = _DEFAULT_CONFIG.max_tilt_deg,
    albedo: float = _DEFAULT_CONFIG.albedo,
    bifaciality: float = _DEFAULT_CONFIG.bifaciality,
    co2_ppm: float = _DEFAULT_CONFIG.co2_ppm,
    move_limit_deg_per_hour: float = _DEFAULT_CONFIG.move_limit_deg_per_hour,
    wind_stow_speed_ms: float = _DEFAULT_CONFIG.wind_stow_speed_ms,
    wind_stow_tracker_theta_deg: float = _DEFAULT_CONFIG.wind_stow_tracker_theta_deg,
    fallback_air_temp_c: float = _DEFAULT_CONFIG.fallback_air_temp_c,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Run radiation, control, DLI, PV, and growth over any weather duration.

    The controller makes a decision at ``control_interval`` while all outputs retain
    the same short time resolution. Daily summaries are derived afterward; the
    biomass state is never reset at midnight or month boundaries.

    ``weather`` may optionally include ``air_temp_c``, ``module_temp_c``,
    ``wind_speed_ms`` (or ``wind_speed``), and ``pressure_hpa`` columns, e.g. from
    :func:`project.io.field_data.to_canonical_frames`. When present these feed the
    PV thermal model, the wind-stow safety fallback, and refraction-corrected
    solar position instead of falling back to fixed defaults. During high wind,
    ``wind_stow_tracker_theta_deg`` is an absolute rotation angle and therefore
    overrides the sun-following baseline. The configured park angle must be
    verified against manufacturer guidance before hardware use.
    ``temperature_c`` takes precedence. If no finite air-temperature input is
    available, the explicitly configured ``fallback_air_temp_c`` scenario
    value is used and logged; it is included in the output with its source.

    Only up to ``max_gap_periods`` consecutive missing samples are bridged by
    interpolation; longer comms outages are left as ``NaN`` rather than invented,
    and ``daily['input_data_complete_fraction']`` reports how much of each day's
    input was actually measured (pre-interpolation) so low-quality days can be
    identified instead of silently trusted.
    """
    if weather.index.tz is None:
        raise ValueError("weather must use timezone-aware timestamps")
    if (
        not math.isfinite(wind_stow_tracker_theta_deg)
        or abs(wind_stow_tracker_theta_deg) > MAX_TRACKER_TILT_DEG
    ):
        raise ValueError(
            f"wind_stow_tracker_theta_deg must be finite and between "
            f"-{MAX_TRACKER_TILT_DEG:g} and {MAX_TRACKER_TILT_DEG:g} degrees"
        )
    if "ghi" in weather.columns:
        raw_ghi_presence = weather["ghi"].notna().astype(float)
        sample_deltas = weather.index.sort_values().to_series().diff().dt.total_seconds()
        native_intervals = sample_deltas[(sample_deltas > 0.0) & (sample_deltas <= 7200.0)]
        native_sample_seconds = (
            float(native_intervals.median())
            if not native_intervals.empty
            else pd.Timedelta(control_interval).total_seconds()
        )
    else:
        raw_ghi_presence = None
        native_sample_seconds = pd.Timedelta(control_interval).total_seconds()
    weather = weather.sort_index().resample(control_interval).mean()
    if raw_ghi_presence is not None:
        raw_ghi_presence = (
            raw_ghi_presence.resample(control_interval).max().reindex(weather.index).fillna(0.0)
        )
    weather = weather.interpolate(method="time", limit=max_gap_periods, limit_area="inside")
    required = {"ghi", "dhi", "dni"}
    missing = required.difference(weather.columns)
    if missing:
        raise ValueError(f"weather is missing columns: {sorted(missing)}")

    wind_column = next((column for column in ("wind_speed_ms", "wind_speed") if column in weather.columns), None)
    wind_speed_ms = weather[wind_column] if wind_column is not None else 1.0
    if temperature_c is None:
        if "air_temp_c" in weather.columns and weather["air_temp_c"].notna().any():
            temperature_c = weather["air_temp_c"]
            temperature_source = "weather.air_temp_c"
        else:
            temperature_c = fallback_air_temp_c
            temperature_source = "configured scenario fallback"
            logging.warning(
                "No finite air-temperature input is available; using configured "
                "fallback_air_temp_c=%.1f C",
                fallback_air_temp_c,
            )
    elif isinstance(temperature_c, pd.Series):
        temperature_c = temperature_c.reindex(weather.index).interpolate(
            method="time",
            limit=max_gap_periods,
            limit_area="inside",
        )
        temperature_source = "explicit temperature_c series"
        if not temperature_c.notna().any():
            raise ValueError("temperature_c series must contain at least one finite value")
    else:
        if not math.isfinite(float(temperature_c)):
            raise ValueError("temperature_c scalar must be finite")
        temperature_source = "explicit temperature_c scalar"
    if not math.isfinite(float(fallback_air_temp_c)) or not 5.0 <= fallback_air_temp_c <= 40.0:
        raise ValueError("fallback_air_temp_c must be finite and between 5 and 40 degrees C")
    if dli_min_mol_m2_day < 0.0 or dli_target_mol_m2_day <= 0.0:
        raise ValueError("DLI minimum must be non-negative and target must be positive")
    if dli_max_mol_m2_day < max(dli_target_mol_m2_day, dli_min_mol_m2_day):
        raise ValueError("DLI maximum must be greater than or equal to the effective DLI target")
    effective_dli_target = max(dli_target_mol_m2_day, dli_min_mol_m2_day)
    model_air_temperature = (
        temperature_c.reindex(weather.index)
        if isinstance(temperature_c, pd.Series)
        else pd.Series(float(temperature_c), index=weather.index)
    )
    module_temp_c = weather["module_temp_c"] if "module_temp_c" in weather.columns else None
    pressure_hpa = weather["pressure_hpa"] if "pressure_hpa" in weather.columns else None
    refraction_temp_c = weather["air_temp_c"] if "air_temp_c" in weather.columns else None

    solar, _ = solar_position_and_clearsky(
        location, weather.index, pressure_hpa=pressure_hpa, temp_air_c=refraction_temp_c
    )
    baseline = tracker_orientation(solar, axis_azimuth_deg, gcr, max_tilt_deg=max_tilt_deg)

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

    target_ppfd = pd.Series(0.0, index=weather.index, dtype=float)
    daylight_seconds = pd.Series(0.0, index=weather.index, dtype=float)
    interval_seconds = pd.Timedelta(control_interval).total_seconds()
    for day in pd.date_range(weather.index.min().normalize(), weather.index.max().normalize(), freq="D"):
        day_mask = weather.index.normalize() == day
        if not day_mask.any():
            continue
        daylight = solar.loc[day_mask, "apparent_zenith"] < 90.0
        total_daylight_seconds = float(daylight.astype(float).sum() * interval_seconds)
        if total_daylight_seconds <= 0.0:
            continue
        daylight_seconds.loc[day_mask] = daylight.astype(float) * interval_seconds
        target_ppfd.loc[day_mask] = effective_dli_target * 1_000_000.0 / total_daylight_seconds
    target_ppfd = target_ppfd.where(solar["apparent_zenith"] < 90.0, 0.0)
    max_move_deg = move_limit_deg_per_hour * (interval_seconds / 3600.0)
    candidate_offsets = {float(offset) for offset in tilt_offsets_deg}
    if max_move_deg > 0.0:
        min_offset = min(candidate_offsets)
        max_offset = max(candidate_offsets)
        step = max_move_deg
        value = 0.0
        while value <= max_offset:
            candidate_offsets.add(round(value, 6))
            value += step
        value = -step
        while value >= min_offset:
            candidate_offsets.add(round(value, 6))
            value -= step
        candidate_offsets.update((min_offset, max_offset))
    candidates = {}
    for offset in sorted(candidate_offsets):
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
            gamma_pdc,
            system_losses_percent=pv_system_losses_percent,
            inverter_efficiency=pv_inverter_efficiency,
            wind_speed_ms=wind_speed_ms,
            module_temp_c=module_temp_c,
        )
        evaluated["tracker_theta_deg"] = orientation["tracker_theta"]
        candidates[float(offset)] = evaluated

    schedule = optimize_tilt_schedule(
        candidates,
        target_ppfd,
        previous_tilt=0.0,
        max_move_deg=max_move_deg,
        pv_loss_weight=pv_loss_weight,
        movement_weight=movement_weight,
        dli_target_mol_m2_day=effective_dli_target,
        dli_max_mol_m2_day=dli_max_mol_m2_day,
        daylight_seconds=daylight_seconds,
    )
    selected = pd.DataFrame(index=weather.index)
    selected["tilt_offset_deg"] = schedule["tilt_deg"]
    for column in (
        "candidate_min_dli_mol_m2_day",
        "candidate_max_dli_mol_m2_day",
        "candidate_dli_minimum_reachable",
        "candidate_dli_ceiling_reachable",
        "candidate_dli_target_band_reachable",
        "dli_ceiling_enforced",
    ):
        selected[column] = schedule[column]
    selected["crop_ghi_w_m2"] = [candidates[tilt].loc[t, "crop_ghi_w_m2"] for t, tilt in schedule["tilt_deg"].items()]
    selected["crop_ppfd_umol_m2_s"] = [candidates[tilt].loc[t, "crop_ppfd_umol_m2_s"] for t, tilt in schedule["tilt_deg"].items()]
    selected["pv_power_w"] = [candidates[tilt].loc[t, "pv_power_w"] for t, tilt in schedule["tilt_deg"].items()]
    selected["tracker_theta_deg"] = [candidates[tilt].loc[t, "tracker_theta_deg"] for t, tilt in schedule["tilt_deg"].items()]
    if wind_column is not None:
        wind = weather[wind_column].reindex(weather.index).interpolate(
            method="time",
            limit=max_gap_periods,
            limit_area="inside",
        )
        stow_mask = wind.isna() | wind.ge(wind_stow_speed_ms)
        if stow_mask.any():
            stow_orientation = baseline.copy()
            stow_orientation["tracker_theta"] = pd.Series(
                wind_stow_tracker_theta_deg, index=weather.index
            )
            surface_orientation = pvlib.tracking.calc_surface_orientation(
                stow_orientation["tracker_theta"],
                axis_azimuth=axis_azimuth_deg,
            )
            stow_orientation[["surface_tilt", "surface_azimuth"]] = surface_orientation
            stowed = crop_and_pv_irradiance(
                solar,
                weather,
                stow_orientation,
                gcr=gcr,
                height_m=height_m,
                pitch_m=pitch_m,
                albedo=albedo,
                bifaciality=bifaciality,
            )
            stowed["pv_power_w"] = pvwatts_power(
                stowed["poa_global_w_m2"],
                temperature_c,
                pdc0_w,
                gamma_pdc,
                system_losses_percent=pv_system_losses_percent,
                inverter_efficiency=pv_inverter_efficiency,
                wind_speed_ms=wind_speed_ms,
                module_temp_c=module_temp_c,
            )
            selected.loc[stow_mask, "crop_ghi_w_m2"] = stowed.loc[stow_mask, "crop_ghi_w_m2"]
            selected.loc[stow_mask, "crop_ppfd_umol_m2_s"] = stowed.loc[stow_mask, "crop_ppfd_umol_m2_s"]
            selected.loc[stow_mask, "pv_power_w"] = stowed.loc[stow_mask, "pv_power_w"]
            selected.loc[stow_mask, "tracker_theta_deg"] = stow_orientation[
                "tracker_theta"
            ].loc[stow_mask]
            stow_offset = stow_orientation["tracker_theta"] - baseline["tracker_theta"]
            selected.loc[stow_mask, "tilt_offset_deg"] = stow_offset.loc[stow_mask].fillna(0.0)
    selected["target_ppfd_umol_m2_s"] = target_ppfd
    selected["model_air_temp_c"] = model_air_temperature
    selected["model_air_temp_source"] = temperature_source
    selected["dli_mol_m2_day"] = dli_from_timeseries(selected["crop_ppfd_umol_m2_s"]).reindex(selected.index.normalize()).to_numpy()
    growth = simulate_growth_timeseries(
        selected.index,
        ghi_to_par(selected["crop_ghi_w_m2"]),
        temperature_c,
        co2_ppm=co2_ppm,
    )
    selected = selected.join(growth[["total_dry_biomass"]])

    daily = pd.DataFrame(index=selected.resample("1D").first().index)
    daily["dli_mol_m2_day"] = dli_from_timeseries(
        selected["crop_ppfd_umol_m2_s"]
    ).reindex(daily.index)
    daily["pv_energy_kwh"] = energy_from_power_timeseries_kwh(
        selected["pv_power_w"]
    ).reindex(daily.index)
    daily["final_dry_biomass"] = selected["total_dry_biomass"].resample("1D").last()
    daily["model_air_temp_source"] = temperature_source
    for column in (
        "candidate_min_dli_mol_m2_day",
        "candidate_max_dli_mol_m2_day",
        "candidate_dli_minimum_reachable",
        "candidate_dli_ceiling_reachable",
        "candidate_dli_target_band_reachable",
        "dli_ceiling_enforced",
    ):
        daily[column] = selected[column].resample("1D").first()
    boolean_diagnostics = (
        "candidate_dli_minimum_reachable",
        "candidate_dli_ceiling_reachable",
        "candidate_dli_target_band_reachable",
        "dli_ceiling_enforced",
    )
    daily[list(boolean_diagnostics)] = daily[list(boolean_diagnostics)].astype(
        "boolean"
    )
    if raw_ghi_presence is not None:
        expected_times = pd.date_range(
            weather.index.min().normalize(),
            weather.index.max().normalize() + pd.Timedelta(days=1),
            freq=control_interval,
            inclusive="left",
        )
        expected_solar = location.get_solarposition(expected_times)
        expected_daylight_seconds = (
            (expected_solar["apparent_zenith"] < 90.0)
            .astype(float)
            .groupby(expected_times.normalize())
            .sum()
            * interval_seconds
        )
        expected_samples = (expected_daylight_seconds / native_sample_seconds).map(math.ceil)
        observed_daylight_samples = (
            raw_ghi_presence
            * (solar["apparent_zenith"] < 90.0).astype(float)
        ).groupby(weather.index.normalize()).sum()
        coverage = (
            observed_daylight_samples.reindex(daily.index, fill_value=0.0)
            / expected_samples.reindex(daily.index).replace(0.0, float("nan"))
        ).clip(upper=1.0)
        insufficient_coverage = coverage.lt(MIN_DAYLIGHT_COVERAGE_FRACTION) | coverage.isna()
        daily["daylight_coverage_fraction"] = coverage
        daily["daylight_coverage_sufficient"] = ~insufficient_coverage
        daily["input_data_complete_fraction"] = coverage
        daily.loc[insufficient_coverage, ["dli_mol_m2_day", "pv_energy_kwh"]] = float("nan")
        diagnostic_columns = (
            "candidate_min_dli_mol_m2_day",
            "candidate_max_dli_mol_m2_day",
        )
        daily.loc[insufficient_coverage, diagnostic_columns] = pd.NA
        daily.loc[insufficient_coverage, list(boolean_diagnostics)] = pd.NA
    return selected, daily
