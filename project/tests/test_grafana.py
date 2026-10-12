"""Grafana and InfluxDB telemetry export tests."""

from __future__ import annotations

import pandas as pd
import pytest

from project.io.grafana import to_influx_lines


def test_to_influx_lines_omits_missing_and_non_finite_fields():
    times = pd.date_range("2026-01-01 12:00", periods=1, tz="America/Sao_Paulo")
    results = pd.DataFrame(
        {
            "pv_power_w": [100.0],
            "crop_ppfd_umol_m2_s": [float("inf")],
            "total_dry_biomass": [float("nan")],
            "tilt_offset_deg": [float("-inf")],
        },
        index=times,
    )

    lines = to_influx_lines(results)

    assert lines == "agripv,subzone_id=pilot pv_power_w=100.0 1767279600000000000"


def test_to_influx_lines_rejects_naive_timestamps():
    times = pd.date_range("2026-01-01 12:00", periods=1)
    results = pd.DataFrame({"pv_power_w": [100.0]}, index=times)

    with pytest.raises(ValueError, match="timezone-aware"):
        to_influx_lines(results)


def test_to_influx_lines_requires_datetime_index():
    results = pd.DataFrame({"pv_power_w": [100.0]}, index=["2026-01-01T12:00:00-03:00"])

    with pytest.raises(TypeError, match="DatetimeIndex"):
        to_influx_lines(results)
