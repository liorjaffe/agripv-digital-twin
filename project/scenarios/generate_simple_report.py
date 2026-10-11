"""Create a small standalone English report from the lettuce/PV model."""

from __future__ import annotations

import argparse
import base64
import html
import io
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from project.config import make_site_location
from project.io.service import process_period_results_export


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = ROOT / "project" / "data" / "raw" / "Period_Components.csv"
DEFAULT_OUTPUT = ROOT / "standalone" / "lettuce-pv-summary-report.html"


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
        ("biomass", "Lettuce dry biomass", results["total_dry_biomass"], "g/m2", "#3f7d4b", "line"),
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
        rows.append(
            "<tr>"
            f"<td>{html.escape(timestamp.strftime('%Y-%m-%d'))}</td>"
            f"<td>{row['dli_mol_m2_day']:.2f}</td>"
            f"<td>{row['pv_energy_kwh']:.2f}</td>"
            f"<td>{row['final_dry_biomass']:.2f}</td>"
            f"<td>{row['input_data_complete_fraction'] * 100:.0f}%</td>"
            "</tr>"
        )
    return "".join(rows)


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
            f"<td>{row['total_dry_biomass']:.2f}</td>"
            f"{tracker_cell}"
            "</tr>"
        )
    return "".join(rows)


def subzone_section(subzone_id: str, results: pd.DataFrame, daily: pd.DataFrame) -> str:
    total_energy = daily["pv_energy_kwh"].sum()
    final_biomass = daily["final_dry_biomass"].dropna().iloc[-1]
    mean_dli = daily["dli_mol_m2_day"].mean()
    tracker_header = (
        "<th>Observed tracker<br>(degrees)</th>"
        if "observed_tracker_angle_deg" in results.columns else ""
    )
    return f"""
    <section class="subzone">
      <h2>{html.escape(subzone_id)}</h2>
      <div class="metrics">
        <div><strong>{mean_dli:.2f}</strong><span>Average DLI (mol/m2/day)</span></div>
        <div><strong>{total_energy:.2f}</strong><span>Total PV energy (kWh)</span></div>
        <div><strong>{final_biomass:.2f}</strong><span>Final dry biomass (g/m2)</span></div>
      </div>
    <div class="dashboard-grid">{chart_cards(results, daily)}</div>
      <h3>Daily results</h3>
      <table>
        <thead><tr><th>Date</th><th>DLI<br>(mol/m2/day)</th><th>PV energy<br>(kWh)</th><th>Dry biomass<br>(g/m2)</th><th>Input complete</th></tr></thead>
        <tbody>{daily_table(daily)}</tbody>
      </table>
      <details>
        <summary>Hourly model output</summary>
        <table>
          <thead><tr><th>Time</th><th>Crop PPFD<br>(umol/m2/s)</th><th>PV power<br>(kW)</th><th>Dry biomass<br>(g/m2)</th>{tracker_header}</tr></thead>
          <tbody>{hourly_table(results)}</tbody>
        </table>
      </details>
    </section>
    """


def build_report(input_path: Path, output_path: Path) -> None:
    location = make_site_location()
    results, daily, *_ = process_period_results_export(input_path, location)
    start = results.index.min().strftime("%Y-%m-%d")
    end = results.index.max().strftime("%Y-%m-%d")
    sections = subzone_section("Period Components", results, daily)
    report = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
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
    <p class="note">This report is generated directly from the Python model and is independent of the existing dashboard. GHI, DNI and DHI come directly from the Period Components export. Crop light is calculated by the agrivoltaic radiation model. Values are hourly averages unless shown as daily totals.</p>
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
    print(f"Wrote {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    build_report(args.input, args.output)


if __name__ == "__main__":
    main()
