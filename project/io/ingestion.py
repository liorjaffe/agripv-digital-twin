"""Protocol-neutral sensor and forecast ingestion."""

from __future__ import annotations

from io import StringIO
from pathlib import Path

import pandas as pd

from project.io.field_data import to_canonical_frames
from project.qc.cleaning import clean_field_frame


def load_timeseries(source: str | Path | pd.DataFrame, *, time_column: str = "time", timezone: str = "America/Sao_Paulo") -> pd.DataFrame:
    """Load a sensor/forecast batch from DataFrame, CSV, JSON, or Parquet.

    The returned frame has a sorted, timezone-aware DatetimeIndex. Transport details
    such as MQTT, HTTP, or a lab historian can be adapted to this same contract.
    """
    if isinstance(source, pd.DataFrame):
        frame = source.copy()
    else:
        path = Path(source)
        suffix = path.suffix.lower()
        if suffix == ".csv":
            frame = pd.read_csv(path)
        elif suffix in {".json", ".jsonl"}:
            frame = pd.read_json(path, lines=suffix == ".jsonl")
        elif suffix == ".parquet":
            frame = pd.read_parquet(path)
        else:
            raise ValueError("Supported inputs are DataFrame, CSV, JSON/JSONL, and Parquet")

    if isinstance(frame.index, pd.DatetimeIndex) and time_column not in frame.columns:
        timestamps = frame.index
    elif time_column in frame.columns:
        timestamps = pd.DatetimeIndex(pd.to_datetime(frame.pop(time_column), errors="coerce"))
    else:
        raise ValueError(f"No '{time_column}' column or DatetimeIndex found")
    if timestamps.isna().any():
        raise ValueError("Input contains invalid timestamps")
    if timestamps.tz is None:
        timestamps = timestamps.tz_localize(timezone, ambiguous="NaT", nonexistent="shift_forward")
    else:
        timestamps = timestamps.tz_convert(timezone)
    frame.index = timestamps
    return frame.sort_index()


def load_period_results_export(
    source: str | Path,
    *,
    sheet_name: str = "in",
    timezone: str = "America/Sao_Paulo",
) -> pd.DataFrame:
    """Load a Period_Results CSV or workbook without mixing synthetic inputs.

    The field export may be a normal CSV, or CSV text stored in one Excel column.
    In both cases the returned frame is time-indexed and timezone-aware.
    """
    if Path(source).suffix.lower() == ".csv":
        frame = pd.read_csv(source)
    else:
        workbook_column = pd.read_excel(source, sheet_name=sheet_name, header=None).iloc[:, 0]
        lines = workbook_column.dropna().astype(str)
        header_at = next(
            (index for index, line in enumerate(lines) if line.startswith("date,datetime,GHI,DNI,DHI,")),
            None,
        )
        if header_at is None:
            raise ValueError("Period_Results export header not found")
        frame = pd.read_csv(StringIO("\n".join(lines.iloc[header_at:].tolist())))
    return load_timeseries(frame, time_column="datetime", timezone=timezone)


def load_field_export(
    source: str | Path | pd.DataFrame,
    *,
    time_column: str = "TIMESTAMP",
    timezone: str = "America/Sao_Paulo",
    interval: str = "15min",
    max_gap_periods: int = 4,
) -> dict[str, pd.DataFrame]:
    """Load a raw multi-logger field export into cleaned canonical frames per subzone.

    This is the entry point for real Campbell Scientific-style station exports
    (e.g. Grafana/LoggerNet CSV pulls) with columns such as ``CR1Kx-TempMod1`` or
    ``CR310_01-Ws``. It chains :func:`project.io.field_data.to_canonical_frames`
    (column recognition and multi-probe aggregation) with
    :func:`project.qc.cleaning.clean_field_frame` (physical-bounds rejection,
    spike rejection, gap-limited interpolation) and returns one cleaned frame per
    logger/subzone with canonical columns such as ``ppfd_umol_m2_s``,
    ``air_temp_c``, ``module_temp_c``, ``wind_speed_ms``, and ``pressure_hpa``.

    These frames still need
    :func:`project.models.radiation.estimate_ghi_dni_dhi_from_ppfd` to become a
    full ``ghi``/``dhi``/``dni`` weather contract, since this station has no
    pyranometer -- see :func:`project.io.service.process_field_export` for the
    full chain.
    """
    raw = load_timeseries(source, time_column=time_column, timezone=timezone)
    canonical_frames = to_canonical_frames(raw)
    return {
        subzone_id: clean_field_frame(frame, interval=interval, max_gap_periods=max_gap_periods)
        for subzone_id, frame in canonical_frames.items()
    }


def validate_weather_contract(frame: pd.DataFrame) -> None:
    """Validate the minimum weather contract consumed by the radiation model."""
    required = {"ghi", "dhi", "dni"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Weather input is missing columns: {sorted(missing)}")
