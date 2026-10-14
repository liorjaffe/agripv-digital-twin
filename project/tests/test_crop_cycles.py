import pandas as pd
import pytest

from project.scenarios.crop_cycles import (
    TRANSPLANT_DRY_MASS_G_PER_PLANT,
    estimate_sowing_date,
    seasonal_canopy_temperature,
    seasonal_mean_temp_c,
    simulate_repeated_crops,
    transplant_initial_state_g_m2,
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


def test_repeated_crop_uses_supplied_air_temperature_for_biomass():
    # A complete TC cycle at 24 C contains 27 days of field biomass.
    times = pd.date_range("2026-01-01", periods=30 * 24, freq="h", tz="America/Sao_Paulo")
    frame = pd.DataFrame({"crop_light": 100.0}, index=times)

    cool = simulate_repeated_crops(
        frame,
        "crop_light",
        max_cycle_days=30,
        temperature_c=pd.Series(14.0, index=times),
        plant_density_per_m2=8.0,
    )
    warm = simulate_repeated_crops(
        frame,
        "crop_light",
        max_cycle_days=30,
        temperature_c=pd.Series(24.0, index=times),
        plant_density_per_m2=8.0,
    )

    assert (warm["cycle_stage"] == "field").any()
    assert cool["cycle_dry_biomass_g_m2"].iloc[-1] != warm[
        "cycle_dry_biomass_g_m2"
    ].iloc[-1]


def test_cycles_start_at_transplant_and_are_contiguous_with_no_nursery_rows():
    times = pd.date_range("2026-01-01", periods=60 * 24, freq="h", tz="America/Sao_Paulo")
    frame = pd.DataFrame({"crop_light": 100.0}, index=times)
    density = 8.0

    cycles = simulate_repeated_crops(
        frame,
        "crop_light",
        max_cycle_days=60,
        temperature_c=pd.Series(24.0, index=times),
        plant_density_per_m2=density,
    )
    assert set(cycles["cycle_stage"]) == {"field"}
    for _, cycle in cycles.groupby("cycle_id"):
        assert cycle["cycle_dry_biomass_g_m2"].iloc[0] == pytest.approx(
            TRANSPLANT_DRY_MASS_G_PER_PLANT * density
        )
        assert cycle["cycle_model_fresh_biomass_g_m2"].iloc[0] == pytest.approx(
            0.90 * density
        )
        assert cycle["sowing_date_estimate"].dropna().nunique() <= 1
    groups = list(cycles.groupby("cycle_id"))
    for (_, previous), (_, following) in zip(groups, groups[1:]):
        assert following.index[0] == previous.index[-1] + pd.Timedelta(hours=1)

    first = cycles[cycles["cycle_id"] == 1]
    # 472.79 GDD / (24 - 6.1) C/day requires 27 calendar days.
    assert first["harvest"].iloc[-1]
    assert len(first) == 27 * 24


def test_sowing_date_estimate_counts_st_gdd_backwards():
    times = pd.date_range("2026-01-01", periods=30 * 24, freq="h", tz="America/Sao_Paulo")
    daily_temperatures = pd.Series(24.0, index=times).groupby(times.normalize()).mean()

    estimate = estimate_sowing_date(pd.Timestamp("2026-01-25", tz="America/Sao_Paulo"), daily_temperatures)

    assert estimate == pd.Timestamp("2026-01-04", tz="America/Sao_Paulo")


def test_transplant_initial_state_rejects_invalid_density():
    structural, nonstructural = transplant_initial_state_g_m2(10.0)
    assert structural + nonstructural == pytest.approx(TRANSPLANT_DRY_MASS_G_PER_PLANT * 10.0)
    with pytest.raises(ValueError, match="plant_density_per_m2"):
        transplant_initial_state_g_m2(0.0)


def test_repeated_crop_simulation_rejects_invalid_inputs():
    times = pd.date_range("2026-01-01", periods=1, freq="h", tz="America/Sao_Paulo")
    frame = pd.DataFrame({"crop_light": [100.0]}, index=times)

    with pytest.raises(ValueError, match="max_cycle_days"):
        simulate_repeated_crops(frame, "crop_light", max_cycle_days=0)
    with pytest.raises(ValueError, match="missing light column"):
        simulate_repeated_crops(frame, "unknown")
    with pytest.raises(ValueError, match="temperature_c must align"):
        simulate_repeated_crops(
            frame,
            "crop_light",
            temperature_c=pd.Series(
                [20.0], index=frame.index + pd.Timedelta(hours=1)
            ),
        )
