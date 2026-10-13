"""Verify dashboard HTML constants match Python configuration and models."""

import re
import yaml
import pytest

from project.models.lettuce import LettuceParams
from project.models.conversions import PAR_FRACTION, PPFD_PER_PAR_WM2


def load_html_constants():
    """Extract JavaScript constants from agripv_dashboard.html."""
    with open("agripv_dashboard.html") as f:
        html = f.read()

    constants = {}

    # Extract SITE constant
    site_match = re.search(
        r"const SITE = \{ latitude: ([\d.-]+), longitude: ([\d.-]+), utcOffsetHours: ([\d.-]+), altitudeM: ([\d.]+) \}",
        html,
    )
    if site_match:
        constants["site"] = {
            "latitude": float(site_match.group(1)),
            "longitude": float(site_match.group(2)),
            "altitude_m": float(site_match.group(4)),
        }

    # Extract PV constant
    pv_match = re.search(
        r"const PV = \{ heightM: ([\d.]+), pitchM: ([\d.]+), rowWidthM: ([\d.]+), gcr: ([\d.]+), axisAzimuthDeg: ([\d.]+), maxTiltDeg: ([\d.]+), bifaciality: ([\d.]+), albedo: ([\d.]+), pdc0W: ([\d.]+), gammaPdc: ([\d.-]+) \}",
        html,
    )
    if pv_match:
        constants["pv"] = {
            "height_m": float(pv_match.group(1)),
            "pitch_m": float(pv_match.group(2)),
            "gcr": float(pv_match.group(4)),
            "max_tilt_deg": float(pv_match.group(6)),
            "bifaciality": float(pv_match.group(7)),
            "albedo": float(pv_match.group(8)),
            "pdc0_w": float(pv_match.group(9)),
            "gamma_pdc_per_c": float(pv_match.group(10)),
        }

    # Extract PAR constants
    par_match = re.search(r"const PAR_FRACTION = ([\d.]+);", html)
    if par_match:
        constants["par_fraction"] = float(par_match.group(1))

    ppfd_match = re.search(r"const PPFD_PER_PAR_WM2 = ([\d.]+);", html)
    if ppfd_match:
        constants["ppfd_per_par_wm2"] = float(ppfd_match.group(1))

    # Extract LETTUCE constant - simplified; just check key values
    lettuce_match = re.search(r"const LETTUCE = \{(.+?)\}", html)
    if lettuce_match:
        lettuce_str = lettuce_match.group(1)
        constants["lettuce"] = {}
        for key, pattern in [
            ("c_yf", r"cYf: ([\d.]+)"),
            ("c_gr_max", r"cGrMax: ([\d.e\-]+)"),
            ("c_tau", r"cTau: ([\d.]+)"),
            ("c_k", r"cK: ([\d.]+)"),
            ("c_lar", r"cLar: ([\d.e\-]+)"),
            ("c_resp_sht", r"cRespSht: ([\d.e\-]+)"),
            ("c_resp_rt", r"cRespRt: ([\d.e\-]+)"),
            ("c_q10_resp", r"cQ10Resp: ([\d.]+)"),
        ]:
            m = re.search(pattern, lettuce_str)
            if m:
                constants["lettuce"][key] = float(m.group(1))

    return constants


def test_site_constants_match_config():
    """Verify SITE constant in HTML matches project/config/site.yaml."""
    with open("project/config/site.yaml") as f:
        config = yaml.safe_load(f)

    html_consts = load_html_constants()
    assert "site" in html_consts, "SITE constant not found in HTML"

    html_site = html_consts["site"]
    yaml_site = config["site"]

    assert html_site["latitude"] == yaml_site["latitude"], "Latitude mismatch"
    assert html_site["longitude"] == yaml_site["longitude"], "Longitude mismatch"
    assert html_site["altitude_m"] == yaml_site["altitude_m"], "Altitude mismatch"


def test_pv_constants_match_config():
    """Verify PV constant in HTML matches project/config/site.yaml."""
    with open("project/config/site.yaml") as f:
        config = yaml.safe_load(f)

    html_consts = load_html_constants()
    assert "pv" in html_consts, "PV constant not found in HTML"

    html_pv = html_consts["pv"]
    yaml_pv = config["pv"]

    assert html_pv["height_m"] == yaml_pv["height_m"], "height_m mismatch"
    assert html_pv["pitch_m"] == yaml_pv["pitch_m"], "pitch_m mismatch"
    assert html_pv["gcr"] == yaml_pv["gcr"], "gcr mismatch"
    assert (
        html_pv["max_tilt_deg"] == yaml_pv["max_tilt_deg"]
    ), "max_tilt_deg mismatch"
    assert html_pv["bifaciality"] == yaml_pv["bifaciality"], "bifaciality mismatch"
    assert html_pv["albedo"] == yaml_pv["albedo"], "albedo mismatch"
    assert html_pv["pdc0_w"] == yaml_pv["pdc0_w"], "pdc0_w mismatch"
    assert (
        html_pv["gamma_pdc_per_c"] == yaml_pv["gamma_pdc_per_c"]
    ), "gamma_pdc_per_c mismatch"


def test_par_constants_match_conversions():
    """Verify PAR constants in HTML match project/models/conversions.py."""
    html_consts = load_html_constants()

    assert html_consts["par_fraction"] == PAR_FRACTION, "PAR_FRACTION mismatch"
    assert (
        html_consts["ppfd_per_par_wm2"] == PPFD_PER_PAR_WM2
    ), "PPFD_PER_PAR_WM2 mismatch"


def test_lettuce_constants_match_model():
    """Verify LETTUCE constants in HTML match project/models/lettuce.py defaults."""
    html_consts = load_html_constants()
    lettuce_params = LettuceParams()

    assert "lettuce" in html_consts, "LETTUCE constant not found in HTML"
    html_lettuce = html_consts["lettuce"]

    assert html_lettuce["c_yf"] == lettuce_params.c_yf, "c_yf mismatch"
    assert html_lettuce["c_gr_max"] == lettuce_params.c_gr_max, "c_gr_max mismatch"
    assert html_lettuce["c_tau"] == lettuce_params.c_tau, "c_tau mismatch"
    assert html_lettuce["c_k"] == lettuce_params.c_k, "c_k mismatch"
    assert html_lettuce["c_lar"] == lettuce_params.c_lar, "c_lar mismatch"
    assert (
        html_lettuce["c_resp_sht"] == lettuce_params.c_resp_sht
    ), "c_resp_sht mismatch"
    assert (
        html_lettuce["c_resp_rt"] == lettuce_params.c_resp_rt
    ), "c_resp_rt mismatch"
    assert (
        html_lettuce["c_q10_resp"] == lettuce_params.c_q10_resp
    ), "c_q10_resp mismatch"
