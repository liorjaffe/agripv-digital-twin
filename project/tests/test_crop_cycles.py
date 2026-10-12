import pandas as pd
import pytest

from project.scenarios.crop_cycles import (
    seasonal_canopy_temperature,
    seasonal_mean_temp_c,
    simulate_repeated_crops,
)


def test_seasonal_temperature_curve_is_shared_and_starts_at_planting_temperature():
    times = pd.date_range("2026-01-01", periods=3, freq="h", tz="America/Sao_Paulo")

    temperatures = seasonal_canopy_temperature(times, planting_temp_c=24.0)

    assert temperatures.iloc[0] == 24.0
    assert seasonal_mean_temp_c(1) > seasonal_mean_temp_c(182)


def test_repeated_crop_window_preserves_timeline_harvest_marker_behavior():
    times = pd.date_range("2026-01-01", periods=24, freq="h", tz="America/Sao_Paulo")
    light = pd.DataFrame({"crop_light": 100.0}, index=times)

    model_explorer_cycles = simulate_repeated_crops(light, "crop_light", max_cycle_days=1)
    timeline_cycles = simulate_repeated_crops(
        light,
        "crop_light",
        max_cycle_days=1,
        mark_cycle_window_end_as_harvest=True,
    )

    assert not model_explorer_cycles["harvest"].any()
    assert timeline_cycles["harvest"].sum() == 1
    assert timeline_cycles["cycle_id"].nunique() == 1
    assert (timeline_cycles["cycle_fresh_biomass_g_m2"] >= 0).all()
    assert (timeline_cycles["cycle_fresh_biomass_g_m2"] == timeline_cycles["cycle_model_fresh_biomass_g_m2"]).all()


def test_repeated_crop_simulation_rejects_invalid_inputs():
    times = pd.date_range("2026-01-01", periods=1, freq="h", tz="America/Sao_Paulo")
    frame = pd.DataFrame({"crop_light": [100.0]}, index=times)

    with pytest.raises(ValueError, match="max_cycle_days"):
        simulate_repeated_crops(frame, "crop_light", max_cycle_days=0)
    with pytest.raises(ValueError, match="missing light column"):
        simulate_repeated_crops(frame, "unknown")
