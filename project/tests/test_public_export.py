"""Tests for the reproducible public period-data export."""

from __future__ import annotations

import runpy
from pathlib import Path

import pandas as pd
import pytest


EXPORT_RECORDS = runpy.run_path(
    str(Path(__file__).parents[2] / "scripts" / "export-period-results-public.py")
)["export_records"]


def test_public_export_reads_the_tracked_csv_and_keeps_timestamps_and_nulls(tmp_path):
    source = tmp_path / "period.csv"
    pd.DataFrame(
        {
            "datetime": ["2026-01-01T07:00:00-03:00"],
            "GHI": [49.12345],
            "DNI": [None],
            "DHI": [49.0],
        }
    ).to_csv(source, index=False)

    assert EXPORT_RECORDS(source, as_of="2026-01-01T08:00:00-03:00") == [
        {
            "datetime": "2026-01-01T07:00:00-03:00",
            "ghi": 49.123,
            "dni": None,
            "dhi": 49.0,
            "data_source": "observed_field_data",
        }
    ]


def test_public_export_marks_future_timestamps_as_unverified(tmp_path):
    source = tmp_path / "period.csv"
    pd.DataFrame(
        {
            "datetime": [
                "2026-10-13T08:00:00-03:00",
                "2026-10-13T10:00:00-03:00",
            ],
            "GHI": [49.0, 52.0],
            "DNI": [0.0, 3.0],
            "DHI": [49.0, 49.0],
        }
    ).to_csv(source, index=False)

    records = EXPORT_RECORDS(
        source,
        as_of="2026-10-13T09:00:00-03:00",
    )

    assert [record["data_source"] for record in records] == [
        "observed_field_data",
        "future_timestamp_unverified",
    ]


def test_public_export_rejects_naive_timestamps(tmp_path):
    source = tmp_path / "period.csv"
    pd.DataFrame(
        {
            "datetime": ["2026-01-01 07:00:00"],
            "GHI": [49.0],
            "DNI": [0.0],
            "DHI": [49.0],
        }
    ).to_csv(source, index=False)

    with pytest.raises(ValueError, match="timezone-aware"):
        EXPORT_RECORDS(source)
