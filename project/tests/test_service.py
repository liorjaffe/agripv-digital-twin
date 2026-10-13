"""Tests for source-status handling at the period-results boundary."""

from __future__ import annotations

import pandas as pd

import project.io.service as service


def test_period_results_service_does_not_label_future_timestamps_observed(
    tmp_path,
    monkeypatch,
):
    timestamps = [
        "2026-10-13T08:00:00-03:00",
        "2026-10-13T09:00:00-03:00",
        "2026-10-13T10:00:00-03:00",
    ]
    source = tmp_path / "period-results.csv"
    pd.DataFrame(
        {
            "datetime": timestamps,
            "GHI": [50.0, 60.0, 70.0],
            "DNI": [0.0, 10.0, 20.0],
            "DHI": [50.0, 50.0, 50.0],
            "Solar_Azimuth": [0.0, 0.0, 0.0],
            "Solar_Zenith": [90.0, 80.0, 70.0],
            "Solar_Elevation": [0.0, 10.0, 20.0],
            "Tracker_Angle": [0.0, 1.0, 2.0],
        }
    ).to_csv(source, index=False)

    def fake_pipeline(weather, location, **options):
        results = pd.DataFrame({"tilt_offset_deg": 0.0}, index=weather.index)
        daily = pd.DataFrame(
            {"sample_count": [len(weather)]},
            index=pd.DatetimeIndex([weather.index[0].normalize()]),
        )
        return results, daily

    monkeypatch.setattr(service, "run_timeseries_pipeline", fake_pipeline)
    monkeypatch.setattr(service, "telemetry_frame", lambda *args, **kwargs: pd.DataFrame())

    results, daily, _, _ = service.process_period_results_export(
        source,
        location=None,
        as_of="2026-10-13T09:00:00-03:00",
    )

    assert results["data_source"].tolist() == [
        "observed_field_data",
        "observed_field_data",
        "future_timestamp_unverified",
    ]
    assert daily["data_source"].iloc[0] == "future_timestamp_unverified"
