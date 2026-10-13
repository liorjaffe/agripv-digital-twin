"""Explicit handling for the real ``Period_Results`` field workbook.

This export is independent from the Campbell-style station export.  Its GHI,
DNI, DHI and tracker-angle columns are already available directly, while its
``0A`` through ``5F`` labels have no physical role or unit metadata in the
workbook and are deliberately kept unclassified.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from project.io.ingestion import load_period_results_export

CORE_COLUMNS = (
    "GHI", "DNI", "DHI", "Solar_Azimuth", "Solar_Zenith",
    "Solar_Elevation", "Tracker_Angle",
)


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


def period_results_weather(source: str, *, sheet_name: str = "in") -> tuple[pd.DataFrame, pd.DataFrame, PeriodResultsInventory]:
    """Load real irradiance/weather inputs and separate tracker observations.

    The returned weather data is the direct, observed-field radiation contract
    consumed by the simulation pipeline. ``tracker_observed`` is retained
    separately because it documents what the site actually drove; it is not
    substituted for a model recommendation.
    """
    frame = load_period_results_export(source, sheet_name=sheet_name)
    missing = set(CORE_COLUMNS).difference(frame.columns)
    if missing:
        raise ValueError(f"Period_Results is missing required columns: {sorted(missing)}")
    weather = frame[["GHI", "DNI", "DHI"]].rename(columns={"GHI": "ghi", "DNI": "dni", "DHI": "dhi"})
    observed_tracker = frame[["Tracker_Angle", "Solar_Azimuth", "Solar_Zenith", "Solar_Elevation"]].rename(
        columns={"Tracker_Angle": "observed_tracker_angle_deg"}
    )
    return weather, observed_tracker, inventory_period_results(frame)