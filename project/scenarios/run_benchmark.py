"""Scenario benchmark entry point.

This will host the historical-season strategy comparison once the datasets are available.
"""

from __future__ import annotations


def run_benchmark() -> dict:
    return {
        "strategy": "baseline",
        "lettuce_dry_matter": 0.0,
        "pv_kwh": 0.0,
    }
