"""Van Henten-style lettuce growth model.

This keeps the implementation compatible with scipy.integrate.solve_ivp.
Literature context is registered as VAN-001; the default parameters and
initial state have not been reconciled coefficient-by-coefficient.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np
import pandas as pd

from project.models.conversions import PPFD_PER_PAR_WM2


MODEL_TEMPERATURE_RANGE_C = (5.0, 40.0)  # VAN-001 attribution; polynomial validity range remains unverified.
# CROP-002: provisional model initialization; it is not a transplant measurement.
DEFAULT_INITIAL_STRUCTURAL_DRY_BIOMASS_G_M2 = 8.0
DEFAULT_INITIAL_NONSTRUCTURAL_DRY_BIOMASS_G_M2 = 3.0


def _clamp_model_temperature(u_t: float) -> float:
    """Restrict temperature to the domain where the empirical conductance term is valid.

    The Van Henten-inspired conductance polynomial in this implementation is only
    physically meaningful between 5 C and 40 C. Outside that band we keep the model
    finite and non-productive instead of letting negative conductance or a division-by-
    zero event destabilize the crop dynamics.
    """
    return float(np.clip(u_t, MODEL_TEMPERATURE_RANGE_C[0], MODEL_TEMPERATURE_RANGE_C[1]))


@dataclass
class LettuceParams:
    c_ch2o: float = 30.0 / 44.0  # CHEM-001; stoichiometric mass ratio, not a fitted parameter.
    c_yf: float = 0.8  # LETTUCE-001; Sweeney attribution remains unverified.
    c_gr_max: float = 5e-6  # LETTUCE-002; van Holsteijn attribution remains unverified.
    c_gamma: float = 1.1981  # VAN-001; primary-paper location is not yet verified.
    c_q10_gr: float = 1.6  # VAN-001; primary-paper location is not yet verified.
    c_resp_sht: float = 3.47e-7  # VAN-001; primary-paper location is not yet verified.
    c_resp_rt: float = 1.16e-7  # VAN-001; primary-paper location is not yet verified.
    c_q10_resp: float = 2.0  # VAN-001; primary-paper location is not yet verified.
    c_tau: float = 0.14  # LETTUCE-005 hydroponic proxy; not calibrated for site cultivar.
    c_k: float = 0.9  # LETTUCE-003; primary-source location is not yet verified.
    c_lar: float = 75e-3  # LETTUCE-003; primary-source location is not yet verified.
    c_omega: float = 1.83e-3  # VAN-001; primary-paper location is not yet verified.
    c_ggamma: float = 40.0  # VAN-001; primary-paper location is not yet verified.
    c_q10_ggamma: float = 2.0  # VAN-001; primary-paper location is not yet verified.
    c_epsilon: float = 17e-6  # VAN-001; primary-paper location is not yet verified.
    g_bnd: float = 0.00071987  # VAN-001; primary-paper location is not yet verified.
    g_stm: float = 0.005  # VAN-001; primary-paper location is not yet verified.
    c_car1: float = -1.32e-5  # VAN-001; primary-paper location is not yet verified.
    c_car2: float = 5.94e-4  # VAN-001; primary-paper location is not yet verified.
    c_car3: float = -2.64e-3  # VAN-001; primary-paper location is not yet verified.
    # TEMP-001 (EXPLORATORY, OFF by default): optional trapezoidal air-temperature
    # limitation of canopy assimilation. Known limitation (CROP-003): the VAN-001
    # structure gains MORE dry mass in cool air, opposite to measured lettuce
    # growth (LETTUCE-006). The cardinal values below are NOT evidence of zero
    # assimilation: 6.1 C is a phenology (GDD) base temperature and 32 C is only
    # the highest tested air temperature in LETTUCE-009. Use for sensitivity runs
    # only; a validated fix is pending (LETTUCE-010).
    apply_temperature_factor: bool = False
    t_min_growth_c: float = 6.1  # GDD-001 phenology base temperature, NOT a measured assimilation limit.
    t_opt_low_c: float = 22.0  # LETTUCE-006 / LETTUCE-007: growth-rate maximum near 22 C.
    t_opt_high_c: float = 24.0  # LETTUCE-008 / LETTUCE-009: dry-mass / leaf-expansion optimum near 24 C air.
    t_max_growth_c: float = 32.0  # LETTUCE-009 highest TESTED air temperature, NOT a measured zero point.


def get_r_gr(x_sdw: float, x_nsdw: float, u_t: float, p: LettuceParams | None = None) -> float:
    """Return the saturating structural growth-rate equation attributed to VAN-001."""
    p = p or LettuceParams()
    return (
        p.c_gr_max
        * (x_nsdw / (p.c_gamma * x_sdw + x_nsdw))
        * (p.c_q10_gr ** ((u_t - 20.0) / 10.0))
    )


def get_ggamma(u_t: float, p: LettuceParams | None = None) -> float:
    """Return the temperature-adjusted compensation point attributed to VAN-001."""
    p = p or LettuceParams()
    return p.c_ggamma * (p.c_q10_ggamma ** ((u_t - 20.0) / 10.0))


def get_epsilon(u_co2: float, gamma: float, p: LettuceParams | None = None) -> float:
    """Return the CO2 response equation attributed to VAN-001."""
    p = p or LettuceParams()
    return p.c_epsilon * ((u_co2 - gamma) / (u_co2 + 2.0 * gamma))


def get_g_car(u_t: float, p: LettuceParams | None = None) -> float:
    """Return the clamped carboxylation conductance polynomial attributed to VAN-001."""
    p = p or LettuceParams()
    u_t = _clamp_model_temperature(u_t)
    return p.c_car1 * u_t**2 + p.c_car2 * u_t + p.c_car3


def get_g_co2(g_car: float, p: LettuceParams | None = None) -> float:
    """Combine conductances as attributed to VAN-001."""
    p = p or LettuceParams()
    if g_car <= 0.0:
        return 0.0
    return 1.0 / ((1.0 / p.g_bnd) + (1.0 / p.g_stm) + (1.0 / g_car))


def get_f_resp(x_sdw: float, u_t: float, p: LettuceParams | None = None) -> float:
    """Return the shoot/root maintenance respiration equation attributed to VAN-001."""
    p = p or LettuceParams()
    return (
        (p.c_resp_sht * (1.0 - p.c_tau) * x_sdw + p.c_resp_rt * p.c_tau * x_sdw)
        * (p.c_q10_resp ** ((u_t - 25.0) / 10.0))
    )


def get_f_phot_max(u_par: float, u_co2: float, epsilon: float, g_co2: float, gamma: float, p: LettuceParams | None = None) -> float:
    """Return the CO2-limited maximum photosynthesis equation attributed to VAN-001."""
    p = p or LettuceParams()
    numerator = epsilon * u_par * g_co2 * p.c_omega * (u_co2 - gamma)
    denominator = epsilon * u_par + g_co2 * p.c_omega * (u_co2 - gamma)
    return numerator / denominator


def get_f_temp(u_t: float, p: LettuceParams | None = None) -> float:
    """Return the TEMP-001 trapezoidal temperature factor (0..1) for assimilation.

    See references/TEMP-001.md for evidence and limitations.

    0 at or below ``t_min_growth_c``, rising linearly to 1 at ``t_opt_low_c``,
    1 up to ``t_opt_high_c``, falling linearly to 0 at ``t_max_growth_c``.
    Returns 1.0 when ``apply_temperature_factor`` is False (the default).
    Exploratory sensitivity setting only; endpoints are not measured zero points.
    """
    p = p or LettuceParams()
    if not p.apply_temperature_factor:
        return 1.0
    if not (p.t_min_growth_c < p.t_opt_low_c <= p.t_opt_high_c < p.t_max_growth_c):
        raise ValueError(
            "temperature factor requires t_min < t_opt_low <= t_opt_high < t_max"
        )
    if u_t <= p.t_min_growth_c or u_t >= p.t_max_growth_c:
        return 0.0
    if u_t < p.t_opt_low_c:
        return (u_t - p.t_min_growth_c) / (p.t_opt_low_c - p.t_min_growth_c)
    if u_t <= p.t_opt_high_c:
        return 1.0
    return (p.t_max_growth_c - u_t) / (p.t_max_growth_c - p.t_opt_high_c)


def get_f_phot(x_sdw: float, f_phot_max: float, p: LettuceParams | None = None) -> float:
    """Apply the canopy light-interception equation attributed to LETTUCE-004."""
    p = p or LettuceParams()
    return (1.0 - np.exp(-p.c_k * p.c_lar * (1.0 - p.c_tau) * x_sdw)) * f_phot_max


def lettuce_rhs(t: float, state: Sequence[float], u: Sequence[float], p: LettuceParams | None = None):
    """Right-hand side for scipy.integrate.solve_ivp.

    state = [x_sdw, x_nsdw]
    u = [temp_air_c, par_wm2, co2_ppm]

    The equation structure is attributed to VAN-001; the yield-factor term is
    separately attributed to LETTUCE-001. Coefficient-level source locations
    remain unverified in those records.
    """
    p = p or LettuceParams()
    x_sdw, x_nsdw = state
    u_t, u_par, u_co2 = u

    r_gr = get_r_gr(x_sdw, x_nsdw, u_t, p)
    gamma = get_ggamma(u_t, p)
    epsilon = get_epsilon(u_co2, gamma, p)
    g_car = get_g_car(u_t, p)
    g_co2 = get_g_co2(g_car, p)
    f_phot_max = get_f_phot_max(u_par, u_co2, epsilon, g_co2, gamma, p)
    f_phot = get_f_phot(x_sdw, f_phot_max, p) * get_f_temp(u_t, p)
    f_resp = get_f_resp(x_sdw, u_t, p)

    dx_sdw = r_gr * x_sdw
    dx_nsdw = p.c_ch2o * f_phot - r_gr * x_sdw - f_resp - ((1.0 - p.c_yf) / p.c_yf) * r_gr * x_sdw
    return [dx_sdw, dx_nsdw]


def simulate_growth_timeseries(
    times,
    par_wm2,
    temp_air_c,
    co2_ppm=420.0,
    x_sdw0=DEFAULT_INITIAL_STRUCTURAL_DRY_BIOMASS_G_M2,
    x_nsdw0=DEFAULT_INITIAL_NONSTRUCTURAL_DRY_BIOMASS_G_M2,
    par_to_ppfd_factor: float = PPFD_PER_PAR_WM2,
    params: LettuceParams | None = None,
    max_gap_periods: int = 4,
    integration_step_seconds: float = 900.0,
):
    """Integrate biomass over an arbitrary, timezone-aware time series.

    ``par_wm2`` is PAR energy in W/m². Short internal input gaps are interpolated
    up to ``max_gap_periods``; missing model input beyond that point invalidates
    the biomass state for that timestamp and all subsequent timestamps. The
    model uses fixed-step RK4 integration between observations and carries state
    continuously across day boundaries.
    """
    times = pd.DatetimeIndex(times)
    if times.tz is None:
        raise ValueError("times must be timezone-aware")
    if max_gap_periods < 0:
        raise ValueError("max_gap_periods must be non-negative")
    if not np.isfinite(integration_step_seconds) or integration_step_seconds <= 0.0:
        raise ValueError("integration_step_seconds must be finite and positive")
    raw_par = pd.Series(par_wm2, index=times, dtype=float)
    raw_temp = pd.Series(temp_air_c, index=times, dtype=float)
    raw_co2 = pd.Series(co2_ppm, index=times, dtype=float)
    par = (
        raw_par
        .interpolate(method="time", limit=max_gap_periods, limit_area="inside")
        .clip(lower=0.0)
    )
    temp = raw_temp.interpolate(
        method="time",
        limit=max_gap_periods,
        limit_area="inside",
    )
    co2 = raw_co2.interpolate(
        method="time",
        limit=max_gap_periods,
        limit_area="inside",
    )

    x_sdw, x_nsdw = float(x_sdw0), float(x_nsdw0)
    state_valid = True
    records = []
    for position, timestamp in enumerate(times):
        par_value = float(par.iloc[position])
        temp_value = float(temp.iloc[position])
        co2_value = float(co2.iloc[position])
        input_valid = all(
            np.isfinite(value) for value in (par_value, temp_value, co2_value)
        )
        if not input_valid:
            state_valid = False
        if position > 0 and state_valid:
            start = times[position - 1]
            interval_seconds = (timestamp - start).total_seconds()
            if interval_seconds < 0.0:
                raise ValueError("times must be monotonically increasing")
            if interval_seconds > 0.0:
                start_inputs = (
                    float(temp.iloc[position - 1]),
                    float(par.iloc[position - 1]),
                    float(co2.iloc[position - 1]),
                )
                end_inputs = (temp_value, par_value, co2_value)
                if not all(np.isfinite(value) for value in start_inputs):
                    state_valid = False
                else:
                    elapsed = 0.0
                    while elapsed < interval_seconds:
                        step = min(
                            integration_step_seconds,
                            interval_seconds - elapsed,
                        )
                        fraction_start = elapsed / interval_seconds
                        fraction_mid = (elapsed + step * 0.5) / interval_seconds
                        fraction_end = (elapsed + step) / interval_seconds

                        def inputs_at(fraction: float) -> tuple[float, float, float]:
                            return tuple(
                                start_value
                                + (end_value - start_value) * fraction
                                for start_value, end_value in zip(
                                    start_inputs,
                                    end_inputs,
                                )
                            )

                        state = np.array([x_sdw, x_nsdw], dtype=float)

                        def derivative(
                            state_values: np.ndarray,
                            fraction: float,
                        ) -> np.ndarray:
                            return np.asarray(
                                lettuce_rhs(
                                    elapsed,
                                    state_values,
                                    inputs_at(fraction),
                                    params,
                                ),
                                dtype=float,
                            )

                        k1 = derivative(state, fraction_start)
                        k2 = derivative(
                            np.maximum(state + step * k1 * 0.5, 0.0),
                            fraction_mid,
                        )
                        k3 = derivative(
                            np.maximum(state + step * k2 * 0.5, 0.0),
                            fraction_mid,
                        )
                        k4 = derivative(
                            np.maximum(state + step * k3, 0.0),
                            fraction_end,
                        )
                        state = np.maximum(
                            state + step * (k1 + 2.0 * k2 + 2.0 * k3 + k4) / 6.0,
                            0.0,
                        )
                        x_sdw, x_nsdw = (float(value) for value in state)
                        elapsed += step
        if not state_valid:
            x_sdw = x_nsdw = float("nan")
        records.append({
            "time": timestamp,
            "x_sdw": x_sdw,
            "x_nsdw": x_nsdw,
            "total_dry_biomass": x_sdw + x_nsdw,
            "par_wm2": par_value if np.isfinite(par_value) else float("nan"),
            "ppfd_umol_m2_s": (
                par_value * par_to_ppfd_factor
                if np.isfinite(par_value)
                else float("nan")
            ),
            "temp_air_c": temp_value,
            "co2_ppm": co2_value,
            "input_data_complete": bool(
                np.isfinite(raw_par.iloc[position])
                and np.isfinite(raw_temp.iloc[position])
                and np.isfinite(raw_co2.iloc[position])
            ),
            "model_input_valid": input_valid,
            "biomass_state_valid": state_valid,
            "light_interpolated": bool(
                pd.isna(raw_par.iloc[position])
                and np.isfinite(par_value)
            ),
            "temperature_interpolated": bool(
                pd.isna(raw_temp.iloc[position])
                and np.isfinite(temp_value)
            ),
        })
    return pd.DataFrame(records).set_index("time")
