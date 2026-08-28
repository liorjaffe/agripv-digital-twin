"""Tests for the lettuce thermal-time (GDD) phenology clock."""

from __future__ import annotations

import math

from project.models.lettuce_development import (
    LettuceThermalDevelopment,
    LettuceThermalDevelopmentParams,
    daily_gdd,
)


def test_temperature_below_base_temperature_gives_zero_gdd():
    assert daily_gdd(2.0, base_temperature_c=4.1) == 0.0


def test_temperature_equal_to_base_temperature_gives_zero_gdd():
    assert daily_gdd(4.1, base_temperature_c=4.1) == 0.0


def test_normal_development_temperature_accumulates_expected_gdd():
    assert math.isclose(daily_gdd(24.31, base_temperature_c=4.1), 20.21, rel_tol=1e-9)


def test_transition_from_st_to_tc_resets_stage_gdd_and_uses_new_base_temperature():
    params = LettuceThermalDevelopmentParams(
        lettuce_base_temperature_st=4.1,
        lettuce_base_temperature_tc=6.1,
        lettuce_thermal_requirement_st=20.0,
        lettuce_thermal_requirement_tc=1000.0,
    )
    clock = LettuceThermalDevelopment(params=params)
    result = clock.update(24.1)  # 20.0 GDD for ST, meets the 20.0 requirement exactly
    assert result["stage"] == "TC"
    assert result["stage_accumulated_gdd"] == 0.0
    assert result["development_fraction"] == 0.0
    assert clock.params.stage_params("TC").base_temperature_c == 6.1


def test_transition_from_tc_to_harvest_marks_harvest_ready():
    params = LettuceThermalDevelopmentParams(
        lettuce_base_temperature_st=4.1,
        lettuce_base_temperature_tc=6.1,
        lettuce_thermal_requirement_st=0.0,
        lettuce_thermal_requirement_tc=10.0,
    )
    clock = LettuceThermalDevelopment(params=params)
    clock.update(6.1)  # ST requirement is 0, immediately transitions to TC
    result = clock.update(16.1)  # 10.0 GDD for TC, meets the 10.0 requirement exactly
    assert result["stage"] == "HARVEST"
    assert result["harvest_ready"] is True
    assert result["development_fraction"] == 1.0


def test_accumulated_gdd_sums_across_multiple_days():
    params = LettuceThermalDevelopmentParams(lettuce_thermal_requirement_st=1000.0)
    clock = LettuceThermalDevelopment(params=params)
    clock.update(14.1)  # 10.0 GDD
    result = clock.update(19.1)  # 15.0 GDD
    assert math.isclose(result["stage_accumulated_gdd"], 25.0, rel_tol=1e-9)
    assert math.isclose(result["total_gdd"], 25.0, rel_tol=1e-9)


def test_development_fraction_is_capped_at_one():
    params = LettuceThermalDevelopmentParams(lettuce_thermal_requirement_st=10.0, lettuce_thermal_requirement_tc=1000.0)
    clock = LettuceThermalDevelopment(params=params)
    result = clock.update(104.1)  # far above the ST requirement in a single day
    assert result["development_fraction"] <= 1.0


def test_st_and_tc_use_different_base_temperatures():
    params = LettuceThermalDevelopmentParams(
        lettuce_base_temperature_st=4.1,
        lettuce_base_temperature_tc=6.1,
        lettuce_thermal_requirement_st=0.0,
        lettuce_thermal_requirement_tc=1000.0,
    )
    clock = LettuceThermalDevelopment(params=params)
    # 5.0 is above the ST base temperature (4.1), so this day's GDD is still
    # computed under ST before the zero-requirement transition to TC fires.
    result = clock.update(5.0)
    assert result["stage"] == "TC"
    assert math.isclose(result["daily_gdd"], 0.9, rel_tol=1e-9)


def test_stage_gdd_resets_after_final_transplant():
    params = LettuceThermalDevelopmentParams(lettuce_thermal_requirement_st=5.0, lettuce_thermal_requirement_tc=1000.0)
    clock = LettuceThermalDevelopment(params=params)
    clock.update(9.1)  # 5.0 GDD, meets ST requirement, transitions to TC
    assert clock.stage == "TC"
    assert clock.accumulated_gdd == 0.0


def test_harvest_ready_defaults_to_false_before_completion():
    clock = LettuceThermalDevelopment()
    result = clock.update(10.0)
    assert result["harvest_ready"] is False


def test_update_after_harvest_stays_at_harvest_with_zero_daily_gdd():
    params = LettuceThermalDevelopmentParams(lettuce_thermal_requirement_st=0.0, lettuce_thermal_requirement_tc=0.0)
    clock = LettuceThermalDevelopment(params=params)
    clock.update(20.0)  # ST -> TC (requirement 0.0)
    clock.update(20.0)  # TC -> HARVEST (requirement 0.0)
    result = clock.update(20.0)
    assert result["stage"] == "HARVEST"
    assert result["daily_gdd"] == 0.0
    assert result["harvest_ready"] is True
