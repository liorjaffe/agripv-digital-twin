"""Orchestration boundary between incoming data, model decisions, and outputs."""

from __future__ import annotations

import pandas as pd
import pvlib

from project.io.commands import CommandSink, TrackerCommand, manual_tracker_command
from project.io.field_data import (
    AIR_TEMP_C,
    MODULE_TEMP_C,
    PPFD_UMOL_M2_S,
    PRESSURE_HPA,
    WIND_SPEED_MS,
)
from project.io.grafana import telemetry_frame
from project.io.ingestion import load_field_export, load_timeseries, validate_weather_contract
from project.models.radiation import estimate_ghi_dni_dhi_from_ppfd
from project.scenarios.run_timeseries import run_timeseries_pipeline


def send_manual_tracker_override(
    command_sink: CommandSink,
    *,
    timestamp: str,
    subzone_id: str = "pilot",
    tilt_deg: float,
    reason: str = "manual_override",
) -> None:
    """Emit one absolute tracker-angle override to the configured command sink.

    Use ``tilt_deg=0.0`` and ``reason="manual_flat"`` for the flat-position
    experiment. The command is validated before it reaches any adapter; this
    function never talks to hardware itself.
    """
    command_sink.send(manual_tracker_command(
        timestamp=timestamp,
        subzone_id=subzone_id,
        tilt_deg=tilt_deg,
        reason=reason,
    ))


def process_weather_batch(
    source,
    location: pvlib.location.Location,
    *,
    command_sink: CommandSink | None = None,
    subzone_id: str = "pilot",
    time_column: str = "time",
    **pipeline_options,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Process an incoming batch and optionally emit tracker recommendations.

    This is the intended boundary for a future HTTP/MQTT/historian adapter. It
    computes first and only emits commands after the model returns successfully.
    """
    weather = load_timeseries(source, time_column=time_column)
    validate_weather_contract(weather)
    results, daily = run_timeseries_pipeline(weather, location, **pipeline_options)
    if command_sink is not None:
        for timestamp, row in results.iterrows():
            command_sink.send(TrackerCommand(
                timestamp=timestamp.isoformat(),
                subzone_id=subzone_id,
                tilt_offset_deg=float(row["tilt_offset_deg"]),
            ))
    return results, daily, telemetry_frame(results, subzone_id=subzone_id)


def process_field_export(
    source,
    location: pvlib.location.Location,
    *,
    command_sink: CommandSink | None = None,
    time_column: str = "TIMESTAMP",
    **pipeline_options,
) -> dict[str, tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]]:
    """Process a raw multi-logger field export end to end, per logger/subzone.

    Unlike :func:`process_weather_batch` (which expects an already-clean
    ghi/dhi/dni weather contract), this accepts the station's native Campbell
    Scientific-style export directly. Column mapping, physical-bounds cleaning,
    and PPFD-based ghi/dhi/dni reconstruction (this pilot has no pyranometer)
    all happen here before each subzone is handed to the same
    :func:`run_timeseries_pipeline` used everywhere else. Subzones with no
    usable PAR/PPFD data are skipped rather than fed fabricated weather.
    """
    canonical_by_subzone = load_field_export(source, time_column=time_column)
    outputs: dict[str, tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]] = {}
    for subzone_id, canonical in canonical_by_subzone.items():
        if PPFD_UMOL_M2_S not in canonical.columns or canonical[PPFD_UMOL_M2_S].dropna().empty:
            continue
        weather = estimate_ghi_dni_dhi_from_ppfd(location, canonical.index, canonical[PPFD_UMOL_M2_S])
        for role in (AIR_TEMP_C, MODULE_TEMP_C, WIND_SPEED_MS, PRESSURE_HPA):
            if role in canonical.columns:
                weather[role] = canonical[role]

        results, daily = run_timeseries_pipeline(weather, location, **pipeline_options)
        if command_sink is not None:
            for timestamp, row in results.iterrows():
                command_sink.send(TrackerCommand(
                    timestamp=timestamp.isoformat(),
                    subzone_id=subzone_id,
                    tilt_offset_deg=float(row["tilt_offset_deg"]),
                ))
        outputs[subzone_id] = (results, daily, telemetry_frame(results, subzone_id=subzone_id))
    return outputs

