"""Create a small standalone English report from the lettuce/PV model."""

from __future__ import annotations

import argparse
import base64
import html
import io
import logging
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from project.config import make_site_location
from project.io.ingestion import load_period_results_export
from project.io.service import process_period_results_export
from project.models.conversions import ghi_to_par, par_to_ppfd
from project.scenarios.artifact_metadata import build_artifact_metadata
from project.validation.validate_radiation import validate_radiation


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = ROOT / "project" / "data" / "raw" / "Period_Components.csv"
DEFAULT_OUTPUT = ROOT / "standalone" / "lettuce-pv-summary-report.html"
CHANNELS_FOR_COMPARISON = ("2A_AVG", "2B_AVG", "2C_AVG")


def attach_channel_ppfd_estimates(
    results: pd.DataFrame, period_components: pd.DataFrame
) -> pd.DataFrame:
    """Attach channel-derived PPFD using the documented shortwave conversion.

    The export has no channel unit or sensor metadata, so these estimates must
    not be presented as confirmed quantum-sensor measurements.
    """
    available = [
        channel for channel in CHANNELS_FOR_COMPARISON if channel in period_components
    ]
    attached = results.copy()
    for channel in available:
        shortwave_w_m2 = pd.to_numeric(period_components[channel], errors="coerce")
        channel_ppfd = par_to_ppfd(ghi_to_par(shortwave_w_m2))
        attached[f"channel_ppfd_{channel}"] = channel_ppfd.reindex(attached.index)
    return attached


def chart_image(values: pd.Series, title: str, ylabel: str, color: str, kind: str = "line") -> str:
    """Render one report graph as an embedded image."""
    figure, axis = plt.subplots(figsize=(10, 3.1), constrained_layout=True)
    if kind == "bar":
        values.plot(ax=axis, kind="bar", color=color)
        axis.tick_params(axis="x", rotation=0)
    else:
        values.plot(ax=axis, color=color, linewidth=1.5)
    axis.set_title(title, loc="left", fontsize=12, fontweight="normal")
    axis.set_ylabel(ylabel)
    axis.set_xlabel("")
    image = io.BytesIO()
    figure.savefig(image, format="png", dpi=130)
    plt.close(figure)
    return base64.b64encode(image.getvalue()).decode("ascii")


def chart_cards(results: pd.DataFrame, daily: pd.DataFrame) -> str:
    """Build movable graph panels for the report dashboard."""
    hourly = results.resample("1h").mean(numeric_only=True)
    charts = (
        ("light", "Crop light", hourly["crop_ppfd_umol_m2_s"], "PPFD (umol/m2/s)", "#167d8d", "line"),
        ("pv", "PV energy by day", daily["pv_energy_kwh"], "kWh", "#e07a32", "bar"),
        ("temperature", "Typical-year air temperature", hourly["model_air_temp_c"], "°C", "#7357a6", "line"),
        ("biomass", "Modeled total dry biomass (uncalibrated)", daily["final_dry_biomass"], "g/m²", "#a33c70", "line"),
    )
    return "".join(
        f"""<article class="panel" draggable="true" data-panel="{key}">
          <div class="panel-head"><h3>{title}</h3><button class="panel-toggle" type="button" aria-expanded="true">Hide</button></div>
          <div class="panel-body"><img src="data:image/png;base64,{chart_image(values, title, ylabel, color, kind)}" alt="{title}"></div>
        </article>"""
        for key, title, values, ylabel, color, kind in charts
    )


def daily_table(daily: pd.DataFrame) -> str:
    rows = []
    for timestamp, row in daily.iterrows():
        coverage = row.get("daylight_coverage_fraction")
        coverage_text = f"{coverage * 100:.0f}%" if pd.notna(coverage) else "n/a"
        dli_text = f"{row['dli_mol_m2_day']:.2f}" if pd.notna(row["dli_mol_m2_day"]) else "n/a"
        pv_text = f"{row['pv_energy_kwh']:.2f}" if pd.notna(row["pv_energy_kwh"]) else "n/a"
        biomass = row.get("final_dry_biomass")
        biomass_text = f"{biomass:.2f}" if pd.notna(biomass) else "n/a"
        if pd.isna(row.get("candidate_dli_target_band_reachable")):
            reachability_text = "unknown"
        elif (
            not bool(row["candidate_dli_ceiling_reachable"])
            and not bool(row["candidate_dli_minimum_reachable"])
        ):
            reachability_text = "target and ceiling unreachable"
        elif not bool(row["candidate_dli_ceiling_reachable"]):
            reachability_text = "ceiling unreachable"
        elif not bool(row["candidate_dli_minimum_reachable"]):
            reachability_text = "target unreachable"
        else:
            reachability_text = "band reachable"
        candidate_min = row.get("candidate_min_dli_mol_m2_day")
        candidate_max = row.get("candidate_max_dli_mol_m2_day")
        candidate_range_text = (
            f"{candidate_min:.2f}–{candidate_max:.2f}"
            if pd.notna(candidate_min) and pd.notna(candidate_max)
            else "unknown"
        )
        rows.append(
            "<tr>"
            f"<td>{html.escape(timestamp.strftime('%Y-%m-%d'))}</td>"
            f"<td>{dli_text}</td>"
            f"<td>{pv_text}</td>"
            f"<td>{biomass_text}</td>"
            f"<td>{coverage_text}</td>"
            f"<td>{candidate_range_text}</td>"
            f"<td>{reachability_text}</td>"
            "</tr>"
        )
    return "".join(rows)


def channel_comparison_summary(results: pd.DataFrame) -> str:
    modeled = results.get("crop_ppfd_umol_m2_s")
    channel_columns = [
        f"channel_ppfd_{channel}"
        for channel in CHANNELS_FOR_COMPARISON
        if f"channel_ppfd_{channel}" in results
    ]
    if not channel_columns or modeled is None:
        return """
        <div class="note">No comparable 2A/2B/2C irradiance channels are available in this result set.</div>
        """

    rows = []
    for channel_column in channel_columns:
        channel = channel_column.removeprefix("channel_ppfd_")
        measured = pd.to_numeric(results[channel_column], errors="coerce")
        validation = validate_radiation(measured, modeled)
        if validation["status"] != "ok":
            rows.append(
                f"<tr><th>{html.escape(channel)}</th><td colspan='5'>"
                f"{html.escape(validation.get('message', validation['status']))}</td></tr>"
            )
            continue
        paired = (
            np.isfinite(measured.to_numpy())
            & np.isfinite(pd.to_numeric(modeled, errors="coerce").to_numpy())
        )
        paired_days = results.index[paired].normalize().nunique()
        rows.append(
            f"<tr><th>{html.escape(channel)}</th>"
            f"<td>{validation['samples']}</td>"
            f"<td>{paired_days}</td>"
            f"<td>{validation['mae_ppfd_umol_m2_s']:.2f}</td>"
            f"<td>{validation['rmse_ppfd_umol_m2_s']:.2f}</td>"
            f"<td>{validation['bias_ppfd_umol_m2_s']:.2f}</td></tr>"
        )

    return f"""
    <h3>Exploratory channel comparison</h3>
    <p class="note"><strong>Open scientific task:</strong> obtain the authoritative site channel map, including sensor type, units, calibration, and physical placement. These values are exploratory, not independent validation: only for comparison, each channel is assumed to be shortwave irradiance in W/m² and converted with PAR fraction 0.45 and 4.57 µmol/J. A different sensor type could materially change the comparison. Do not use these metrics to calibrate crop-light conversion until the channel map is verified. Channels are shown by export name; no bed mapping is asserted. DLI errors are omitted because daylight sampling coverage is incomplete.</p>
    <div class="table-wrap"><table>
      <thead><tr><th>Export channel</th><th>Paired samples</th><th>Days represented</th><th>MAE PPFD<br>(µmol/m²/s)</th><th>RMSE PPFD<br>(µmol/m²/s)</th><th>Bias PPFD<br>(µmol/m²/s)</th></tr></thead>
      <tbody>{''.join(rows)}</tbody>
    </table></div>
    """


def hourly_table(results: pd.DataFrame) -> str:
    hourly = results.resample("1h").mean(numeric_only=True)
    observed_tracker = "observed_tracker_angle_deg" in hourly.columns
    rows = []
    for timestamp, row in hourly.iterrows():
        tracker_cell = (
            f"<td>{row['observed_tracker_angle_deg']:.1f}</td>"
            if observed_tracker else ""
        )
        rows.append(
            "<tr>"
            f"<td>{html.escape(timestamp.strftime('%Y-%m-%d %H:%M'))}</td>"
            f"<td>{row['crop_ppfd_umol_m2_s']:.1f}</td>"
            f"<td>{row['pv_power_w'] / 1000:.2f}</td>"
            f"{tracker_cell}"
            "</tr>"
        )
    return "".join(rows)


def subzone_section(subzone_id: str, results: pd.DataFrame, daily: pd.DataFrame) -> str:
    total_energy = daily["pv_energy_kwh"].sum(min_count=1)
    mean_dli = daily["dli_mol_m2_day"].mean()
    covered_days = int(daily["daylight_coverage_sufficient"].sum())
    mean_dli_text = f"{mean_dli:.2f}" if pd.notna(mean_dli) else "n/a"
    total_energy_text = f"{total_energy:.2f}" if pd.notna(total_energy) else "n/a"
    valid_biomass = daily["final_dry_biomass"].dropna()
    final_biomass_text = (
        f"{valid_biomass.iloc[-1]:.2f}" if not valid_biomass.empty else "n/a"
    )
    tracker_header = (
        "<th>Observed tracker<br>(degrees)</th>"
        if "observed_tracker_angle_deg" in results.columns else ""
    )
    return f"""
    <section class="subzone">
      <h2>{html.escape(subzone_id)}</h2>
      <div class="metrics">
        <div><strong>{mean_dli_text}</strong><span>Average DLI (mol/m2/day; {covered_days} covered days)</span></div>
        <div><strong>{total_energy_text}</strong><span>PV energy (kWh; covered days only)</span></div>
        <div><strong>{final_biomass_text}</strong><span>Final modeled total dry biomass (g/m²; uncalibrated continuous model state, not harvest yield)</span></div>
      </div>
    <div class="dashboard-grid">{chart_cards(results, daily)}</div>
      {channel_comparison_summary(results)}
      <h3>Daily results</h3>
      <table>
        <thead><tr><th>Date</th><th>DLI<br>(mol/m2/day)</th><th>PV energy<br>(kWh)</th><th>Modeled dry biomass<br>(g/m²; uncalibrated)</th><th>Daylight coverage</th><th>Candidate DLI envelope<br>(mol/m2/day)</th><th>Candidate-band reachability<br>(movement/stow unconstrained)</th></tr></thead>
        <tbody>{daily_table(daily)}</tbody>
      </table>
      <details>
        <summary>Hourly model output</summary>
        <table>
          <thead><tr><th>Time</th><th>Crop PPFD<br>(umol/m2/s)</th><th>PV power<br>(kW)</th>{tracker_header}</tr></thead>
          <tbody>{hourly_table(results)}</tbody>
        </table>
      </details>
    </section>
    """


def build_report(input_path: Path, output_path: Path) -> None:
    location = make_site_location()
    results, daily, *_ = process_period_results_export(input_path, location)
    period_components = load_period_results_export(input_path)
    results = attach_channel_ppfd_estimates(results, period_components)
    start = results.index.min().strftime("%Y-%m-%d")
    end = results.index.max().strftime("%Y-%m-%d")
    temperature_source = str(results["model_air_temp_source"].iloc[0])
    temperature_value = float(results["model_air_temp_c"].iloc[0])
    artifact_metadata = build_artifact_metadata()
    temperature_note = (
        f" Temperature-dependent calculations use the supplemental typical-year "
        f"air-temperature series ({temperature_source}; first value "
        f"{temperature_value:.1f}°C). It is not measured temperature from the "
        "irradiance year, so biomass outputs are uncalibrated scenario results, "
        "not field predictions. The continuous biomass state is not a per-harvest "
        "yield."
        if temperature_source.startswith("TMY climatological")
        else (
            f" Temperature-dependent calculations use {temperature_value:.1f}°C "
            "as a configured scenario fallback because no air-temperature input "
            "is present; biomass outputs are not field predictions."
            if temperature_source == "configured scenario fallback"
            else f" Temperature input source for this run: {temperature_source}."
        )
    )
    temperature_note += (
        " The Period Components export records daytime samples; unrecorded "
        "irradiance timestamps are assumed to have zero light in the model. "
        "This assumption does not alter measured source values or the reported "
        "daylight-coverage checks. Crop-cycle fresh-mass equivalents are separate "
        "from the continuous dry-biomass state and can be higher in cool seasons "
        "because the GDD clock makes those cycles longer; they are not calibrated "
        "or observed harvests."
    )
    sections = subzone_section("Period Components", results, daily)
    report = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="agripv-source-commit" content="{html.escape(str(artifact_metadata['source_commit']), quote=True)}">
<meta name="agripv-working-tree-dirty" content="{str(artifact_metadata['working_tree_dirty']).lower()}">
<title>Lettuce and PV model report</title>
<style>
:root {{ color-scheme: light; --ink:#17333b; --muted:#61747a; --line:#d8e1df; --paper:#f5f7f4; --teal:#167d8d; --orange:#e07a32; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--paper); color:var(--ink); font:15px/1.45 Georgia, serif; }}
main {{ max-width:1100px; margin:0 auto; padding:44px 24px 72px; }}
h1 {{ margin:0 0 8px; font-size:clamp(2rem,5vw,4rem); font-weight:400; letter-spacing:0; }}
.lead {{ color:var(--muted); margin:0 0 36px; }}
.subzone {{ border-top:4px solid var(--teal); padding-top:18px; margin-top:48px; }}
h2 {{ font-size:1.8rem; font-weight:400; margin:0 0 18px; }}
h3 {{ margin:28px 0 10px; font-size:1.1rem; font-weight:400; }}
.metrics {{ display:grid; grid-template-columns:repeat(3,1fr); gap:12px; margin-bottom:22px; }}
.metrics div {{ background:white; border:1px solid var(--line); padding:16px; }}
.metrics strong {{ display:block; font-size:1.7rem; font-weight:400; }}
.metrics span {{ color:var(--muted); font-size:.85rem; }}
.dashboard-grid {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:14px; align-items:start; }}
.panel {{ background:white; border:1px solid var(--line); min-width:0; box-shadow:0 3px 10px rgba(23,51,59,.05); }}
.panel:first-child {{ grid-column:span 2; }}
.panel.dragging {{ opacity:.45; border:1px dashed var(--teal); }}
.panel-head {{ display:flex; align-items:center; justify-content:space-between; gap:12px; padding:12px 14px 0; cursor:grab; }}
.panel-head h3 {{ margin:0; }}
.panel-toggle {{ border:0; background:transparent; color:var(--teal); cursor:pointer; font:inherit; font-size:.8rem; padding:4px 0; }}
.panel-body {{ padding:4px 10px 10px; }}
.panel-body img {{ display:block; width:100%; height:auto; }}
.panel.is-collapsed .panel-body {{ display:none; }}
table {{ width:100%; border-collapse:collapse; background:white; font-family:ui-monospace, SFMono-Regular, Menlo, monospace; font-size:.8rem; }}
th,td {{ border-bottom:1px solid var(--line); padding:8px 10px; text-align:right; }}
th:first-child,td:first-child {{ text-align:left; }}
th {{ color:var(--muted); font-weight:400; }}
details {{ margin-top:20px; }}
summary {{ cursor:pointer; color:var(--teal); }}
.note {{ color:var(--muted); font-size:.9rem; max-width:760px; }}
@media (max-width:650px) {{ main {{ padding:28px 14px 52px; }} .metrics {{ grid-template-columns:1fr; }} .dashboard-grid {{ grid-template-columns:1fr; }} .panel:first-child {{ grid-column:span 1; }} table {{ font-size:.7rem; }} th,td {{ padding:7px 5px; }} }}
</style>
</head>
<body>
<main>
  <h1>Lettuce and PV model</h1>
  <p class="lead">A simple hour-by-hour view of the modeled agrivoltaic system · {start} to {end}</p>
    <p class="note">Generated from commit <code>{html.escape(str(artifact_metadata['source_commit']))}</code>; working tree dirty: {str(artifact_metadata['working_tree_dirty']).lower()}.</p>
    <p class="note">This report is generated directly from the Python model and is independent of the existing dashboard. GHI, DNI and DHI come directly from the Period Components export. Crop light is calculated by the agrivoltaic radiation model. Values are hourly averages unless shown as daily totals. Daily DLI and PV energy use trapezoidal integration over finite adjacent samples and are shown only when at least 80% of expected daylight source samples are present. The source does not document the sensor type, units, or physical locations of its grid channels; channel comparisons are therefore exploratory and assumption-based, not confirmed bed-level validation.{html.escape(temperature_note)}</p>
  {sections}
</main>
<script>
document.querySelectorAll('.panel-toggle').forEach(function(button) {{
    button.addEventListener('click', function() {{
        const panel = button.closest('.panel');
        const collapsed = panel.classList.toggle('is-collapsed');
        button.textContent = collapsed ? 'Show' : 'Hide';
        button.setAttribute('aria-expanded', String(!collapsed));
    }});
}});

document.querySelectorAll('.panel').forEach(function(panel) {{
    panel.addEventListener('dragstart', function(event) {{
        panel.classList.add('dragging');
        event.dataTransfer.effectAllowed = 'move';
        event.dataTransfer.setData('text/plain', panel.dataset.panel);
    }});
    panel.addEventListener('dragend', function() {{ panel.classList.remove('dragging'); }});
    panel.addEventListener('dragover', function(event) {{
        event.preventDefault();
        const moving = document.querySelector('.panel.dragging');
        if (moving && moving !== panel) {{
            const grid = panel.parentElement;
            const after = event.clientY > panel.getBoundingClientRect().top + panel.offsetHeight / 2;
            grid.insertBefore(moving, after ? panel.nextSibling : panel);
        }}
    }});
}});
</script>
</body>
</html>
"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    logging.info("Wrote %s", output_path)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    build_report(args.input, args.output)


if __name__ == "__main__":
    main()
