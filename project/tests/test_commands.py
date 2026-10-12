"""Tracker command contract tests."""

from __future__ import annotations

import pytest

from project.io.commands import TrackerCommand


@pytest.mark.parametrize(
    ("timestamp", "message"),
    [
        ("", "non-empty"),
        ("not-a-timestamp", "valid"),
        ("2026-08-26T12:00:00", "timezone-aware"),
    ],
)
def test_tracker_command_rejects_missing_invalid_or_naive_timestamps(timestamp, message):
    with pytest.raises(ValueError, match=message):
        TrackerCommand(
            timestamp=timestamp,
            subzone_id="CR1Kx",
            tilt_offset_deg=0.0,
        )


@pytest.mark.parametrize(
    "timestamp",
    [
        "2026-08-26T12:00:00-03:00",
        "2026-08-26T15:00:00Z",
    ],
)
def test_tracker_command_accepts_timezone_aware_iso_timestamps(timestamp):
    command = TrackerCommand(
        timestamp=timestamp,
        subzone_id="CR1Kx",
        tilt_offset_deg=0.0,
    )

    assert command.timestamp == timestamp
