"""Thermal-time (growing-degree-day) phenology clock for hydroponic curly lettuce.

Source attribution: `GDD-001`. The defaults are attributed to the four-cycle
mean basal temperatures and thermal requirements in Janaina Goncalves da
Silva's 2022 UFSC thesis; the source locations and four-cycle calculation must
be verified against the original thesis before treating them as literature
parameters.

This module is a development/phenology clock, not a biomass model: it tracks
which stage the crop is in and how close it is to completing that stage's
thermal requirement. It is independent from the Van Henten biomass ODE in
project.models.lettuce; `development_fraction` can optionally be read by a
biomass model, but this module never computes biomass itself, since the
source paper explicitly states GDD accounts for temperature only and not
radiation, humidity, photoperiod, or root temperature.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Stage = Literal["ST", "TC", "HARVEST"]


@dataclass
class LettuceThermalStageParams:
    base_temperature_c: float
    thermal_requirement_gdd: float


@dataclass
class LettuceThermalDevelopmentParams:
    """Configurable calibration parameters, not hard-coded constants."""

    lettuce_base_temperature_st: float = 4.1
    lettuce_base_temperature_tc: float = 6.1
    lettuce_thermal_requirement_st: float = 398.67
    lettuce_thermal_requirement_tc: float = 472.79

    def stage_params(self, stage: Stage) -> LettuceThermalStageParams:
        if stage == "ST":
            return LettuceThermalStageParams(self.lettuce_base_temperature_st, self.lettuce_thermal_requirement_st)
        if stage == "TC":
            return LettuceThermalStageParams(self.lettuce_base_temperature_tc, self.lettuce_thermal_requirement_tc)
        raise ValueError(f"stage {stage!r} has no thermal parameters (harvest reached)")


def daily_gdd(tmean_c: float, base_temperature_c: float) -> float:
    """Growing degree days accumulated in one day; negative development is not allowed."""
    return max(0.0, tmean_c - base_temperature_c)


@dataclass
class LettuceThermalDevelopment:
    """Stateful day-by-day thermal-time phenology clock for one crop cycle."""

    params: LettuceThermalDevelopmentParams = field(default_factory=LettuceThermalDevelopmentParams)
    stage: Stage = "ST"
    accumulated_gdd: float = 0.0
    total_gdd: float = 0.0

    def update(self, mean_air_temperature_c: float) -> dict:
        """Advance the clock by one day and return the current phenology state."""
        if self.stage == "HARVEST":
            return {
                "stage": self.stage,
                "daily_gdd": 0.0,
                "stage_accumulated_gdd": self.accumulated_gdd,
                "total_gdd": self.total_gdd,
                "development_fraction": 1.0,
                "harvest_ready": True,
            }

        stage_params = self.params.stage_params(self.stage)
        gdd_today = daily_gdd(mean_air_temperature_c, stage_params.base_temperature_c)
        self.accumulated_gdd += gdd_today
        self.total_gdd += gdd_today

        if stage_params.thermal_requirement_gdd <= 0.0:
            development_fraction = 1.0
        else:
            development_fraction = min(self.accumulated_gdd / stage_params.thermal_requirement_gdd, 1.0)

        if self.stage == "ST" and self.accumulated_gdd >= stage_params.thermal_requirement_gdd:
            self.stage = "TC"
            self.accumulated_gdd = 0.0
            development_fraction = 0.0
        elif self.stage == "TC" and self.accumulated_gdd >= stage_params.thermal_requirement_gdd:
            self.stage = "HARVEST"
            development_fraction = 1.0

        return {
            "stage": self.stage,
            "daily_gdd": gdd_today,
            "stage_accumulated_gdd": self.accumulated_gdd,
            "total_gdd": self.total_gdd,
            "development_fraction": development_fraction,
            "harvest_ready": self.stage == "HARVEST",
        }
