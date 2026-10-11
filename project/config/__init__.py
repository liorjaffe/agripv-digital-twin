"""Load the site settings used by the simulation pipeline."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import math
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import pvlib
import yaml

DEFAULT_CONFIG_PATH = Path(__file__).with_name("site.yaml")
MAX_TRACKER_TILT_DEG = 55.0


@dataclass(frozen=True)
class RuntimeConfig:
    site_name: str
    latitude: float
    longitude: float
    timezone: str
    altitude_m: float
    pdc0_w: float
    height_m: float
    pitch_m: float
    gcr: float
    axis_azimuth_deg: float
    max_tilt_deg: float
    bifaciality: float
    albedo: float
    bed_length_m: float
    bed_width_m: float
    rows_per_bed: int
    plants_per_row: int
    dli_target_mol_m2_day: float
    co2_ppm: float
    move_limit_deg_per_hour: float
    wind_stow_speed_ms: float
    fallback_tilt_offset_deg: float

    @property
    def bed_area_m2(self) -> float:
        return self.bed_length_m * self.bed_width_m

    @property
    def plants_per_bed(self) -> int:
        return self.rows_per_bed * self.plants_per_row

    @property
    def plant_density_per_m2(self) -> float:
        return self.plants_per_bed / self.bed_area_m2

    def make_location(self) -> pvlib.location.Location:
        return pvlib.location.Location(
            latitude=self.latitude,
            longitude=self.longitude,
            tz=self.timezone,
            altitude=self.altitude_m,
            name=self.site_name,
        )


def _section(settings: object, name: str, path: Path) -> Mapping[str, object]:
    if not isinstance(settings, Mapping) or name not in settings:
        raise ValueError(f"Configuration {path} must contain a '{name}' mapping")
    section = settings[name]
    if not isinstance(section, Mapping):
        raise ValueError(f"Configuration section '{name}' in {path} must be a mapping")
    return section


def _number(section: Mapping[str, object], key: str, path: Path) -> float:
    value = section.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"Configuration value '{key}' in {path} must be a finite number")
    return float(value)


def load_runtime_config(path: str | Path = DEFAULT_CONFIG_PATH) -> RuntimeConfig:
    """Read and validate the settings that directly affect model calculations."""
    config_path = Path(path)
    with config_path.open(encoding="utf-8") as source:
        raw = yaml.safe_load(source)

    site = _section(raw, "site", config_path)
    pv = _section(raw, "pv", config_path)
    crop = _section(raw, "crop", config_path)
    cultivation = _section(raw, "cultivation", config_path)
    tracker = _section(raw, "tracker", config_path)

    site_name = site.get("name")
    timezone = site.get("timezone")
    if not isinstance(site_name, str) or not site_name.strip():
        raise ValueError(f"Configuration value 'site.name' in {config_path} must be a non-empty string")
    if not isinstance(timezone, str) or not timezone.strip():
        raise ValueError(f"Configuration value 'site.timezone' in {config_path} must be a non-empty string")
    try:
        ZoneInfo(timezone)
    except ZoneInfoNotFoundError as error:
        raise ValueError(f"Configuration value 'site.timezone' in {config_path} is not a known timezone") from error

    rows_per_bed = _number(cultivation, "rows_per_bed", config_path)
    plants_per_row = _number(cultivation, "plants_per_row", config_path)
    if not rows_per_bed.is_integer() or not plants_per_row.is_integer():
        raise ValueError(f"Bed row and plant counts in {config_path} must be whole numbers")

    values = RuntimeConfig(
        site_name=site_name,
        latitude=_number(site, "latitude", config_path),
        longitude=_number(site, "longitude", config_path),
        timezone=timezone,
        altitude_m=_number(site, "altitude_m", config_path),
        pdc0_w=_number(pv, "pdc0_w", config_path),
        height_m=_number(pv, "height_m", config_path),
        pitch_m=_number(pv, "pitch_m", config_path),
        gcr=_number(pv, "gcr", config_path),
        axis_azimuth_deg=_number(pv, "axis_azimuth_deg", config_path),
        max_tilt_deg=_number(pv, "max_tilt_deg", config_path),
        bifaciality=_number(pv, "bifaciality", config_path),
        albedo=_number(pv, "albedo", config_path),
        bed_length_m=_number(cultivation, "bed_length_m", config_path),
        bed_width_m=_number(cultivation, "bed_width_m", config_path),
        rows_per_bed=int(rows_per_bed),
        plants_per_row=int(plants_per_row),
        dli_target_mol_m2_day=_number(crop, "dli_target_mol_m2_day", config_path),
        co2_ppm=_number(crop, "co2_ppm_target", config_path),
        move_limit_deg_per_hour=_number(tracker, "move_limit_deg_per_hour", config_path),
        wind_stow_speed_ms=_number(tracker, "wind_stow_speed_ms", config_path),
        fallback_tilt_offset_deg=_number(tracker, "fallback_tilt_offset_deg", config_path),
    )

    if not -90.0 <= values.latitude <= 90.0:
        raise ValueError(f"Configuration value 'site.latitude' in {config_path} must be between -90 and 90")
    if not -180.0 <= values.longitude <= 180.0:
        raise ValueError(f"Configuration value 'site.longitude' in {config_path} must be between -180 and 180")
    if values.pdc0_w <= 0.0 or values.height_m <= 0.0 or values.pitch_m <= 0.0:
        raise ValueError(f"PV power, height, and pitch in {config_path} must be greater than zero")
    if not 0.0 < values.gcr <= 1.0:
        raise ValueError(f"Configuration value 'pv.gcr' in {config_path} must be in (0, 1]")
    if not 0.0 <= values.albedo <= 1.0 or not 0.0 <= values.bifaciality <= 1.0:
        raise ValueError(f"PV albedo and bifaciality in {config_path} must be between 0 and 1")
    if values.bed_length_m <= 0.0 or values.bed_width_m <= 0.0:
        raise ValueError(f"Bed length and width in {config_path} must be greater than zero")
    if values.rows_per_bed <= 0 or values.plants_per_row <= 0:
        raise ValueError(f"Bed row and plant counts in {config_path} must be greater than zero")
    if not 0.0 < values.max_tilt_deg <= MAX_TRACKER_TILT_DEG:
        raise ValueError(
            f"Configuration value 'pv.max_tilt_deg' in {config_path} must be in "
            f"(0, {MAX_TRACKER_TILT_DEG:g}] for this tracker"
        )
    if values.dli_target_mol_m2_day <= 0.0 or values.co2_ppm <= 0.0:
        raise ValueError(f"Crop DLI target and CO2 concentration in {config_path} must be greater than zero")
    if values.move_limit_deg_per_hour < 0.0 or values.wind_stow_speed_ms < 0.0:
        raise ValueError(f"Tracker movement and wind limits in {config_path} must not be negative")
    if not -MAX_TRACKER_TILT_DEG <= values.fallback_tilt_offset_deg <= MAX_TRACKER_TILT_DEG:
        raise ValueError(
            f"Tracker fallback offset in {config_path} must be between "
            f"-{MAX_TRACKER_TILT_DEG:g} and {MAX_TRACKER_TILT_DEG:g} degrees"
        )
    return values


def make_site_location(path: str | Path = DEFAULT_CONFIG_PATH) -> pvlib.location.Location:
    """Create a pvlib site location from the shared runtime configuration."""
    return load_runtime_config(path).make_location()


__all__ = [
    "DEFAULT_CONFIG_PATH",
    "MAX_TRACKER_TILT_DEG",
    "RuntimeConfig",
    "load_runtime_config",
    "make_site_location",
]
