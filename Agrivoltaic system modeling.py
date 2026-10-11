"""
Agrivoltaic system modeling
===========================

Irradiance at crop level between rows
"""

# %%
# This example demonstrates how to calculate power output for a bifacial
# agriPV plant as well as calculating the irradiance at crop level
# using pvlib's infinite sheds model.
# For an overview of agrivPV concepts and performance, the reader
# is referred to :doi:`10.69766/XAEU5008`.
#
# This gallery example is based on an actual AgriPV plant, namely
# European Energy's Flakkebjerg AgriPV site.
#
# The first steps are to define the plant location and to calculate solar
# position and clearsky irradiance for a single day as an example.
#
# .. figure:: ../../_images/agrivoltaics_system.jpg
#    :align: center
#    :width: 75%
#    :alt: Photo of the Flakkebjerg agriPV system
#
#    Photo of an agriPV system.
#    *Source: Adam R. Jensen*

import os

import pvlib
import pandas as pd
from numpy import array, exp
from pvlib.tools import cosd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from project.models.conversions import dli_from_timeseries
from project.models.lettuce import simulate_growth_timeseries
from project.models.radiation import crop_and_pv_irradiance, pvwatts_power
from project.scenarios.run_timeseries import run_timeseries_pipeline


def run_control_pipeline(weather, location=None, **kwargs):
    """Run the short-interval controller and return timestep plus daily results.

    This public entry point accepts a weather DataFrame with ``ghi``, ``dhi`` and
    ``dni`` columns. It is intended for future sensor or forecast data while the
    example below continues to generate the current demonstration plots.
    """
    if location is None:
        location = pvlib.location.Location(
            latitude=-27.5949,
            longitude=-48.5480,
            tz='America/Sao_Paulo',
        )
    return run_timeseries_pipeline(weather, location, **kwargs)

# -----------------------------------------------------------------------------
# Van Henten lettuce growth model adapted for the agriPV crop layer
# -----------------------------------------------------------------------------

# Constants
C_CH2O = 30 / 44
C_YF = 0.8
C_GR_MAX = 5e-6
C_GAMMA = 1.1981
C_Q10_GR = 1.6
C_RESP_SHT = 3.47e-7
C_RESP_RT = 1.16e-7
C_Q10_RESP = 2.0
C_TAU = 0.15
C_K = 0.9
C_LAR = 75e-3
C_OMEGA = 1.83e-3
C_GGAMMA = 40
C_Q10_GGAMMA = 2
C_EPSILON = 17e-6
G_BND = 0.00071987
G_STM = 0.005
C_CAR1 = -1.32e-5
C_CAR2 = 5.94e-4
C_CAR3 = -2.64e-3
DRY_TO_WET_RATIO = 0.1
RATIO_SDW_NSDW = array([0.3, 0.7])


def get_default_constants(filter_: list = []):
    consts = {key: value for key, value in globals().items() if key.isupper()}
    if filter_:
        return {key: value for key, value in consts.items() if key in filter_}
    return consts


def lettuce_growth_model(_: int, x: tuple[float, float], u: tuple[float, float, float], c: dict[str, float] = {}) -> tuple[float, float]:
    """Overall dynamic growth model."""
    dx_sdw_dt, dx_nsdw_dt, __ = _lettuce_growth_model(_, x, u, **c)
    return dx_sdw_dt, dx_nsdw_dt


def _lettuce_growth_model(_ : int, x: tuple[float, float], u: tuple[float, float, float], **kwargs) -> tuple[float, float, dict]:
    x_sdw, x_nsdw = x
    u_T, u_par, u_co2 = u
    consts = get_default_constants()
    consts.update(kwargs)

    r_gr = get_r_gr(
        x_sdw,
        x_nsdw,
        u_T,
        consts["C_GR_MAX"],
        consts["C_GAMMA"],
        consts["C_Q10_GR"],
    )

    gamma = get_ggamma(
        u_T,
        consts["C_GGAMMA"],
        consts["C_Q10_GGAMMA"],
    )
    epsilon = get_epsilon(
        u_co2,
        gamma,
        consts["C_EPSILON"],
    )
    g_co2 = get_g_co2(
        get_g_car(
            u_T,
            consts["C_CAR1"],
            consts["C_CAR2"],
            consts["C_CAR3"],
        ),
        consts["G_BND"],
        consts["G_STM"],
    )
    f_phot_max = get_f_phot_max(
        u_par,
        u_co2,
        epsilon,
        g_co2,
        gamma,
        consts["C_OMEGA"],
    )
    f_phot = get_f_phot(
        x_sdw,
        f_phot_max,
        consts["C_K"],
        consts["C_LAR"],
        consts["C_TAU"],
    )
    f_resp = get_f_resp(
        x_sdw,
        u_T,
        consts["C_RESP_SHT"],
        consts["C_TAU"],
        consts["C_RESP_RT"],
        consts["C_Q10_RESP"],
    )
    dx_sdw_dt = predict_x_sdw(x_sdw, r_gr)
    dx_nsdw_dt = predict_x_nsdw(
        x_sdw,
        r_gr,
        f_phot,
        f_resp,
        consts["C_CH2O"],
        consts["C_YF"],
    )
    return dx_sdw_dt, dx_nsdw_dt, locals()


def predict_x_sdw(x_sdw: float, r_gr: float) -> float:
    return r_gr * x_sdw


def predict_x_nsdw(
    x_sdw: float,
    r_gr: float,
    f_phot: float,
    f_resp: float,
    c_ch2o: float = C_CH2O,
    c_yf: float = C_YF,
) -> float:
    return (
        c_ch2o * f_phot
        - r_gr * x_sdw
        - f_resp
        - ((1 - c_yf) / c_yf) * r_gr * x_sdw
    )


def get_r_gr(
    x_sdw: float,
    x_nsdw: float,
    u_T: float,
    c_gr_max: float = C_GR_MAX,
    c_gamma: float = C_GAMMA,
    c_Q10_gr: float = C_Q10_GR,
) -> float:
    return (
        c_gr_max
        * (x_nsdw / (c_gamma * x_sdw + x_nsdw))
        * c_Q10_gr ** ((u_T - 20) / 10)
    )


def get_f_resp(
    x_sdw: float,
    u_T: float,
    c_resp_sht: float = C_RESP_SHT,
    c_tau: float = C_TAU,
    c_resp_rt: float = C_RESP_RT,
    c_Q10_resp: float = C_Q10_RESP,
) -> float:
    return (
        c_resp_sht * (1 - c_tau) * x_sdw + c_resp_rt * c_tau * x_sdw
    ) * c_Q10_resp ** ((u_T - 25) / 10)


def get_f_phot(
    x_sdw: float,
    f_phot_max: float,
    c_K: float = C_K,
    c_lar: float = C_LAR,
    c_tau: float = C_TAU,
) -> float:
    return (1 - exp(-c_K * c_lar * (1 - c_tau) * x_sdw)) * f_phot_max


def get_f_phot_max(
    u_par: float,
    u_co2: float,
    epsilon: float,
    g_co2: float,
    gamma: float,
    c_omega: float = C_OMEGA,
) -> float:
    return (epsilon * u_par * g_co2 * c_omega * (u_co2 - gamma)) / (
        epsilon * u_par + g_co2 * c_omega * (u_co2 - gamma)
    )


def get_ggamma(
    u_T: float,
    c_Gamma: float = C_GGAMMA,
    c_Q10_Gamma: float = C_Q10_GGAMMA,
) -> float:
    return c_Gamma * c_Q10_Gamma ** ((u_T - 20) / 10)


def get_epsilon(
    u_co2: float,
    gamma: float,
    c_epsilon: float = C_EPSILON,
) -> float:
    return c_epsilon * ((u_co2 - gamma) / (u_co2 + 2 * gamma))


def get_g_co2(
    g_car: float,
    g_bdn: float = G_BND,
    g_stm: float = G_STM,
) -> float:
    return 1 / ((1 / g_bdn) + (1 / g_stm) + (1 / g_car))


def get_g_car(
    u_T: float,
    c_car1: float = C_CAR1,
    c_car2: float = C_CAR2,
    c_car3: float = C_CAR3,
):
    return c_car1 * u_T**2 + c_car2 * u_T + c_car3


def simulate_lettuce_growth(
    times,
    crop_irradiance,
    temp_air_c,
    co2_ppm=420.0,
    x_sdw0=8.0,
    x_nsdw0=3.0,
    par_conversion=0.45,
):
    """Run the Van Henten lettuce growth model using crop-level irradiance.

    Parameters
    ----------
    times : pandas.DatetimeIndex
        Time index for the simulation.
    crop_irradiance : pandas.Series or array-like
        Either crop-level shortwave irradiance in W/m^2 or already converted PAR
        values. Set par_conversion=1.0 if the input is already PAR (W/m^2).
    temp_air_c : scalar or pandas.Series
        Air temperature in degC.
    co2_ppm : scalar or pandas.Series
        CO2 concentration in ppm.
    par_conversion : float
        Fraction used to convert shortwave crop irradiance to PAR. A value of
        0.45-0.5 is a typical first-order approximation for terrestrial crops.
    """
    crop_irradiance = pd.Series(crop_irradiance, index=times)
    temp_series = pd.Series(temp_air_c, index=times)
    co2_series = pd.Series(co2_ppm, index=times)

    crop_par = crop_irradiance * par_conversion
    x_sdw = float(x_sdw0)
    x_nsdw = float(x_nsdw0)
    records = []

    dt_s = 60.0

    for time, par, temp, co2 in zip(times, crop_par, temp_series, co2_series):
        par_wm2 = float(par)
        temp_c = float(temp)
        co2_value = float(co2)

        if pd.isna(par_wm2):
            par_wm2 = 0.0
        if pd.isna(temp_c):
            temp_c = 25.0
        if pd.isna(co2_value):
            co2_value = 420.0

        par_wm2 = max(par_wm2, 0.0)

        dx_sdw, dx_nsdw = lettuce_growth_model(
            0,
            (x_sdw, x_nsdw),
            (temp_c, par_wm2, co2_value),
        )

        # Simple restriction: negative net growth at night is not allowed to keep
        # the biomass series stable for the day-scale demonstration.
        if par_wm2 <= 0.0:
            dx_sdw = max(dx_sdw, 0.0)
            dx_nsdw = max(dx_nsdw, 0.0)

        x_sdw = max(x_sdw + dx_sdw * dt_s, 0.0)
        x_nsdw = max(x_nsdw + dx_nsdw * dt_s, 0.0)

        records.append({
            'time': time,
            'x_sdw': x_sdw,
            'x_nsdw': x_nsdw,
            'total_dry_biomass': x_sdw + x_nsdw,
            'u_par': par_wm2,
            'temp_air': temp_c,
            'co2_ppm': co2_value,
        })

    growth_df = pd.DataFrame(records).set_index('time')
    return growth_df


def load_field_data(file_path, time_column='time', par_column=None,
                   temp_column='temperature_c', co2_column='co2_ppm',
                   par_unit='auto'):
    """Load field data from CSV/Excel and prepare a ready-to-use dataframe.

    Supported inputs:
    - CSV or Excel file
    - column with timestamps
    - optional PAR or irradiance column
    - temperature and CO2 columns

    par_unit can be 'auto', 'w_m2', or 'umol_m2_s'.
    """
    if file_path.lower().endswith('.csv'):
        df = pd.read_csv(file_path)
    elif file_path.lower().endswith(('.xls', '.xlsx')):
        df = pd.read_excel(file_path)
    else:
        raise ValueError('Unsupported file type. Use .csv, .xlsx, or .xls.')

    if time_column not in df.columns:
        raise ValueError(f"Column '{time_column}' not found in the file.")

    df = df.copy()
    df[time_column] = pd.to_datetime(df[time_column])
    df = df.set_index(time_column)

    if par_column is not None and par_column in df.columns:
        par_series = df[par_column].astype(float)

        if par_unit == 'auto':
            # Heuristic: if values look obviously larger than 2000, assume umol/m2/s
            if par_series.abs().median() > 2000:
                par_unit = 'umol_m2_s'
            else:
                par_unit = 'w_m2'

        if par_unit == 'umol_m2_s':
            par_series = par_series / 2.04
        elif par_unit == 'w_m2':
            par_series = par_series
        else:
            raise ValueError("par_unit must be 'auto', 'w_m2', or 'umol_m2_s'.")

        df['crop_irradiance_w_m2'] = par_series.clip(lower=0)
    else:
        df['crop_irradiance_w_m2'] = 0.0

    if temp_column in df.columns:
        df['temp_air_c'] = pd.to_numeric(df[temp_column], errors='coerce')
    else:
        df['temp_air_c'] = 25.0

    if co2_column in df.columns:
        df['co2_ppm'] = pd.to_numeric(df[co2_column], errors='coerce').fillna(420.0)
    else:
        df['co2_ppm'] = 420.0

    df = df.sort_index()
    return df


def run_field_growth_model(file_path, time_column='time', par_column=None,
                          temp_column='temperature_c', co2_column='co2_ppm',
                          par_unit='auto', x_sdw0=8.0, x_nsdw0=3.0,
                          par_conversion=0.45):
    """Convenience wrapper: load real field data and run the lettuce growth model."""
    field_df = load_field_data(
        file_path=file_path,
        time_column=time_column,
        par_column=par_column,
        temp_column=temp_column,
        co2_column=co2_column,
        par_unit=par_unit,
    )

    growth_df = simulate_lettuce_growth(
        times=field_df.index,
        crop_irradiance=field_df['crop_irradiance_w_m2'],
        temp_air_c=field_df['temp_air_c'],
        co2_ppm=field_df['co2_ppm'],
        x_sdw0=x_sdw0,
        x_nsdw0=x_nsdw0,
        par_conversion=par_conversion,
    )

    growth_df = growth_df.join(
        field_df[['crop_irradiance_w_m2', 'temp_air_c', 'co2_ppm']].rename(
            columns={
                'crop_irradiance_w_m2': 'crop_irradiance_w_m2_field',
                'temp_air_c': 'temp_air_c_field',
                'co2_ppm': 'co2_ppm_field',
            }
        ),
        how='left',
    )
    return field_df, growth_df


# sphinx_gallery_thumbnail_path = '_images/agrivoltaics_system.jpg'

output_dir = os.path.dirname(os.path.abspath(__file__))
os.makedirs(output_dir, exist_ok=True)

# Florianópolis, Santa Catarina, Brazil
location = pvlib.location.Location(latitude=-27.5949, longitude=-48.5480, tz='America/Sao_Paulo')

times = pd.date_range('2020-12-21', periods=24*60, freq='1min', tz='America/Sao_Paulo')

solpos = location.get_solarposition(times)

clearsky = location.get_clearsky(times, model='ineichen')

# %%
# Next, we need to define the plant layout:

height = 2.6  # [m] height of torque above ground
pitch = 12  # [m] row spacing
row_width = 2 * 2.384  # [m] two modules in portrait, each 2 m long
gcr = row_width / pitch  # ground coverage ratio [unitless]
axis_azimuth = 0  # [degrees] north-south tracking axis
max_angle = 55  # [degrees] mechanical single-axis tracking limit in either direction

# %%
# Before running the infinite sheds model, we need to know the orientation
# of the trackers. For a single-axis tracker, this can be calculated as:

tracking_orientations = pvlib.tracking.singleaxis(
    apparent_zenith=solpos['apparent_zenith'],
    apparent_azimuth=solpos['azimuth'],
    axis_azimuth=axis_azimuth,
    max_angle=max_angle,
    backtrack=True,
    gcr=gcr,
)

# %%
# For agrivPV systems, the local albedo is dependent on crop growth and thus
# changes throughout the seasons. In this example, we only simulate one
# day and thus use a constant value. Similarly, we will assume a constant
# air temperature to avoid getting external data. Both albedo and air
# temperature could be defined as Series with the same index as used for the
# solar position calculations.

albedo = 0.18  # [unitless], typical for a vegetated ground in southern Brazil
temp_air = 26  # [degrees C], representative daytime air temperature in Florianópolis

# %%
# Calculate crop-level and module irradiance through the reusable project wrapper.
# Replacing clearsky with measured or forecast GHI/DHI/DNI here later propagates
# clouds automatically through the same pipeline.
irradiance = crop_and_pv_irradiance(
    solar_position=solpos,
    weather=clearsky,
    orientation=tracking_orientations,
    gcr=gcr,
    height_m=height,
    pitch_m=pitch,
    albedo=albedo,
    bifaciality=0.7,
)

# %%
# Once the in-plane irradiance is known, we can estimate the PV array power.
# For simplicity, we use the PVWatts model:

# UFSC pilot rating from the project brief; replace with subzone ratings later.
pdc0 = 8000  # [W] subsystem 2A-2B-2C nameplate power

gamma_pdc = -0.004  # [1/degrees C]

power_dc = pvwatts_power(
    irradiance=irradiance['poa_global_w_m2'],
    temp_air_c=temp_air,
    pdc0_w=pdc0,
    gamma_pdc=gamma_pdc,
)

power_ax = power_dc.divide(1000).plot(figsize=(10, 6))
power_ax.set_ylabel('DC power [kW]')
power_ax.set_ylim(0, max(1.1, power_dc.max() / 1000 * 1.15))
plt.tight_layout()
plt.savefig(os.path.join(output_dir, 'agrivoltaic_power.png'), dpi=200)
plt.close()

crop_avg_irradiance = irradiance['crop_ghi_w_m2']

# -----------------------------------------------------------------------------
# Integrate crop growth model for lettuce using the irradiance at crop level
# -----------------------------------------------------------------------------
# Convert crop-level shortwave irradiation to PAR approximation (approx. 45% of solar radiation)
# and use the local air temperature as canopy temperature proxy for the model.
lettuce_growth = simulate_growth_timeseries(
    times=times,
    par_wm2=crop_avg_irradiance * 0.45,
    temp_air_c=pd.Series(temp_air, index=times),
    co2_ppm=420.0,
    x_sdw0=8.0,
    x_nsdw0=3.0,
)

daily_dli = dli_from_timeseries(irradiance['crop_ppfd_umol_m2_s'])
print('Daily crop DLI [mol/m^2/day]:')
print(daily_dli.round(3).to_string())

fig, ax = plt.subplots(figsize=(10, 6))
clearsky['ghi'].plot(ax=ax, label='Horizontal irradiance above panels')
crop_avg_irradiance.plot(ax=ax, label='Horizontal irradiance at crop level')
ax.legend(loc='upper center')
ax.set_ylabel('Irradiance [W/m$^2$]')
ax.set_ylim(-10, max(1100, clearsky['ghi'].max() * 1.1, crop_avg_irradiance.max() * 1.1))
plt.tight_layout()
fig.savefig(os.path.join(output_dir, 'agrivoltaic_crop_irradiance.png'), dpi=200)
plt.close(fig)

# Biomass growth plot for lettuce under the agriPV crop layer
fig_bio, ax_bio = plt.subplots(figsize=(10, 6))
lettuce_growth['total_dry_biomass'].plot(ax=ax_bio, label='Total dry biomass')
ax_bio.set_ylabel('Dry biomass [g m$^{-2}$]')
ax_bio.set_xlabel('Time')
ax_bio.legend()
plt.tight_layout()
fig_bio.savefig(os.path.join(output_dir, 'lettuce_growth.png'), dpi=200)
plt.close(fig_bio)