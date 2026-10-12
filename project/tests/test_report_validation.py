"""Regression tests for the report's assumption-qualified channel comparison."""

from __future__ import annotations

import numpy as np
import pandas as pd

from project.scenarios.generate_simple_report import (
    attach_channel_ppfd_estimates,
    channel_comparison_summary,
)


def test_channel_comparison_attaches_converted_values_and_reports_all_channels():
    times = pd.date_range("2026-01-01 08:00", periods=3, freq="h", tz="America/Sao_Paulo")
    period_components = pd.DataFrame(
        {
            "2A_AVG": [100.0, 200.0, 300.0],
            "2B_AVG": [150.0, 250.0, 350.0],
            "2C_AVG": [200.0, 300.0, 400.0],
        },
        index=times,
    )
    results = pd.DataFrame(
        {"crop_ppfd_umol_m2_s": period_components["2A_AVG"] * 0.45 * 4.57},
        index=times,
    )

    compared = attach_channel_ppfd_estimates(results, period_components)

    assert np.allclose(
        compared["channel_ppfd_2A_AVG"],
        period_components["2A_AVG"] * 0.45 * 4.57,
    )
    report = channel_comparison_summary(compared)
    assert all(channel in report for channel in ("2A_AVG", "2B_AVG", "2C_AVG"))
    assert "1</td>" in report
    assert "Not independent validation" in report
    assert "Open item: obtain an authoritative sensor/channel map" in report
    assert "DLI errors are omitted" in report
    assert "Mean DLI error" not in report


def test_channel_comparison_does_not_fabricate_missing_channels():
    times = pd.date_range("2026-01-01 08:00", periods=2, freq="h", tz="UTC")
    results = pd.DataFrame({"crop_ppfd_umol_m2_s": [100.0, 200.0]}, index=times)
    period_components = pd.DataFrame({"unclassified": [50.0, 100.0]}, index=times)

    compared = attach_channel_ppfd_estimates(results, period_components)

    assert not any(column.startswith("channel_ppfd_") for column in compared.columns)
    assert "No comparable 2A/2B/2C" in channel_comparison_summary(compared)
