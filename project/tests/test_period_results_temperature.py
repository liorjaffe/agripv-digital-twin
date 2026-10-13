from __future__ import annotations

import pandas as pd
import pytest

from project.io.period_results import (
    load_tmy_air_temperature,
    period_results_weather,
)


def _write_tmy_temperature(path):
    timestamps = pd.date_range(
        "1990-01-01T00:00:00Z",
        periods=365 * 24,
        freq="h",
    )
    pd.DataFrame(
        {
            "time_utc": timestamps,
            "temp_air_c": [10.0 + timestamp.month + timestamp.hour / 100 for timestamp in timestamps],
        }
    ).to_csv(path, index=False)
    return timestamps


def test_load_tmy_temperature_maps_utc_hours_to_target_site_year(tmp_path):
    source = tmp_path / "tmy-temperature.csv"
    _write_tmy_temperature(source)

    temperature = load_tmy_air_temperature(source, year=2026)

    assert len(temperature) == 365 * 24
    assert temperature.index.tz is not None
    assert temperature.loc[
        pd.Timestamp("2026-01-01 09:00", tz="America/Sao_Paulo")
    ] == 11.12
    assert temperature.loc[
        pd.Timestamp("2026-01-01 00:00", tz="America/Sao_Paulo")
    ] == 11.03


def test_load_tmy_temperature_rejects_incomplete_typical_year(tmp_path):
    source = tmp_path / "incomplete-tmy.csv"
    _write_tmy_temperature(source)
    frame = pd.read_csv(source).iloc[:-1]
    frame.to_csv(source, index=False)

    with pytest.raises(ValueError, match="complete, hourly"):
        load_tmy_air_temperature(source, year=2026)


def test_period_results_weather_adds_temperature_without_replacing_irradiance(tmp_path):
    tmy_source = tmp_path / "tmy-temperature.csv"
    _write_tmy_temperature(tmy_source)
    field_source = tmp_path / "period-components.csv"
    field = pd.DataFrame(
        {
            "datetime": [
                "2026-01-01T09:00:00-03:00",
                "2026-01-01T10:00:00-03:00",
            ],
            "GHI": [510.0, 620.0],
            "DNI": [300.0, 400.0],
            "DHI": [210.0, 220.0],
            "Solar_Azimuth": [30.0, 45.0],
            "Solar_Zenith": [50.0, 40.0],
            "Solar_Elevation": [40.0, 50.0],
            "Tracker_Angle": [1.0, 2.0],
        }
    )
    field.to_csv(field_source, index=False)

    weather, _, _ = period_results_weather(
        field_source,
        air_temperature_source=tmy_source,
    )

    assert len(weather) == 365 * 24
    field_index = pd.DatetimeIndex(
        pd.to_datetime(field["datetime"], utc=True)
    ).tz_convert("America/Sao_Paulo")
    pd.testing.assert_series_equal(
        weather.loc[field_index, "ghi"].reset_index(drop=True),
        pd.Series([510.0, 620.0], name="ghi"),
        check_names=True,
    )
    assert weather.loc[
        pd.Timestamp("2026-01-01 09:00", tz="America/Sao_Paulo"), "air_temp_c"
    ] == 11.12
    assert weather.attrs["air_temp_source"].startswith("TMY climatological")
    assert weather.attrs["missing_irradiance_policy"] == "zero"
