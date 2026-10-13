"""Regression tests for the report's assumption-qualified channel comparison."""

from __future__ import annotations

import numpy as np
import pandas as pd

from project.scenarios.generate_simple_report import (
    attach_channel_ppfd_estimates,
    channel_comparison_summary,
    daily_table,
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
    assert "not independent validation" in report
    assert "Open scientific task:</strong> obtain the authoritative site channel map" in report
    assert "Do not use these metrics to calibrate" in report
    assert "DLI errors are omitted" in report
    assert "Mean DLI error" not in report


def test_channel_comparison_does_not_fabricate_missing_channels():
    times = pd.date_range("2026-01-01 08:00", periods=2, freq="h", tz="UTC")
    results = pd.DataFrame({"crop_ppfd_umol_m2_s": [100.0, 200.0]}, index=times)
    period_components = pd.DataFrame({"unclassified": [50.0, 100.0]}, index=times)

    compared = attach_channel_ppfd_estimates(results, period_components)

    assert not any(column.startswith("channel_ppfd_") for column in compared.columns)
    assert "No comparable 2A/2B/2C" in channel_comparison_summary(compared)


def test_daily_table_exposes_target_band_reachability():
    daily = pd.DataFrame(
        {
            "dli_mol_m2_day": [33.0],
            "pv_energy_kwh": [5.0],
            "final_dry_biomass": [20.0],
            "daylight_coverage_fraction": [1.0],
            "candidate_min_dli_mol_m2_day": [20.0],
            "candidate_max_dli_mol_m2_day": [40.0],
            "candidate_dli_target_band_reachable": [False],
            "candidate_dli_ceiling_reachable": [False],
            "candidate_dli_minimum_reachable": [True],
        },
        index=pd.DatetimeIndex(["2026-01-01"], tz="America/Sao_Paulo"),
    )

    rendered = daily_table(daily)

    assert "ceiling unreachable" in rendered
    assert "20.00–40.00" in rendered
