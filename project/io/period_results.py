"""Explicit handling for the real ``Period_Results`` field workbook.

This export is independent from the Campbell-style station export.  Its GHI,
DNI, DHI and tracker-angle columns are already available directly, while its
``0A`` through ``5F`` labels have no physical role or unit metadata in the
workbook and are deliberately kept unclassified.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from project.io.ingestion import load_period_results_export

DEFAULT_TMY_AIR_TEMPERATURE_SOURCE = (
    Path(__file__).resolve().parents[1] / "data" / "raw" / "tmy_air_temperature.csv"
)
CORE_COLUMNS = (
    "GHI", "DNI", "DHI", "Solar_Azimuth", "Solar_Zenith",
    "Solar_Elevation", "Tracker_Angle",
)


def load_tmy_air_temperature(
    source: str | Path,
    *,
    year: int,
    timezone: str = "America/Sao_Paulo",
) -> pd.Series:
    """Map one complete UTC typical year to local hourly timestamps for ``year``."""
    frame = pd.read_csv(source)
    required = {"time_utc", "temp_air_c"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"TMY temperature input is missing columns: {sorted(missing)}")

    timestamps = pd.DatetimeIndex(
        pd.to_datetime(frame["time_utc"], errors="coerce", utc=True)
    )
    temperature = pd.to_numeric(frame["temp_air_c"], errors="coerce")
    if timestamps.isna().any() or not timestamps.is_unique:
        raise ValueError("TMY temperature timestamps must be valid and unique")
    if not np.isfinite(temperature.to_numpy(dtype=float)).all():
        raise ValueError("TMY air temperatures must all be finite numeric values")

    ordered = pd.Series(temperature.to_numpy(), index=timestamps).sort_index()
    timestamps = ordered.index
    expected_tmy = pd.date_range(
        timestamps[0].normalize(),
        periods=365 * 24,
        freq="h",
    )
    if (
        len(timestamps) != len(expected_tmy)
        or not timestamps.equals(expected_tmy)
        or timestamps[0].month != 1
        or timestamps[0].day != 1
        or timestamps[0].hour != 0
    ):
        raise ValueError(
            "TMY temperature input must contain one complete, hourly, "
            "non-leap UTC year starting January 1 at 00:00"
        )

    target_index = pd.date_range(
        f"{year}-01-01",
        periods=365 * 24,
        freq="h",
        tz=timezone,
    )
    target_utc = target_index.tz_convert("UTC")
    source_keys = timestamps.strftime("%m-%d %H:%M")
    target_keys = target_utc.strftime("%m-%d %H:%M")
    lookup = pd.Series(ordered.to_numpy(), index=source_keys)
    mapped = lookup.reindex(target_keys)
    if mapped.isna().any():
        raise ValueError(
            f"TMY temperature input cannot cover every hour of {year} in "
            f"{timezone}; leap years and daylight-saving transitions are unsupported"
        )
    mapped.index = target_index
    mapped.name = "air_temp_c"
    return mapped.astype(float)


@dataclass(frozen=True)
class PeriodResultsInventory:
    """Named channel groups retained exactly as exported by the field system."""

    fixed_plane_irradiance: tuple[str, ...]
    tracker_face_irradiance: tuple[str, ...]
    tracker_side_irradiance: tuple[str, ...]
    unclassified_grid_channels: tuple[str, ...]


def inventory_period_results(frame: pd.DataFrame) -> PeriodResultsInventory:
    """Return exact export-name groups without inferring unsupported sensor roles."""
    columns = tuple(frame.columns)
    return PeriodResultsInventory(
        fixed_plane_irradiance=tuple(column for column in columns if column.startswith("FIX")),
        tracker_face_irradiance=tuple(
            column for column in columns
            if column.startswith("TRK") and ("_Front_AVG" in column or "_Back_AVG" in column)
        ),
        tracker_side_irradiance=tuple(
            column for column in columns
            if column.startswith("TRK") and column.endswith("_AVG") and "_Front_" not in column and "_Back_" not in column
        ),
        unclassified_grid_channels=tuple(
            column for column in columns
            if len(column) == 6 and column[0].isdigit() and column[1].isalpha() and column.endswith("_AVG")
        ),
    )


def period_results_data_source(
    index: pd.DatetimeIndex,
    *,
    as_of: str | pd.Timestamp | None = None,
) -> pd.Series:
    """Classify rows by timestamp without guessing what future rows represent.

    Timestamps after the cutoff are retained as ``future_timestamp_unverified``;
    the available export does not establish whether they are forecasts or
    simulations. A timezone-aware cutoff is required when one is provided.
    """
    if not isinstance(index, pd.DatetimeIndex) or index.tz is None:
        raise ValueError("Period_Results timestamps must be timezone-aware")
    cutoff = pd.Timestamp.now(tz=index.tz) if as_of is None else pd.Timestamp(as_of)
    if cutoff.tzinfo is None:
        raise ValueError("as_of must be timezone-aware")
    cutoff = cutoff.tz_convert(index.tz)
    return pd.Series(
        ["observed_field_data" if timestamp <= cutoff else "future_timestamp_unverified"
         for timestamp in index],
        index=index,
        name="data_source",
    )


def period_results_weather(
    source: str | Path,
    *,
    sheet_name: str = "in",
    air_temperature_source: str | Path | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, PeriodResultsInventory]:
    """Load field irradiance, optional TMY temperature, and tracker observations.

    The returned weather frame retains field GHI/DNI/DHI values and can add a
    separate full-year temperature-only typical-year series. ``tracker_observed``
    is retained separately because it documents what the site actually drove;
    it is not substituted for a model recommendation.
    """
    frame = load_period_results_export(source, sheet_name=sheet_name)
    missing = set(CORE_COLUMNS).difference(frame.columns)
    if missing:
        raise ValueError(f"Period_Results is missing required columns: {sorted(missing)}")
    weather = frame[["GHI", "DNI", "DHI"]].rename(columns={"GHI": "ghi", "DNI": "dni", "DHI": "dhi"})
    observed_tracker = frame[["Tracker_Angle", "Solar_Azimuth", "Solar_Zenith", "Solar_Elevation"]].rename(
        columns={"Tracker_Angle": "observed_tracker_angle_deg"}
    )
    if air_temperature_source is not None:
        if "air_temp_c" in frame.columns:
            raise ValueError(
                "Period_Results already contains air_temp_c; refusing to replace it"
            )
        years = weather.index.year.unique()
        if len(years) != 1:
            raise ValueError("TMY temperature mapping requires one field-data calendar year")
        temperature = load_tmy_air_temperature(
            air_temperature_source,
            year=int(years[0]),
            timezone="America/Sao_Paulo",
        )
        weather = weather.join(temperature, how="outer")
        weather.attrs["air_temp_source"] = (
            "TMY climatological air temperature from "
            f"{Path(air_temperature_source).name}, UTC month/day/hour mapped "
            "to local standard-time hours"
        )
    weather.attrs["irradiance_source"] = (
        f"{Path(source).name} GHI/DNI/DHI"
    )
    weather.attrs["missing_irradiance_policy"] = "zero"
    return weather, observed_tracker, inventory_period_results(frame)