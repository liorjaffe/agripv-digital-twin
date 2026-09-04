"""Tests for real field-data ingestion: column mapping, QC bounds, and GHI/DNI/DHI
reconstruction from a measured PAR (PPFD) sensor when no pyranometer exists.

The bad-value patterns used here (huge negative temperature, an out-of-range PAR
spike, a negative wind reading, and a pressure dropout/spike) mirror what is
actually visible in the station's Grafana export screenshots.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pvlib
import pytest

from project.io.field_data import classify_column, classify_columns, raw_probe_quality_report, to_canonical_frames
from project.io.ingestion import load_field_export
from project.io.commands import DryRunCommandSink
from project.io.service import process_field_export, send_manual_tracker_override
from project.models.radiation import estimate_ghi_dni_dhi_from_ppfd
from project.qc.cleaning import (
    AIR_TEMP_C,
    MODULE_TEMP_C,
    PPFD_UMOL_M2_S,
    PRESSURE_HPA,
    RELATIVE_HUMIDITY_PCT,
    WIND_SPEED_MS,
    clean_field_frame,
    quality_report,
)
from project.validation.validate_radiation import validate_radiation

SITE = pvlib.location.Location(
    latitude=-27.5949, longitude=-48.5480, tz="America/Sao_Paulo", altitude=20.0
)


def _daily_index(days: int = 2, freq: str = "15min") -> pd.DatetimeIndex:
    return pd.date_range("2026-01-15", periods=int(days * 24 * 60 / 15), freq=freq, tz="America/Sao_Paulo")


def test_classify_column_recognizes_all_observed_logger_naming_variants():
    cases = {
        "CR1Kx-TempMod1": ("CR1Kx", MODULE_TEMP_C),
        "CR1Kx-TempMod4": ("CR1Kx", MODULE_TEMP_C),
        "CR1Kx-TempAr1": ("CR1Kx", AIR_TEMP_C),
        "CR310-04-TempMod0": ("CR310-04", MODULE_TEMP_C),
        "CR310_04-TempAr": ("CR310-04", AIR_TEMP_C),
        "CR1Kx-Par1": ("CR1Kx", PPFD_UMOL_M2_S),
        "CR310-02-Par": ("CR310-02", PPFD_UMOL_M2_S),
        "CR1Kx-RH2": ("CR1Kx", RELATIVE_HUMIDITY_PCT),
        "CR310_01-RA": ("CR310-01", "precipitation_mm"),
        "CR310_01_-RA": ("CR310-01", "precipitation_mm"),
        "CR310_01-Ws": ("CR310-01", WIND_SPEED_MS),
        "CR310_01_-Ws": ("CR310-01", WIND_SPEED_MS),
        "CR310_01-Pressure": ("CR310-01", PRESSURE_HPA),
        "CR310_01_-Pressure": ("CR310-01", PRESSURE_HPA),
    }
    for column, expected in cases.items():
        assert classify_column(column) == expected, column


def test_classify_columns_groups_duplicate_wind_channel_into_one_subzone():
    mapping = classify_columns(["CR310_01-Ws", "CR310_01_-Ws", "TIMESTAMP", "RECORD"])
    assert set(mapping.subzones) == {"CR310-01"}
    assert sorted(mapping.subzones["CR310-01"][WIND_SPEED_MS]) == ["CR310_01-Ws", "CR310_01_-Ws"]
    assert set(mapping.unmapped_columns) == {"TIMESTAMP", "RECORD"}


def test_raw_probe_quality_report_catches_faults_hidden_by_median_aggregation():
    # Four redundant module-temperature probes: one is stuck at a dropout value.
    # The median across the other three healthy probes hides the fault from the
    # aggregated canonical value, but each raw probe must still be checkable.
    index = _daily_index(days=1)
    raw = pd.DataFrame(
        {
            "CR1Kx-TempMod1": -300.0,
            "CR1Kx-TempMod2": 30.0,
            "CR1Kx-TempMod3": 31.0,
            "CR1Kx-TempMod4": 29.0,
        },
        index=index,
    )
    canonical = to_canonical_frames(raw)["CR1Kx"]
    aggregated_report = quality_report(canonical)
    assert aggregated_report.loc[MODULE_TEMP_C, "rejected_samples"] == 0  # hidden by the median

    probe_report = raw_probe_quality_report(raw)
    assert probe_report.loc[("CR1Kx", "CR1Kx-TempMod1"), "rejected_samples"] == len(index)
    assert probe_report.loc[("CR1Kx", "CR1Kx-TempMod2"), "rejected_samples"] == 0


def test_to_canonical_frames_aggregates_redundant_probes_with_median():
    index = _daily_index(days=1)
    raw = pd.DataFrame(
        {
            "CR1Kx-TempMod1": 30.0,
            "CR1Kx-TempMod2": 32.0,
            "CR1Kx-TempMod3": np.nan,
            "CR1Kx-TempMod4": 34.0,
        },
        index=index,
    )
    frames = to_canonical_frames(raw)
    canonical = frames["CR1Kx"]
    assert np.isclose(canonical[MODULE_TEMP_C].iloc[0], 32.0)
    assert canonical[f"{MODULE_TEMP_C}_n_probes"].iloc[0] == 3


def test_clean_field_frame_rejects_sensor_faults_seen_in_field_exports():
    index = _daily_index(days=1)
    n = len(index)
    module_temp = np.full(n, 28.0)
    module_temp[50] = -300.0  # datalogger dropout artifact
    ppfd = np.full(n, 800.0)
    ppfd[60] = 8000.0  # far above the ~2200 umol/m2/s physical ceiling
    wind = np.full(n, 3.0)
    wind[70] = -100.0  # sentinel/error value
    pressure = np.full(n, 1013.0)
    pressure[80] = 0.0  # comms dropout
    pressure[81] = 620.0  # implausible spike

    raw = pd.DataFrame(
        {
            MODULE_TEMP_C: module_temp,
            PPFD_UMOL_M2_S: ppfd,
            WIND_SPEED_MS: wind,
            PRESSURE_HPA: pressure,
        },
        index=index,
    )
    cleaned = clean_field_frame(raw)

    assert pd.isna(cleaned[MODULE_TEMP_C].iloc[50]) or abs(cleaned[MODULE_TEMP_C].iloc[50] - 28.0) < 5
    assert cleaned[PPFD_UMOL_M2_S].max() < 2500.0
    assert cleaned[WIND_SPEED_MS].min() >= 0.0
    assert cleaned[PRESSURE_HPA].min() >= 850.0

    report = quality_report(raw)
    assert report.loc[MODULE_TEMP_C, "rejected_samples"] >= 1
    assert report.loc[PPFD_UMOL_M2_S, "rejected_samples"] >= 1
    assert report.loc[WIND_SPEED_MS, "rejected_samples"] >= 1
    assert report.loc[PRESSURE_HPA, "rejected_samples"] >= 2


def test_clean_field_frame_does_not_bridge_long_outages():
    index = _daily_index(days=2)
    values = pd.Series(500.0, index=index)
    # Simulate a multi-hour station outage (more than max_gap_periods samples).
    values.iloc[10:40] = np.nan
    raw = pd.DataFrame({PPFD_UMOL_M2_S: values})
    cleaned = clean_field_frame(raw, max_gap_periods=4)
    assert cleaned[PPFD_UMOL_M2_S].isna().sum() > 0


def test_estimate_ghi_dni_dhi_from_ppfd_is_physically_bounded():
    times = _daily_index(days=1)
    solar_position = SITE.get_solarposition(times)
    clearsky_ghi = SITE.get_clearsky(times, model="ineichen")["ghi"]
    # A clear, unshaded day: measured PPFD tracks the clear-sky PPFD closely.
    clearsky_ppfd = clearsky_ghi * 0.45 * 4.57
    weather = estimate_ghi_dni_dhi_from_ppfd(
        SITE, times, clearsky_ppfd, solar_position=solar_position, clearsky_ghi=clearsky_ghi
    )
    assert (weather["ghi"] >= 0.0).all()
    assert (weather["dni"] >= 0.0).all()
    assert (weather["dhi"] >= 0.0).all()
    assert weather["ghi"].max() < 1400.0
    daytime = solar_position["apparent_zenith"] < 90.0
    assert np.isclose(weather.loc[~daytime, "ghi"], 0.0, atol=1.0).all()
    # On a clear day the reconstruction should roughly recover the clear-sky GHI.
    midday = weather.index[weather.index.hour == 12]
    assert (weather.loc[midday, "ghi"] > 0.5 * clearsky_ghi.loc[midday]).all()


def test_estimate_ghi_dni_dhi_from_ppfd_handles_cloudy_and_night_conditions():
    times = _daily_index(days=1)
    solar_position = SITE.get_solarposition(times)
    clearsky_ghi = SITE.get_clearsky(times, model="ineichen")["ghi"]
    cloudy_ppfd = clearsky_ghi * 0.45 * 4.57 * 0.2  # heavily overcast
    weather = estimate_ghi_dni_dhi_from_ppfd(
        SITE, times, cloudy_ppfd, solar_position=solar_position, clearsky_ghi=clearsky_ghi
    )
    daytime = solar_position["apparent_zenith"] < 87.0
    assert (weather.loc[daytime, "ghi"] <= clearsky_ghi.loc[daytime] + 1e-6).all()
    assert weather["clear_sky_index"].max() <= 1.2


def _synthetic_station_csv(times: pd.DatetimeIndex) -> pd.DataFrame:
    solar_position = SITE.get_solarposition(times)
    clearsky_ghi = SITE.get_clearsky(times, model="ineichen")["ghi"]
    ppfd = (clearsky_ghi * 0.45 * 4.57).clip(lower=0.0)
    frame = pd.DataFrame(
        {
            "TIMESTAMP": times,
            "CR1Kx-TempMod1": 25.0 + 10.0 * np.cos(np.radians(solar_position["apparent_zenith"].to_numpy())),
            "CR1Kx-TempAr1": 24.0,
            "CR1Kx-Par1": ppfd,
            "CR1Kx-RH1": 70.0,
            "CR310_01-Ws": 3.0,
            "CR310_01-Pressure": 1013.0,
        }
    )
    return frame


def test_process_field_export_runs_end_to_end_with_synthetic_station_export():
    times = _daily_index(days=2)
    raw = _synthetic_station_csv(times)
    outputs = process_field_export(raw, SITE, dli_target_mol_m2_day=14.0)
    assert "CR1Kx" in outputs
    results, daily, telemetry = outputs["CR1Kx"]
    assert np.isfinite(results["pv_power_w"]).all()
    assert np.isfinite(results["crop_ppfd_umol_m2_s"]).all()
    assert (results["pv_power_w"] >= 0.0).all()
    assert results["pv_power_w"].max() <= 8000.0
    assert not telemetry.empty
    assert "input_data_complete_fraction" in daily.columns


def test_clean_field_frame_requires_timezone_aware_index():
    naive_index = pd.date_range("2026-01-01", periods=4, freq="15min")
    raw = pd.DataFrame({PPFD_UMOL_M2_S: [0.0, 1.0, 2.0, 3.0]}, index=naive_index)
    with pytest.raises(ValueError):
        clean_field_frame(raw)


def test_load_field_export_skips_unmapped_columns_without_raising():
    times = _daily_index(days=1)
    raw = _synthetic_station_csv(times)
    raw["Battery_Volts"] = 12.6
    frames = load_field_export(raw)
    assert "CR1Kx" in frames
    assert MODULE_TEMP_C in frames["CR1Kx"].columns


def test_validate_radiation_reports_no_data_explicitly():
    result = validate_radiation()
    assert result["status"] == "no_data"
    assert result["daily_dli_error_percent"] is None


def test_validate_radiation_calculates_ppfd_and_dli_error():
    times = pd.date_range("2026-01-01", periods=5, freq="15min", tz="America/Sao_Paulo")
    measured = pd.Series(1000.0, index=times)
    modeled = pd.Series(1100.0, index=times)
    result = validate_radiation(measured, modeled)
    assert result["status"] == "ok"
    assert result["samples"] == 5
    assert np.isclose(result["mae_ppfd_umol_m2_s"], 100.0)
    assert np.isclose(result["bias_ppfd_umol_m2_s"], 100.0)
    assert np.isclose(result["daily_dli_error_percent"], 10.0)


def test_manual_tracker_override_emits_absolute_flat_command():
    sink = DryRunCommandSink()
    send_manual_tracker_override(
        sink,
        timestamp="2026-08-26T12:00:00-03:00",
        subzone_id="CR1Kx",
        tilt_deg=0.0,
        reason="manual_flat",
    )
    command = sink.commands[0]
    assert command.mode == "manual_override"
    assert command.reason == "manual_flat"
    assert command.tilt_deg == 0.0
    assert command.tilt_offset_deg == 0.0


def test_manual_tracker_override_rejects_out_of_range_absolute_angle():
    sink = DryRunCommandSink()
    with pytest.raises(ValueError):
        send_manual_tracker_override(
            sink,
            timestamp="2026-08-26T12:00:00-03:00",
            tilt_deg=91.0,
        )
