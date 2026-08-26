"""Van Henten-style lettuce growth model.

This keeps the implementation compatible with scipy.integrate.solve_ivp.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

import numpy as np
import pandas as pd


@dataclass
class LettuceParams:
    c_ch2o: float = 30.0 / 44.0
    c_yf: float = 0.8
    c_gr_max: float = 5e-6
    c_gamma: float = 1.1981
    c_q10_gr: float = 1.6
    c_resp_sht: float = 3.47e-7
    c_resp_rt: float = 1.16e-7
    c_q10_resp: float = 2.0
    c_tau: float = 0.15
    c_k: float = 0.9
    c_lar: float = 75e-3
    c_omega: float = 1.83e-3
    c_ggamma: float = 40.0
    c_q10_ggamma: float = 2.0
    c_epsilon: float = 17e-6
    g_bnd: float = 0.00071987
    g_stm: float = 0.005
    c_car1: float = -1.32e-5
    c_car2: float = 5.94e-4
    c_car3: float = -2.64e-3


def get_r_gr(x_sdw: float, x_nsdw: float, u_t: float, p: LettuceParams | None = None) -> float:
    p = p or LettuceParams()
    return (
        p.c_gr_max
        * (x_nsdw / (p.c_gamma * x_sdw + x_nsdw))
        * (p.c_q10_gr ** ((u_t - 20.0) / 10.0))
    )


def get_ggamma(u_t: float, p: LettuceParams | None = None) -> float:
    p = p or LettuceParams()
    return p.c_ggamma * (p.c_q10_ggamma ** ((u_t - 20.0) / 10.0))


def get_epsilon(u_co2: float, gamma: float, p: LettuceParams | None = None) -> float:
    p = p or LettuceParams()
    return p.c_epsilon * ((u_co2 - gamma) / (u_co2 + 2.0 * gamma))


def get_g_car(u_t: float, p: LettuceParams | None = None) -> float:
    p = p or LettuceParams()
    return p.c_car1 * u_t**2 + p.c_car2 * u_t + p.c_car3


def get_g_co2(g_car: float, p: LettuceParams | None = None) -> float:
    p = p or LettuceParams()
    return 1.0 / ((1.0 / p.g_bnd) + (1.0 / p.g_stm) + (1.0 / g_car))


def get_f_resp(x_sdw: float, u_t: float, p: LettuceParams | None = None) -> float:
    p = p or LettuceParams()
    return (
        (p.c_resp_sht * (1.0 - p.c_tau) * x_sdw + p.c_resp_rt * p.c_tau * x_sdw)
        * (p.c_q10_resp ** ((u_t - 25.0) / 10.0))
    )


def get_f_phot_max(u_par: float, u_co2: float, epsilon: float, g_co2: float, gamma: float, p: LettuceParams | None = None) -> float:
    p = p or LettuceParams()
    numerator = epsilon * u_par * g_co2 * p.c_omega * (u_co2 - gamma)
    denominator = epsilon * u_par + g_co2 * p.c_omega * (u_co2 - gamma)
    return numerator / denominator


def get_f_phot(x_sdw: float, f_phot_max: float, p: LettuceParams | None = None) -> float:
    p = p or LettuceParams()
    return (1.0 - np.exp(-p.c_k * p.c_lar * (1.0 - p.c_tau) * x_sdw)) * f_phot_max


def lettuce_rhs(t: float, state: Sequence[float], u: Sequence[float], p: LettuceParams | None = None):
    """Right-hand side for scipy.integrate.solve_ivp.

    state = [x_sdw, x_nsdw]
    u = [temp_air_c, par_wm2, co2_ppm]
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
    f_phot = get_f_phot(x_sdw, f_phot_max, p)
    f_resp = get_f_resp(x_sdw, u_t, p)

    dx_sdw = r_gr * x_sdw
    dx_nsdw = p.c_ch2o * f_phot - r_gr * x_sdw - f_resp - ((1.0 - p.c_yf) / p.c_yf) * r_gr * x_sdw
    return [dx_sdw, dx_nsdw]


def simulate_growth_timeseries(
    times,
    par_wm2,
    temp_air_c,
    co2_ppm=420.0,
    x_sdw0=8.0,
    x_nsdw0=3.0,
    par_to_ppfd_factor: float = 4.57,
    params: LettuceParams | None = None,
):
    """Integrate biomass over an arbitrary, timezone-aware time series.

    ``par_wm2`` is PAR energy in W/m². Actual elapsed seconds are used between
    samples, so 15-minute, hourly, monthly, and multi-year input series are all
    handled consistently. The state is carried continuously across day boundaries.
    """
    times = pd.DatetimeIndex(times)
    if times.tz is None:
        raise ValueError("times must be timezone-aware")
    par = pd.Series(par_wm2, index=times, dtype=float).fillna(0.0).clip(lower=0.0)
    temp = pd.Series(temp_air_c, index=times, dtype=float).interpolate(limit_direction="both").fillna(25.0)
    co2 = pd.Series(co2_ppm, index=times, dtype=float).interpolate(limit_direction="both").fillna(420.0)

    x_sdw, x_nsdw = float(x_sdw0), float(x_nsdw0)
    records = []
    for position, timestamp in enumerate(times):
        dt_s = 0.0 if position == 0 else max((times[position] - times[position - 1]).total_seconds(), 0.0)
        par_value = float(par.iloc[position])
        dx_sdw, dx_nsdw = lettuce_rhs(
            0.0,
            (x_sdw, x_nsdw),
            (float(temp.iloc[position]), par_value, float(co2.iloc[position])),
            params,
        )
        x_sdw = max(x_sdw + dx_sdw * dt_s, 0.0)
        x_nsdw = max(x_nsdw + dx_nsdw * dt_s, 0.0)
        records.append({
            "time": timestamp,
            "x_sdw": x_sdw,
            "x_nsdw": x_nsdw,
            "total_dry_biomass": x_sdw + x_nsdw,
            "par_wm2": par_value,
            "ppfd_umol_m2_s": par_value * par_to_ppfd_factor,
            "temp_air_c": float(temp.iloc[position]),
            "co2_ppm": float(co2.iloc[position]),
        })
    return pd.DataFrame(records).set_index("time")
