from pathlib import Path
from datetime import datetime
import re
from zoneinfo import ZoneInfo

import pytest
import yaml

from project.config import load_runtime_config, make_site_location
from project.scenarios.generate_simple_report import DEFAULT_OUTPUT as SIMPLE_REPORT_OUTPUT
from project.scenarios.generate_model_explorer import DEFAULT_OUTPUT as MODEL_EXPLORER_OUTPUT


def test_runtime_configuration_matches_current_model_defaults():
    config = load_runtime_config()

    assert config.site_name == "Fotovoltaica UFSC / Florianopolis"
    assert config.latitude == -27.5949
    assert config.longitude == -48.5480
    assert config.timezone == "America/Sao_Paulo"
    assert config.altitude_m == 20.0
    assert config.fallback_air_temp_c == 26.0
    assert config.gcr == 0.3973
    assert config.dli_target_mol_m2_day == 14.0
    assert config.dli_min_mol_m2_day == 10.0
    assert config.dli_max_mol_m2_day == 18.0
    assert config.gamma_pdc_per_c == -0.004
    assert config.pv_inverter_efficiency == 0.96
    assert config.wind_stow_tracker_theta_deg == 0.0
    assert config.max_tilt_deg == 55.0
    assert config.bed_area_m2 == 11.25
    assert config.net_planted_area_m2 == pytest.approx(11.25)
    assert config.plants_per_bed == 96
    assert config.plant_density_per_m2 == pytest.approx(96 / 11.25)


def test_net_planted_area_fraction_scales_derived_area_and_plant_density(tmp_path: Path):
    source = Path(__file__).parents[1] / "config" / "site.yaml"
    config_path = tmp_path / "site.yaml"
    config_path.write_text(
        source.read_text(encoding="utf-8").replace(
            "net_planted_area_fraction: 1.0",
            "net_planted_area_fraction: 0.8",
        ),
        encoding="utf-8",
    )

    config = load_runtime_config(config_path)

    assert config.bed_area_m2 == 11.25
    assert config.net_planted_area_m2 == pytest.approx(9.0)
    assert config.plants_per_bed == 96
    assert config.plant_density_per_m2 == pytest.approx(96 / 9.0)


def test_site_location_uses_configured_coordinates_and_altitude():
    location = make_site_location()

    assert location.latitude == -27.5949
    assert location.longitude == -48.5480
    assert location.altitude == 20.0
    assert location.tz == "America/Sao_Paulo"


def test_dashboard_location_and_dli_defaults_stay_synced_with_site_yaml():
    root = Path(__file__).parents[2]
    settings = yaml.safe_load(
        (root / "project" / "config" / "site.yaml").read_text(encoding="utf-8")
    )
    dashboard = (root / "agripv_dashboard.html").read_text(encoding="utf-8")
    site_match = re.search(r"const SITE = \{([^}]+)\}", dashboard)
    assert site_match is not None
    dashboard_site = {
        key: float(value)
        for key, value in re.findall(
            r"(latitude|longitude|utcOffsetHours|altitudeM):\s*(-?\d+(?:\.\d+)?)",
            site_match.group(1),
        )
    }
    site = settings["site"]
    expected_utc_offset = (
        ZoneInfo(site["timezone"])
        .utcoffset(datetime(2026, 1, 15))
        .total_seconds()
        / 3600.0
    )
    assert dashboard_site["latitude"] == site["latitude"]
    assert dashboard_site["longitude"] == site["longitude"]
    assert dashboard_site["altitudeM"] == site["altitude_m"]
    assert dashboard_site["utcOffsetHours"] == expected_utc_offset

    target_match = re.search(
        r'<input id="target"[^>]*value="([0-9.]+)"', dashboard
    )
    assert target_match is not None
    assert float(target_match.group(1)) == settings["crop"]["dli_target_mol_m2_day"]


def test_invalid_site_geometry_is_rejected(tmp_path: Path):
    config = tmp_path / "site.yaml"
    config.write_text(
        """
site:
  name: Example
  latitude: 0
  longitude: 0
  timezone: UTC
  altitude_m: 0
pv:
  pdc0_w: 1000
  height_m: 2
  pitch_m: 10
  gcr: 1.2
  axis_azimuth_deg: 0
  max_tilt_deg: 55
  bifaciality: 0.7
  albedo: 0.2
crop:
  dli_target_mol_m2_day: 14
  co2_ppm_target: 420
cultivation:
  bed_length_m: 7.5
  bed_width_m: 1.5
  rows_per_bed: 24
  plants_per_row: 4
tracker:
  move_limit_deg_per_hour: 15
  wind_stow_speed_ms: 15
  wind_stow_tracker_theta_deg: 0
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="pv.gcr"):
        load_runtime_config(config)


def test_unknown_site_timezone_is_rejected(tmp_path: Path):
    config = tmp_path / "site.yaml"
    config.write_text(
        """
site:
  name: Example
  latitude: 0
  longitude: 0
  timezone: Not/A_Timezone
  altitude_m: 0
pv:
  pdc0_w: 1000
  height_m: 2
  pitch_m: 10
  gcr: 0.4
  axis_azimuth_deg: 0
  max_tilt_deg: 55
  bifaciality: 0.7
  albedo: 0.2
crop:
  dli_target_mol_m2_day: 14
  co2_ppm_target: 420
cultivation:
  bed_length_m: 7.5
  bed_width_m: 1.5
  rows_per_bed: 24
  plants_per_row: 4
tracker:
  move_limit_deg_per_hour: 15
  wind_stow_speed_ms: 15
  wind_stow_tracker_theta_deg: 0
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="site.timezone"):
        load_runtime_config(config)


def test_tracker_limit_above_installed_range_is_rejected(tmp_path: Path):
    config = tmp_path / "site.yaml"
    config.write_text(
        """
site:
  name: Example
  latitude: 0
  longitude: 0
  timezone: UTC
  altitude_m: 0
pv:
  pdc0_w: 1000
  height_m: 2
  pitch_m: 10
  gcr: 0.4
  axis_azimuth_deg: 0
  max_tilt_deg: 90
  bifaciality: 0.7
  albedo: 0.2
crop:
  dli_target_mol_m2_day: 14
  co2_ppm_target: 420
cultivation:
  bed_length_m: 7.5
  bed_width_m: 1.5
  rows_per_bed: 24
  plants_per_row: 4
tracker:
  move_limit_deg_per_hour: 15
  wind_stow_speed_ms: 15
  wind_stow_tracker_theta_deg: 0
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="pv.max_tilt_deg"):
        load_runtime_config(config)


def test_tracker_offset_above_installed_range_is_rejected():
    from project.io.commands import TrackerCommand

    with pytest.raises(ValueError, match="tilt_offset_deg"):
        TrackerCommand(
            timestamp="2026-08-26T12:00:00-03:00",
            subzone_id="CR1Kx",
            tilt_offset_deg=55.1,
        )


def test_bed_geometry_requires_positive_dimensions(tmp_path: Path):
    config = tmp_path / "site.yaml"
    config.write_text(
        """
site:
  name: Example
  latitude: 0
  longitude: 0
  timezone: UTC
  altitude_m: 0
pv:
  pdc0_w: 1000
  height_m: 2
  pitch_m: 10
  gcr: 0.4
  axis_azimuth_deg: 0
  max_tilt_deg: 55
  bifaciality: 0.7
  albedo: 0.2
crop:
  dli_target_mol_m2_day: 14
  co2_ppm_target: 420
cultivation:
  bed_length_m: 0
  bed_width_m: 1.5
  net_planted_area_fraction: 1.0
  rows_per_bed: 24
  plants_per_row: 4
tracker:
  move_limit_deg_per_hour: 15
  wind_stow_speed_ms: 15
  wind_stow_tracker_theta_deg: 0
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Bed length and width"):
        load_runtime_config(config)


def test_report_generators_have_distinct_default_outputs():
    assert MODEL_EXPLORER_OUTPUT != SIMPLE_REPORT_OUTPUT
