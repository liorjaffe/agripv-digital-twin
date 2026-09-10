"""Export the project simulation into the generic visualizador_timeline.html format."""

from __future__ import annotations

import json
import math
from pathlib import Path

import pandas as pd
import pvlib

from project.io.ingestion import load_period_results_export
from project.io.service import process_period_results_export
from project.models.lettuce import simulate_growth_timeseries
from project.models.lettuce_development import LettuceThermalDevelopment

ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / "project" / "data" / "raw" / "Period_Components.csv"
OUT_DIR = ROOT / "standalone"
JSON_PATH = OUT_DIR / "our_simulations_timeline.json"
HTML_PATH = OUT_DIR / "our_simulations_timeline.html"
SOURCE_HTML = Path("/Users/liorjaffe/Desktop/modelo-vanhenten-pacote/visualizador_timeline.html")


def finite_values(values: pd.Series) -> list[float | None]:
    return [float(v) if pd.notna(v) and math.isfinite(float(v)) else None for v in values]


def seasonal_mean_temp_c(day_of_year: int) -> float:
    return 20.5 + 5.0 * math.cos(2.0 * math.pi * (day_of_year - 34.0) / 365.25)


def seasonal_canopy_temperature(times: pd.DatetimeIndex, planting_temp_c: float = 24.0) -> pd.Series:
    planting_day = int(times[0].dayofyear)
    planting_offset = planting_temp_c - seasonal_mean_temp_c(planting_day)
    return pd.Series(
        [seasonal_mean_temp_c(int(timestamp.dayofyear)) + planting_offset for timestamp in times],
        index=times,
    )


def simulate_repeated_crops(results: pd.DataFrame, light_column: str, max_cycle_days: int = 120) -> pd.DataFrame:
    records: list[pd.DataFrame] = []
    start = 0
    cycle_number = 1
    while start < len(results):
        candidate = results.iloc[start:start + max_cycle_days * 24]
        if candidate.empty:
            break
        temperatures = seasonal_canopy_temperature(candidate.index)
        thermal = LettuceThermalDevelopment()
        harvest_position = len(candidate) - 1
        for date, day_temperature in temperatures.groupby(temperatures.index.normalize()).mean().items():
            state = thermal.update(float(day_temperature))
            if state["harvest_ready"]:
                positions = [
                    position for position, timestamp in enumerate(candidate.index)
                    if timestamp.normalize() == date
                ]
                if positions:
                    harvest_position = positions[-1]
                break
        crop = candidate.iloc[:harvest_position + 1]
        growth = simulate_growth_timeseries(
            crop.index,
            crop[light_column] * 0.45,
            seasonal_canopy_temperature(crop.index),
            x_sdw0=8.0,
            x_nsdw0=3.0,
        )
        initial_dry_mass = 11.0
        cycle = pd.DataFrame(index=crop.index)
        cycle["cycle_id"] = cycle_number
        cycle["cycle_dry_biomass_g_m2"] = growth["total_dry_biomass"]
        cycle["cycle_fresh_biomass_g_m2"] = ((growth["total_dry_biomass"] - initial_dry_mass).clip(lower=0.0) / 0.05)
        cycle["harvest"] = False
        cycle.iloc[-1, cycle.columns.get_loc("harvest")] = True
        records.append(cycle)
        start += len(crop)
        cycle_number += 1
    return pd.concat(records, ignore_index=False)


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
            markers.append({
                "ciclo": int(cid),
                "i0": int(start_index),
                "i1": int(end_index),
                "plantio": subset.index[0].strftime("%Y-%m-%d %H:%M"),
                "colheita": subset.index[-1].strftime("%Y-%m-%d %H:%M"),
                "dias": int((subset.index[-1] - subset.index[0]).days + 1),
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
    location = pvlib.location.Location(
        latitude=-27.5949, longitude=-48.5480, tz="America/Sao_Paulo", altitude=20.0
    )
    results, *_ = process_period_results_export(INPUT, location, dli_target_mol_m2_day=14.0)
    hourly = results.resample("1h").mean(numeric_only=True)
    period = load_period_results_export(INPUT).resample("1h").mean(numeric_only=True)

    open_cols = [f"0{letter}_AVG" for letter in "ABCDE"]
    period["light_open_w_m2"] = period[open_cols].mean(axis=1)
    period["light_between_w_m2"] = period["2B_AVG"]
    period["light_under_w_m2"] = period[["2A_AVG", "2C_AVG"]].mean(axis=1)
    hourly = hourly.join(period[["light_open_w_m2", "light_between_w_m2", "light_under_w_m2"]])

    cycle_frames = {
        "open": simulate_repeated_crops(hourly, "light_open_w_m2"),
        "between": simulate_repeated_crops(hourly, "light_between_w_m2"),
        "under": simulate_repeated_crops(hourly, "light_under_w_m2"),
    }
    for setup, cycle in cycle_frames.items():
        hourly[f"fresh_{setup}_g_m2"] = cycle["cycle_fresh_biomass_g_m2"]
        hourly[f"harvest_{setup}"] = cycle["harvest"]

    leaf_temp = seasonal_canopy_temperature(hourly.index, planting_temp_c=24.0)
    hourly["t_folha_c"] = leaf_temp

    def make_series(light_col: str, fresh_col: str) -> dict[str, list[float | None]]:
        light_ghi = hourly[light_col].astype(float)
        par_wm2 = (light_ghi * 0.45).clip(lower=0.0)
        crop_temp = hourly["t_folha_c"].astype(float)
        fresh = hourly[fresh_col].astype(float)
        photo = (par_wm2 * 0.18).clip(lower=0.0)
        constant_optimal = pd.Series(1.0, index=hourly.index)
        return {
            "par_wm2": finite_values(par_wm2),
            "t_folha": finite_values(crop_temp),
            "fm": finite_values(fresh),
            "phi_phot": finite_values(photo),
            "ks": finite_values(constant_optimal),
            "i_n": finite_values(constant_optimal),
        }

    series = {
        "open": make_series("light_open_w_m2", "fresh_open_g_m2"),
        "between": make_series("light_between_w_m2", "fresh_between_g_m2"),
        "under": make_series("light_under_w_m2", "fresh_under_g_m2"),
    }

    payload = {
        "meta": {
            "titulo": "Agrivoltaic lettuce model timeline",
            "subtitulo": "Hourly model output from the Period Components simulation, aligned to the reference visualizador_timeline.html format.",
            "local": "Florianópolis (-27.60, -48.55)",
            "manejo": "Open / between / under tracker comparison",
            "n": len(hourly),
            "t0": hourly.index[0].strftime("%Y-%m-%d %H:%M"),
            "series_ordem": ["open", "between", "under"],
            "canteiros": {
                "open": "0A–0E open",
                "between": "2B between rows",
                "under": "2A/2C under trackers",
            },
            "padrao": ["par_wm2", "t_folha", "fm", "phi_phot", "ks", "i_n"],
            "vars": {
                "par_wm2": {"rot": "luz que chega ao canteiro", "un": "W/m² de PAR", "dec": 1},
                "t_folha": {"rot": "temperatura da folha", "un": "°C", "dec": 2},
                "fm": {"rot": "massa fresca acumulada", "un": "g/m²", "dec": 1},
                "phi_phot": {"rot": "fotossíntese bruta do dossel", "un": "µg CH₂O/m²/s", "dec": 1},
                "ks": {"rot": "abertura do estômato pela água", "un": "0 a 1", "dec": 3},
                "i_n": {"rot": "freio do nitrogênio", "un": "0 a 1", "dec": 3},
            },
        },
        "ciclos": build_cycle_markers(cycle_frames, hourly),
        "series": series,
        "temp_ar": finite_values(leaf_temp),
        "vento": [1.2 for _ in range(len(hourly))],
        "ur": [60.0 for _ in range(len(hourly))],
    }
    return payload


def write_json_payload() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    payload = build_timeline_payload()
    JSON_PATH.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Wrote {JSON_PATH}")


def write_embedded_html() -> None:
    source_html_path = SOURCE_HTML if SOURCE_HTML.exists() else HTML_PATH
    if not source_html_path.exists():
        raise FileNotFoundError(f"Source viewer not found at {source_html_path}")
    source_text = source_html_path.read_text(encoding="utf-8")
    payload = build_timeline_payload()
    payload_js = json.dumps(payload, ensure_ascii=False)
    
    # If the file already has an injected window.__TL__ assignment, replace it;
    # otherwise inject before the marker if (window.__TL__) {
    import re
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
    
    HTML_PATH.write_text(injected, encoding="utf-8")
    print(f"Wrote {HTML_PATH}")


def main() -> None:
    write_json_payload()
    write_embedded_html()


if __name__ == "__main__":
    main()
