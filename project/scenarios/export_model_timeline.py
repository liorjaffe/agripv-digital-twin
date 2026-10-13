"""Export the project simulation into the generic visualizador_timeline.html format."""

from __future__ import annotations

import json
import logging
import math
from pathlib import Path
import re

import pandas as pd

from project.config import load_runtime_config, make_site_location
from project.io.ingestion import load_period_results_export
from project.io.service import process_period_results_export
from project.scenarios.artifact_metadata import build_artifact_metadata
from project.scenarios.crop_cycles import seasonal_canopy_temperature, simulate_repeated_crops

ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / "project" / "data" / "raw" / "Period_Components.csv"
OUT_DIR = ROOT / "standalone"
JSON_PATH = OUT_DIR / "our_simulations_timeline.json"
HTML_PATH = OUT_DIR / "our_simulations_timeline.html"
HTML_TEMPLATE_PATH = OUT_DIR / "timeline_viewer.html"

SYNTHETIC_INPUTS_NOTICE = (
    "SYNTHETIC INPUTS USED HERE — The raw channel units and physical locations "
    "are undocumented. Light groups and their open/between/under labels are "
    "unverified scenario assumptions; PAR uses an assumed 0.45 fraction. The "
    "plotted canopy-temperature curve is a seasonal sinusoid; crop-cycle growth "
    "uses supplemental TMY air temperatures, not measured temperatures from the "
    "irradiance year. Wind and humidity are not measured or modeled in this viewer. "
    "Unrecorded irradiance timestamps are assumed to have zero light. "
    "Crop biomass values are uncalibrated model-derived scenario estimates, not "
    "validated yields: the growth equation, channel units, and dry-matter "
    "conversion are not calibrated for this site. GDD-based timing lets cooler, "
    "longer cycles accumulate more modeled mass. "
    "The per-plant conversion assumes the configured 96 plants on 11.25 m²; "
    "the user-reported 100–300 g/plant range is a plausibility reference only, "
    "not a calibration dataset. "
    "Do not interpret this "
    "visualization as independent validation or field evidence."
)

TIMELINE_VARIABLES = {
    "par_wm2": {"rot": "scenario PAR (assumed)", "un": "W/m²", "dec": 1},
    "t_folha": {
        "rot": "synthetic illustrative seasonal canopy temperature",
        "un": "°C",
        "dec": 2,
    },
    "t_air": {
        "rot": "typical-year air temperature (not observed)",
        "un": "°C",
        "dec": 1,
    },
    "fm": {
        "rot": "modeled fresh-mass equivalent (uncalibrated)",
        "un": "g/m²",
        "dec": 1,
    },
    "fp": {
        "rot": "modeled fresh-mass equivalent per plant (uncalibrated)",
        "un": "g/plant",
        "dec": 1,
    },
}


def finite_values(values: pd.Series) -> list[float | None]:
    return [float(v) if pd.notna(v) and math.isfinite(float(v)) else None for v in values]


def build_scenario_series(
    hourly: pd.DataFrame, light_column: str, fresh_column: str
) -> dict[str, list[float | None]]:
    par_wm2 = (hourly[light_column].astype(float) * 0.45).clip(lower=0.0)
    plant_density = load_runtime_config().plant_density_per_m2
    fresh_mass = hourly[fresh_column].astype(float)
    return {
        "par_wm2": finite_values(par_wm2),
        "t_folha": finite_values(hourly["t_folha_c"].astype(float)),
        "t_air": finite_values(hourly["model_air_temp_c"].astype(float)),
        "fm": finite_values(fresh_mass),
        "fp": finite_values(fresh_mass / plant_density),
    }


def build_timeline_metadata(hourly: pd.DataFrame) -> dict:
    artifact_metadata = build_artifact_metadata()
    return {
        "titulo": "Illustrative AgriPV scenario timeline",
        "subtitulo": (
            "Exploratory model output from the Period Components export. This is "
            "not field validation or a record of observed crop cycles."
        ),
        "local": "Florianópolis (-27.60, -48.55)",
        "manejo": "Unverified channel-group scenarios",
        "synthetic_inputs_notice": (
            f"{SYNTHETIC_INPUTS_NOTICE} Generated from commit "
            f"{artifact_metadata['source_commit']}; working tree dirty: "
            f"{str(artifact_metadata['working_tree_dirty']).lower()}. "
            "Crop-cycle and harvest markers are generated as model scenarios using the "
            "supplemental typical-year temperature series, not measured site "
            "air temperature from the irradiance year or observed harvests; "
            "they are not calibrated or observed harvest predictions. A cycle "
            "still in progress at the end of the data is not a completed harvest."
        ),
        **artifact_metadata,
        "n": len(hourly),
        "t0": hourly.index[0].strftime("%Y-%m-%d %H:%M"),
        "series_ordem": ["open", "between", "under"],
        "canteiros": {
            "open": "0A–0E (unverified group)",
            "between": "2B (unverified group)",
            "under": "2A/2C (unverified group)",
        },
        "padrao": ["par_wm2", "t_air", "fm", "fp"],
        "vars": TIMELINE_VARIABLES,
    }


def build_cycle_markers(cycle_frames: dict[str, pd.DataFrame], hourly: pd.DataFrame) -> list[dict]:
    markers: list[dict] = []
    for setup in ("open", "between", "under"):
        cycle = cycle_frames[setup]
        if cycle.empty:
            continue
        cycle_ids = cycle["cycle_id"].drop_duplicates().tolist()
        for cid in cycle_ids:
            subset = cycle[cycle["cycle_id"] == cid]
            if subset.empty:
                continue
            start_index = hourly.index.get_loc(subset.index[0])
            end_index = hourly.index.get_loc(subset.index[-1])
            matured = bool(subset["harvest"].any())
            markers.append({
                "ciclo": int(cid),
                "i0": int(start_index),
                "i1": int(end_index),
                "plantio": subset.index[0].strftime("%Y-%m-%d %H:%M"),
                "colheita": (
                    subset.index[-1].strftime("%Y-%m-%d %H:%M")
                    if matured
                    else "in progress"
                ),
                "dias": int((subset.index[-1] - subset.index[0]).days + 1),
                "maturidade_gdd": matured,
            })
    if not markers:
        return []
    markers.sort(key=lambda item: item["i0"])
    deduped: list[dict] = []
    for marker in markers:
        if not deduped or marker["i0"] > deduped[-1]["i1"]:
            deduped.append(marker)
    return deduped


def build_timeline_payload() -> dict:
    location = make_site_location()
    results, *_ = process_period_results_export(INPUT, location)
    hourly = results.resample("1h").mean(numeric_only=True)
    period = load_period_results_export(INPUT).resample("1h").mean(numeric_only=True)

    open_cols = [f"0{letter}_AVG" for letter in "ABCDE"]
    period["light_open_w_m2"] = period[open_cols].mean(axis=1)
    period["light_between_w_m2"] = period["2B_AVG"]
    period["light_under_w_m2"] = period[["2A_AVG", "2C_AVG"]].mean(axis=1)
    light_columns = ["light_open_w_m2", "light_between_w_m2", "light_under_w_m2"]
    hourly = hourly.join(period[light_columns])
    hourly[light_columns] = hourly[light_columns].fillna(0.0)

    cycle_frames = {
        "open": simulate_repeated_crops(
            hourly,
            "light_open_w_m2",
            temperature_c=hourly["model_air_temp_c"],
        ),
        "between": simulate_repeated_crops(
            hourly,
            "light_between_w_m2",
            temperature_c=hourly["model_air_temp_c"],
        ),
        "under": simulate_repeated_crops(
            hourly,
            "light_under_w_m2",
            temperature_c=hourly["model_air_temp_c"],
        ),
    }
    for setup, cycle in cycle_frames.items():
        hourly[f"fresh_{setup}_g_m2"] = cycle["cycle_model_fresh_biomass_g_m2"]
        hourly[f"harvest_{setup}"] = cycle["harvest"]

    leaf_temp = seasonal_canopy_temperature(hourly.index, planting_temp_c=24.0)
    hourly["t_folha_c"] = leaf_temp

    series = {
        "open": build_scenario_series(hourly, "light_open_w_m2", "fresh_open_g_m2"),
        "between": build_scenario_series(hourly, "light_between_w_m2", "fresh_between_g_m2"),
        "under": build_scenario_series(hourly, "light_under_w_m2", "fresh_under_g_m2"),
    }

    payload = {
        "meta": build_timeline_metadata(hourly),
        "ciclos": build_cycle_markers(cycle_frames, hourly),
        "series": series,
    }
    return payload


def write_json_payload(payload: dict) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    JSON_PATH.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    logging.info("Wrote %s", JSON_PATH)


def write_embedded_html(payload: dict) -> None:
    if not HTML_TEMPLATE_PATH.exists():
        raise FileNotFoundError(f"Timeline viewer template not found at {HTML_TEMPLATE_PATH}")
    source_text = HTML_TEMPLATE_PATH.read_text(encoding="utf-8")
    payload_js = json.dumps(payload, ensure_ascii=False)

    if re.search(r"window\.__TL__\s*=\s*\{.*?\};\s*\n\s*if\s*\(window\.__TL__\)", source_text, flags=re.DOTALL):
        injected = re.sub(
            r"window\.__TL__\s*=\s*\{.*?\};\s*\n\s*if\s*\(window\.__TL__\)",
            f"window.__TL__ = {payload_js};\nif (window.__TL__)",
            source_text,
            count=1,
            flags=re.DOTALL,
        )
    else:
        marker = "if (window.__TL__) {"
        if marker not in source_text:
            raise ValueError("Could not find embedded trigger in source HTML")
        injected = source_text.replace(marker, f"window.__TL__ = {payload_js};\n{marker}", 1)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    HTML_PATH.write_text(injected, encoding="utf-8")
    logging.info("Wrote %s", HTML_PATH)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    payload = build_timeline_payload()
    write_json_payload(payload)
    write_embedded_html(payload)


if __name__ == "__main__":
    main()
