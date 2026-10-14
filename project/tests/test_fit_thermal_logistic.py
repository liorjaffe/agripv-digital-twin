import numpy as np
import pandas as pd
import pytest

from project.validation.fit_thermal_logistic import (
    DEFAULT_WEIGHING_CSV,
    fit_thermal_logistic,
    logistic_fresh_mass,
)


def test_fit_thermal_logistic_recovers_synthetic_parameters(tmp_path):
    transplant = pd.Timestamp("2026-08-01")
    dates = pd.to_datetime(
        ["2026-08-02", "2026-08-07", "2026-08-12", "2026-08-17", "2026-08-22"]
    )
    temperatures = pd.Series(
        16.0,
        index=pd.date_range("2026-08-01", "2026-08-22", freq="D", tz="America/Sao_Paulo"),
    )
    gdd = np.asarray([(date - transplant).days * 9.9 for date in dates])
    masses = logistic_fresh_mass(gdd, 25.0, -3.0, 0.02)
    weighings = pd.DataFrame(
        {
            "date": dates.strftime("%Y-%m-%d"),
            "bed_position": [f"P{i}" for i in range(len(dates))],
            "fresh_mass_g": masses,
            "dry_mass_g": masses * 0.1,
            "preliminary": False,
        }
    )
    result = fit_thermal_logistic(
        _write_weighings(weighings, tmp_path / "synthetic.csv"),
        transplant.date(),
        temperatures,
        harvest_date=dates[-1].date(),
    )

    assert result["status"] == "fit"
    assert result["parameters"]["a"] == pytest.approx(25.0, rel=1e-4)
    assert result["parameters"]["b"] == pytest.approx(-3.0, rel=1e-4)
    assert result["parameters"]["c"] == pytest.approx(0.02, rel=1e-4)
    assert all(value >= 0.0 for value in result["standard_errors"].values())
    assert result["rmse_g_per_plant"] < 1e-8
    assert result["inflection_gdd"] == pytest.approx(150.0, rel=1e-4)


def test_cycle_one_weighings_are_insufficient_without_harvest_measurement():
    frame = pd.read_csv(DEFAULT_WEIGHING_CSV)
    assert frame.groupby("date").size().to_dict() == {
        "2026-09-02": 6,
        "2026-09-18": 10,
        "2026-09-25": 10,
    }
    assert frame["preliminary"].all()
    assert frame.loc[frame["date"] == "2026-09-02", "dry_mass_g"].isna().all()
    assert frame.loc[frame["date"] == "2026-09-18", "fresh_mass_g"].tolist() == [
        2.43, 1.87, 4.45, 1.31, 2.78, 3.81, 5.29, 3.07, 3.85, 1.47
    ]

    temperature = pd.Series(
        16.0,
        index=pd.date_range("2026-09-02", "2026-10-01", freq="D", tz="America/Sao_Paulo"),
    )

    result = fit_thermal_logistic(
        DEFAULT_WEIGHING_CSV,
        "2026-09-02",
        temperature,
        harvest_date="2026-10-01",
    )

    assert result["status"] == "insufficient_data"
    assert result["distinct_dates"] == 3


def test_fit_requires_a_weighing_on_the_declared_harvest_date(tmp_path):
    dates = pd.date_range("2026-08-02", periods=4, freq="5D")
    weighings = pd.DataFrame(
        {
            "date": dates.strftime("%Y-%m-%d"),
            "bed_position": ["A", "B", "C", "D"],
            "fresh_mass_g": [1.0, 2.0, 4.0, 8.0],
            "dry_mass_g": [0.1, 0.2, 0.4, 0.8],
            "preliminary": [True] * 4,
        }
    )
    temperature = pd.Series(
        16.0,
        index=pd.date_range("2026-08-01", "2026-08-30", freq="D", tz="America/Sao_Paulo"),
    )

    result = fit_thermal_logistic(
        _write_weighings(weighings, tmp_path / "no-harvest.csv"),
        "2026-08-01",
        temperature,
        harvest_date="2026-08-30",
    )

    assert result["status"] == "insufficient_data"
    assert result["reason"] == "no_weighing_on_harvest_date"


def _write_weighings(frame: pd.DataFrame, path):
    frame.to_csv(path, index=False)
    return path
