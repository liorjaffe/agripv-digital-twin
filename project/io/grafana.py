"""Grafana-compatible telemetry export without coupling the model to Grafana."""

from __future__ import annotations

import math
from pathlib import Path

import pandas as pd


def telemetry_frame(results: pd.DataFrame, *, subzone_id: str = "pilot") -> pd.DataFrame:
    """Convert model results to a narrow, dashboard-friendly table."""
    columns = [
        column for column in (
            "crop_ghi_w_m2", "crop_ppfd_umol_m2_s", "target_ppfd_umol_m2_s",
            "pv_power_w", "total_dry_biomass", "tilt_offset_deg",
        ) if column in results.columns
    ]
    telemetry = results[columns].copy()
    telemetry["subzone_id"] = subzone_id
    telemetry.index.name = "time"
    return telemetry.reset_index()


def write_grafana_json(results: pd.DataFrame, path: str | Path, *, subzone_id: str = "pilot") -> Path:
    """Write JSON suitable for Grafana JSON API-style data sources or inspection."""
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    telemetry_frame(results, subzone_id=subzone_id).to_json(output, orient="records", date_format="iso")
    return output


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace(" ", "\\ ").replace(",", "\\,").replace("=", "\\=")


def to_influx_lines(results: pd.DataFrame, *, measurement: str = "agripv", subzone_id: str = "pilot") -> str:
    """Serialize numeric results as InfluxDB line protocol for Grafana ingestion."""
    if not isinstance(results.index, pd.DatetimeIndex):
        raise TypeError("results must use a DatetimeIndex")
    if results.index.tz is None:
        raise ValueError("results timestamps must be timezone-aware")

    telemetry = telemetry_frame(results, subzone_id=subzone_id).set_index("time")
    lines = []
    for timestamp, row in telemetry.iterrows():
        fields = [
            f"{key}={numeric_value}"
            for key, value in row.items()
            if key != "subzone_id"
            and pd.notna(value)
            and math.isfinite(numeric_value := float(value))
        ]
        if fields:
            ns = int(timestamp.timestamp() * 1_000_000_000)
            lines.append(f"{_escape(measurement)},subzone_id={_escape(subzone_id)} {','.join(fields)} {ns}")
    return "\n".join(lines)
