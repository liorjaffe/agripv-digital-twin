"""Create the standalone year-at-a-glance lettuce/PV model explorer."""

from __future__ import annotations

import argparse
import html
import json
import logging
import math
from pathlib import Path

import pandas as pd

from project.config import load_runtime_config, make_site_location
from project.io.service import process_period_results_export
from project.io.ingestion import load_period_results_export
from project.scenarios.artifact_metadata import build_artifact_metadata
from project.scenarios.crop_cycles import simulate_repeated_crops

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = ROOT / "project" / "data" / "raw" / "Period_Components.csv"
DEFAULT_OUTPUT = ROOT / "standalone" / "lettuce-pv-model-report.html"
USER_REPORTED_FRESH_MASS_RANGE_G_PER_PLANT = (100.0, 300.0)
SYNTHETIC_INPUTS_NOTICE = (
    "SYNTHETIC INPUTS USED HERE — The Period Components export does not provide "
    "channel units/locations or air temperature. Channel groups below are "
    "unverified scenario assignments and irradiance is interpreted as W/m². "
    "Temperature-dependent outputs use supplemental typical-year air "
    "temperature, not measured temperatures from the irradiance year; crop-cycle "
    "fresh-mass equivalents also use an assumed 5% dry-matter fraction. "
    "Unrecorded irradiance timestamps are assumed to have zero light. Crop "
    "biomass values are uncalibrated model-derived scenario estimates, not "
    "validated yields: the growth equation, channel units, and dry-matter "
    "conversion are not calibrated for this site. The GDD clock makes cool-season "
    "cycles longer while the separate biomass equation accumulates throughout "
    "each cycle. The final cycle may be incomplete. These are "
    "scenario outputs, not observed harvests or independent field validation."
)


def finite_values(values: pd.Series) -> list[float | None]:
    return [float(value) if math.isfinite(float(value)) else None for value in values]


def cycle_summary_html(cycle_frames: dict[str, pd.DataFrame]) -> str:
    rows = []
    plant_density = load_runtime_config().plant_density_per_m2
    labels = {
        "open": "0A–0E assumed open",
        "between": "2B assumed between",
        "under": "2A/2C assumed under",
    }
    for setup, cycle_frame in cycle_frames.items():
        for cycle_id, cycle in cycle_frame.groupby("cycle_id", sort=True):
            duration_days = (cycle.index[-1] - cycle.index[0]).days + 1
            completed = bool(cycle["harvest"].any())
            mass = float(cycle["cycle_model_fresh_biomass_g_m2"].iloc[-1])
            mass_per_plant = mass / plant_density
            lower, upper = USER_REPORTED_FRESH_MASS_RANGE_G_PER_PLANT
            comparison = (
                "above user-reported range"
                if mass_per_plant > upper
                else "below user-reported range"
                if mass_per_plant < lower
                else "within user-reported range"
            )
            rows.append(
                "<tr>"
                f"<td>{labels[setup]}</td>"
                f"<td>{int(cycle_id)}</td>"
                f"<td>{cycle.index[0].strftime('%Y-%m-%d')}</td>"
                f"<td>{duration_days}</td>"
                f"<td>{'GDD threshold reached' if completed else 'in progress at data end'}</td>"
                f"<td>{mass:.1f}</td>"
                f"<td>{mass_per_plant:.1f}</td>"
                f"<td>{comparison}</td>"
                "</tr>"
            )
    return (
        "<details><summary>Modeled crop-cycle estimates (uncalibrated)</summary>"
        "<p>Fresh-mass equivalent = modeled dry-mass gain divided by the "
        "assumed 5% dry-matter fraction. The GDD clock sets cycle duration and "
        "the separate biomass model accumulates throughout the cycle. The "
        "per-plant conversion uses the configured 96 plants over 11.25 m². "
        "For context only, values are compared with the user-reported 100–300 "
        "g/plant range; those records are not currently available for "
        "calibration. These are not measured or validated harvests.</p>"
        "<div style=\"overflow-x:auto\"><table><thead><tr>"
        "<th>Scenario group</th><th>Cycle</th><th>Start</th><th>Days</th>"
        "<th>Status</th><th>Modeled equivalent (g/m²)</th>"
        "<th>Modeled equivalent (g/plant)</th><th>Comparison</th>"
        f"</tr></thead><tbody>{''.join(rows)}</tbody></table></div></details>"
    )


def build_report(input_path: Path, output_path: Path) -> None:
    location = make_site_location()
    results, *_ = process_period_results_export(input_path, location)
    hourly = results.resample("1h").mean(numeric_only=True)
    period = load_period_results_export(input_path).resample("1h").mean(numeric_only=True)
    open_columns = [f"0{letter}_AVG" for letter in "ABCDE"]
    period["light_open_w_m2"] = period[open_columns].mean(axis=1)
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
    temperature_source = str(results["model_air_temp_source"].iloc[0])
    temperature_value = float(results["model_air_temp_c"].iloc[0])
    artifact_metadata = build_artifact_metadata()
    synthetic_notice = (
        f"{SYNTHETIC_INPUTS_NOTICE} In this run the pipeline temperature "
        f"input was {temperature_source} ({temperature_value:.1f}°C), and the "
        "crop-cycle calculations use the same series. "
        f"Generated from commit {artifact_metadata['source_commit']}; working "
        f"tree dirty: {str(artifact_metadata['working_tree_dirty']).lower()}."
    )
    model_data = {
        "timestamps": [timestamp.isoformat() for timestamp in hourly.index],
        "series": {
            "light_open": {"label": "scenario light (0A-0E; unverified group)", "unit": "assumed W/m2", "color": "#d48300", "values": finite_values(hourly["light_open_w_m2"])},
            "light_between": {"label": "scenario light (2B; unverified group)", "unit": "assumed W/m2", "color": "#2f82b9", "values": finite_values(hourly["light_between_w_m2"])},
            "light_under": {"label": "scenario light (2A/2C; unverified group)", "unit": "assumed W/m2", "color": "#a33c70", "values": finite_values(hourly["light_under_w_m2"])},
            "pv": {"label": "PV power", "unit": "kW", "color": "#2f82b9", "values": finite_values(hourly["pv_power_w"] / 1000.0)},
            "fresh_open": {"label": "modeled fresh-mass equivalent (uncalibrated; open scenario)", "unit": "g/m2", "color": "#d48300", "values": finite_values(hourly["fresh_open_g_m2"])},
            "fresh_between": {"label": "modeled fresh-mass equivalent (uncalibrated; between scenario)", "unit": "g/m2", "color": "#2f82b9", "values": finite_values(hourly["fresh_between_g_m2"])},
            "fresh_under": {"label": "modeled fresh-mass equivalent (uncalibrated; under scenario)", "unit": "g/m2", "color": "#a33c70", "values": finite_values(hourly["fresh_under_g_m2"])},
            "tracker": {"label": "export tracker angle (convention undocumented)", "unit": "degrees", "color": "#4d8b61", "values": finite_values(hourly["observed_tracker_angle_deg"])},
        },
        "cycle_count": int(cycle_frames["open"]["cycle_id"].max()),
        "harvest_mode": "thermal GDD",
        "crop_cycle_temperature_source": temperature_source,
        "harvest_indices": [index for index, is_harvest in enumerate(hourly["harvest_open"]) if is_harvest],
        "synthetic_inputs_notice": synthetic_notice,
        "air_temperature_source": temperature_source,
        "air_temperature_value_c": temperature_value,
        **artifact_metadata,
    }
    report = render_report_template(model_data, synthetic_notice, cycle_frames)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    logging.info("Wrote %s", output_path)


TEMPLATE = r'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>A year, hour by hour</title>
<style>
:root{--ink:#252720;--muted:#7d8175;--line:#dedfd7;--paper:#fafaf7;--card:#fff;--gold:#c97800;--blue:#2f82b9;--pink:#a33c70;--green:#4d8b61}*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:15px/1.45 Georgia,serif}main{max-width:1320px;margin:auto;padding:28px 20px 70px}.eyebrow,.label{color:var(--muted);font:11px/1.3 ui-monospace,SFMono-Regular,Menlo,monospace;letter-spacing:.16em;text-transform:uppercase}h1{margin:8px 0 10px;font-size:clamp(2.5rem,6vw,5.3rem);line-height:.98;font-weight:400}.intro{max-width:720px;color:#596057;font-size:1.08rem}.stats{display:flex;flex-wrap:wrap;gap:28px;margin:25px 0 30px;color:var(--muted);font:12px ui-monospace,SFMono-Regular,Menlo,monospace}.stats b{color:var(--ink);font-weight:500}.card{background:var(--card);border:1px solid var(--line);border-radius:14px;box-shadow:0 5px 18px rgba(50,55,35,.06);margin:16px 0;overflow:hidden}.card-head{display:flex;align-items:center;gap:14px;min-height:64px;padding:14px 20px;border-bottom:1px solid var(--line)}.chips{display:flex;gap:8px;flex-wrap:wrap}.chip,.choice{border:1px solid var(--line);border-radius:99px;background:#fff;color:#596057;padding:8px 13px;font:14px Georgia,serif;cursor:pointer}.choice.active{border-color:transparent;background:#20231f;color:#fff}.chip{color:#fff;border:0}.chip.gold{background:var(--gold)}.chip.blue{background:var(--blue)}.chip.pink{background:var(--pink)}.overview-wrap{padding:14px 20px 10px}canvas{display:block;width:100%}#overview{height:150px;cursor:crosshair}.hint,.footnote{color:var(--muted);font-size:.9rem;padding:8px 20px 16px}.controls{padding:14px 20px 19px}.control-row{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin:6px 0 16px}.control-row .label{margin-right:2px}.check-grid{display:grid;grid-template-columns:repeat(4,minmax(160px,1fr));gap:10px 22px}.check{display:flex;gap:9px;align-items:flex-start;color:#596057;cursor:pointer}.check input{accent-color:var(--gold);margin-top:4px}.swatch{width:9px;height:9px;border-radius:50%;display:inline-block;margin:5px 5px 0 0}.timeline{padding:0 0 12px}#timeline{height:530px;cursor:grab}#timeline.dragging{cursor:grabbing}@media(max-width:720px){main{padding:22px 12px 50px}.check-grid{grid-template-columns:repeat(2,minmax(130px,1fr))}#timeline{height:480px}.stats{gap:14px}}
.timeline-wrap{position:relative}#cursor-line{display:none;position:absolute;z-index:4;top:0;bottom:30px;width:2px;background:#111;box-shadow:0 0 0 1px rgba(255,255,255,.85);pointer-events:none}#cursor-readout{display:none;position:absolute;z-index:5;top:8px;max-width:300px;padding:9px 11px;border:1px solid #bbb;border-radius:6px;background:rgba(255,255,255,.97);box-shadow:0 4px 14px rgba(20,30,20,.18);font:11px/1.45 ui-monospace,SFMono-Regular,Menlo,monospace;pointer-events:none;white-space:nowrap}
</style>
</head>
<body><main>
<div class="eyebrow">Model explorer · Florianópolis (-27.60, -48.50)</div>
<h1>A year, hour by hour</h1>
<p class="intro">Explore illustrative model output from the 2026 irradiance export. Crop groups, temperature inputs, and harvest timing are scenario assumptions, not field observations.</p>
<aside class="synthetic-notice" role="note" style="border:2px solid #a33c70;border-left-width:8px;border-radius:8px;background:#fff;padding:14px 18px;margin:18px 0;color:#252720;font:14px/1.5 Arial,sans-serif"><strong>Scenario assumptions — not field validation</strong><br>__NOTICE__</aside>
<div class="stats"><span><b id="hours">0</b> hours</span><span><b id="cycles">0</b> GDD timing scenarios</span><span><b>8</b> comparison series</span><span>timing by <b>thermal GDD</b></span><span>source <b>Period Components</b></span></div>
<section class="card"><div class="card-head"><span class="label">The whole period</span><div class="chips"><button class="chip gold">0A-0E assumed open</button><button class="chip blue">2B assumed between</button><button class="chip pink">2A/2C assumed under</button></div></div><div class="overview-wrap"><canvas id="overview"></canvas></div><div class="hint">Colors show scenario groupings only: 0A-0E is assumed open, 2B between tracker rows, and 2A/2C under trackers; channel placements are unverified. Vertical markers show unvalidated thermal-time timing scenarios, not measured or recommended harvests. Crop biomass curves are withheld.</div></section>
<section class="card"><div class="controls"><div class="control-row"><span class="label">Window</span><button class="choice" data-span="24">1 day</button><button class="choice" data-span="72">3 days</button><button class="choice active" data-span="336">2 weeks</button><button class="choice" data-span="1460">2 months</button><button class="choice" data-span="all">year</button><span class="label" style="margin-left:12px">go to</span><button class="choice" data-month="0">Jan</button><button class="choice" data-month="3">Apr</button><button class="choice" data-month="6">Jul</button><button class="choice" data-month="9">Oct</button></div><div class="check-grid" id="series-controls"></div></div></section>
<section class="card timeline"><div class="card-head"><span class="label">Detailed model state</span><span id="range-label" style="color:var(--muted)"></span></div><div class="timeline-wrap"><canvas id="timeline"></canvas><div id="cursor-line"></div><div id="cursor-readout"></div></div><div class="footnote">Move the mouse over any graph to see all values at that exact time. Grey bands are night. Scroll over the graph to zoom; drag horizontally to move through time.</div></section>
__CYCLE_SUMMARY__
</main>
<script>
const model=__DATA__;const dates=model.timestamps.map(value=>new Date(value));const order=['light_open','light_between','light_under','pv','fresh_open','fresh_between','fresh_under','tracker'];const selected=new Set(order.filter(key=>key!=='tracker'));let span=dates.length;let center=Math.floor(dates.length/2);let dragStart=null;const controls=document.getElementById('series-controls');document.getElementById('hours').textContent=dates.length.toLocaleString('en-US');document.getElementById('cycles').textContent=model.cycle_count;
order.forEach(key=>{const item=model.series[key];const label=document.createElement('label');label.className='check';label.innerHTML=`<input type="checkbox" ${selected.has(key)?'checked':''}><span><i class="swatch" style="background:${item.color}"></i>${item.label} <small>(${item.unit})</small></span>`;label.querySelector('input').addEventListener('change',event=>{event.target.checked?selected.add(key):selected.delete(key);draw()});controls.appendChild(label)});
function bounds(){if(span==='all')return[0,dates.length-1];const half=Math.floor(span/2);return[Math.max(0,center-half),Math.min(dates.length-1,center+half)]}function dateText(date){return date.toLocaleDateString('en-US',{month:'short',day:'numeric'})}function canvasSetup(canvas){const ratio=devicePixelRatio||1;const box=canvas.getBoundingClientRect();canvas.width=box.width*ratio;canvas.height=box.height*ratio;const ctx=canvas.getContext('2d');ctx.setTransform(ratio,0,0,ratio,0,0);return[ctx,box.width,box.height]}
function drawOverview(){const[ctx,w,h]=canvasSetup(document.getElementById('overview'));const keys=['fresh_open','fresh_between','fresh_under'];const max=Math.max(...keys.flatMap(key=>model.series[key].values.filter(Boolean)),1);ctx.clearRect(0,0,w,h);keys.forEach(key=>{const values=model.series[key].values;ctx.strokeStyle=model.series[key].color;ctx.beginPath();values.forEach((value,i)=>{if(value===null)return;const x=i/(values.length-1)*w,y=h-24-value/max*(h-34);i?ctx.lineTo(x,y):ctx.moveTo(x,y)});ctx.stroke()});model.harvest_indices.forEach(index=>{const x=index/(dates.length-1)*w;ctx.strokeStyle='#d7d8d0';ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x,h-22);ctx.stroke()});const[a,b]=bounds();ctx.fillStyle='rgba(201,120,0,.13)';ctx.fillRect(a/(dates.length-1)*w,0,(b-a)/(dates.length-1)*w,h-22);ctx.strokeStyle='#c97800';ctx.strokeRect(a/(dates.length-1)*w,1,(b-a)/(dates.length-1)*w,h-24);ctx.fillStyle='#7d8175';ctx.font='12px ui-monospace';ctx.fillText(dateText(dates[0]),4,h-5);ctx.fillText(dateText(dates[dates.length-1]),w-74,h-5)}
    // Removed the drawComparison call
function drawComparison(){const[ctx,w,h]=canvasSetup(document.getElementById('comparison'));const[left,right]=bounds();const keys=['fresh_open','fresh_between','fresh_under'];const values=keys.flatMap(key=>model.series[key].values.slice(left,right+1).filter(v=>v!==null));const max=Math.max(...values,1);ctx.clearRect(0,0,w,h);keys.forEach(key=>{const series=model.series[key].values.slice(left,right+1);ctx.strokeStyle=model.series[key].color;ctx.lineWidth=2;ctx.beginPath();series.forEach((value,i)=>{if(value===null)return;const x=48+i/Math.max(1,right-left)*(w-68),y=h-36-value/max*(h-62);i?ctx.lineTo(x,y):ctx.moveTo(x,y)});ctx.stroke()});ctx.strokeStyle='#d7d8d0';ctx.lineWidth=1;for(let i=left;i<=right;i++){if(dates[i].getDate()===1){const x=48+(i-left)/Math.max(1,right-left)*(w-68);ctx.beginPath();ctx.moveTo(x,10);ctx.lineTo(x,h-32);ctx.stroke()}}ctx.fillStyle='#7d8175';ctx.font='11px ui-monospace';ctx.fillText('0 g/m2',8,h-30);ctx.fillText(Math.round(max)+' g/m2',8,20);ctx.textAlign='center';const spanHours=Math.max(1,right-left);const step=spanHours<=48?6:spanHours<=120?12:spanHours<=480?24:spanHours<=1500?168:720;for(let i=left;i<=right;i+=step){const x=48+(i-left)/Math.max(1,right-left)*(w-68);ctx.fillText(axisText(dates[i],spanHours),x,h-10)}ctx.textAlign='start'}
function axisText(date, spanHours){if(!date)return '';const day=date.toLocaleDateString('en-US',{month:'short',day:'numeric'});return spanHours<=72?`${day} ${date.toLocaleTimeString('en-US',{hour:'2-digit',minute:'2-digit',hour12:false})}`:day}
function valueText(value,key){if(key==='pv')return value.toFixed(1)+' kW';if(key.startsWith('light_'))return value.toFixed(0)+' W/m2';if(key==='tracker')return value.toFixed(1)+' deg';return value.toFixed(0)+' g/m2'}
function draw(){drawOverview();const canvas=document.getElementById('timeline');const[ctx,w,h]=canvasSetup(canvas);ctx.clearRect(0,0,w,h);const[left,right]=bounds();const active=order.filter(key=>selected.has(key));const plotHeight=h-30;const bandH=Math.max(58,plotHeight/Math.max(active.length,1));const plotWidth=Math.max(120,w-360);const spanHours=Math.max(1,right-left);document.getElementById('range-label').textContent=`${dateText(dates[left])} – ${dateText(dates[right])}`;active.forEach((key,row)=>{const top=row*bandH,item=model.series[key];ctx.fillStyle='#f4f4ef';ctx.fillRect(0,top,w,bandH-1);ctx.fillStyle='#252720';ctx.font='14px Georgia';ctx.fillText(item.label,16,top+22);ctx.fillStyle=item.color;ctx.font='12px ui-monospace';ctx.fillText(item.unit,16,top+41);const values=item.values.slice(left,right+1),nums=values.filter(v=>v!==null),max=Math.max(...nums,1),min=Math.min(...nums,0);ctx.strokeStyle=item.color;ctx.beginPath();values.forEach((value,i)=>{if(value===null)return;const x=180+i/Math.max(1,right-left)*plotWidth,y=top+bandH-12-(value-min)/Math.max(1,max-min)*(bandH-28);i?ctx.lineTo(x,y):ctx.moveTo(x,y)});ctx.stroke();const current=nums[nums.length-1]??0;ctx.fillStyle=item.color;ctx.font='11px ui-monospace';ctx.fillText('now '+valueText(current,key),w-170,top+20);ctx.fillStyle='#7d8175';ctx.font='10px ui-monospace';ctx.fillText('min '+valueText(Math.min(...nums),key),w-170,top+36);ctx.fillText('max '+valueText(Math.max(...nums),key),w-170,top+50)});const tickStep=spanHours<=48?6:spanHours<=120?12:spanHours<=480?24:spanHours<=1500?168:720;ctx.font='11px ui-monospace';ctx.textAlign='center';for(let i=left;i<=right;i+=tickStep){const x=180+(i-left)/Math.max(1,right-left)*plotWidth;ctx.strokeStyle=dates[i].getDate()===1?'#c9cbc2':'#e3e4de';ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x,plotHeight);ctx.stroke();ctx.fillStyle='#7d8175';ctx.fillText(axisText(dates[i],spanHours),x,h-9)}ctx.textAlign='start';}
document.querySelectorAll('[data-span]').forEach(button=>button.addEventListener('click',()=>{span=button.dataset.span==='all'?'all':Number(button.dataset.span);document.querySelectorAll('[data-span]').forEach(item=>item.classList.toggle('active',item===button));draw()}));document.querySelectorAll('[data-month]').forEach(button=>button.addEventListener('click',()=>{const found=dates.findIndex(date=>date.getMonth()===Number(button.dataset.month));if(found>=0){center=found;draw()}}));document.getElementById('overview').addEventListener('click',event=>{const rect=event.currentTarget.getBoundingClientRect();center=Math.round((event.clientX-rect.left)/rect.width*(dates.length-1));draw()});const timeline=document.getElementById('timeline');timeline.addEventListener('pointerdown',event=>{dragStart={x:event.clientX,center};timeline.classList.add('dragging');timeline.setPointerCapture(event.pointerId)});timeline.addEventListener('pointermove',event=>{if(!dragStart||span==='all')return;const width=timeline.getBoundingClientRect().width;center=Math.max(0,Math.min(dates.length-1,dragStart.center-Math.round((event.clientX-dragStart.x)/width*span)));draw()});timeline.addEventListener('pointerup',()=>{dragStart=null;timeline.classList.remove('dragging')});timeline.addEventListener('wheel',event=>{event.preventDefault();span=Math.max(24,Math.min(dates.length,Math.round(span*(event.deltaY>0?1.25:.8))));document.querySelectorAll('[data-span]').forEach(item=>item.classList.remove('active'));draw()},{passive:false});addEventListener('resize',draw);draw();
function drawGrouped(){drawOverview();const canvas=document.getElementById('timeline');const[ctx,w,h]=canvasSetup(canvas);ctx.clearRect(0,0,w,h);const[left,right]=bounds();const groups=[{label:'crop light comparison',unit:'W/m2',keys:['light_open','light_between','light_under']},{label:'PV power',unit:'kW',keys:['pv']},{label:'crop biomass withheld (uncalibrated)',unit:'',keys:['fresh_open','fresh_between','fresh_under']},{label:'observed tracker angle',unit:'degrees',keys:['tracker']}];const active=groups.filter(group=>group.keys.some(key=>selected.has(key)));const plotHeight=h-30;const bandH=Math.max(72,plotHeight/Math.max(active.length,1));const plotWidth=Math.max(120,w-360);const spanHours=Math.max(1,right-left);document.getElementById('range-label').textContent=`${dateText(dates[left])} – ${dateText(dates[right])}`;active.forEach((group,row)=>{const top=row*bandH;const keys=group.keys.filter(key=>selected.has(key));ctx.fillStyle='#f4f4ef';ctx.fillRect(0,top,w,bandH-1);ctx.fillStyle='#252720';ctx.font='14px Georgia';ctx.fillText(group.label,16,top+22);ctx.fillStyle='#7d8175';ctx.font='12px ui-monospace';ctx.fillText(group.unit,16,top+41);const allValues=keys.flatMap(key=>model.series[key].values.slice(left,right+1).filter(v=>v!==null));const max=Math.max(...allValues,1);const min=Math.min(...allValues,0);keys.forEach((key,line)=>{const values=model.series[key].values.slice(left,right+1);ctx.strokeStyle=model.series[key].color;ctx.lineWidth=1.7;ctx.beginPath();values.forEach((value,i)=>{if(value===null)return;const x=180+i/Math.max(1,right-left)*plotWidth,y=top+bandH-12-(value-min)/Math.max(1,max-min)*(bandH-28);i?ctx.lineTo(x,y):ctx.moveTo(x,y)});ctx.stroke();const nums=values.filter(v=>v!==null);ctx.fillStyle=model.series[key].color;ctx.font='10px ui-monospace';ctx.fillText(model.series[key].label.replace(' light','').replace('fresh biomass, ',''),w-170,top+16+line*13);ctx.fillText(nums.length?valueText(nums[nums.length-1],key):'withheld',w-170,top+29+line*13)});});const tickStep=spanHours<=48?6:spanHours<=120?12:spanHours<=480?24:spanHours<=1500?168:720;ctx.font='11px ui-monospace';ctx.textAlign='center';for(let i=left;i<=right;i+=tickStep){const x=180+(i-left)/Math.max(1,right-left)*plotWidth;ctx.strokeStyle=dates[i].getDate()===1?'#c9cbc2':'#e3e4de';ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x,plotHeight);ctx.stroke();ctx.fillStyle='#7d8175';ctx.fillText(axisText(dates[i],spanHours),x,h-9)}ctx.textAlign='start'}
function cursorValue(key,index){const value=model.series[key].values[index];return value===null||value===undefined?'–':valueText(value,key)}
function showCursor(event){const canvas=document.getElementById('timeline');const wrapper=document.querySelector('.timeline-wrap');const line=document.getElementById('cursor-line');const readout=document.getElementById('cursor-readout');const rect=canvas.getBoundingClientRect();const[left,right]=bounds();const plotLeft=180;const plotWidth=Math.max(120,rect.width-360);const localX=Math.max(plotLeft,Math.min(rect.width-180,event.clientX-rect.left));const index=Math.max(left,Math.min(right,left+Math.round((localX-plotLeft)/plotWidth*(right-left))));const x=plotLeft+(index-left)/Math.max(1,right-left)*plotWidth;line.style.display='block';line.style.left=x+'px';readout.style.display='block';readout.style.left=(x>rect.width-300?Math.max(6,x-285):x+10)+'px';readout.innerHTML='<strong>'+dates[index].toLocaleDateString('en-US',{month:'short',day:'numeric'})+' '+dates[index].toLocaleTimeString('en-US',{hour:'2-digit',minute:'2-digit',hour12:false})+'</strong><br><span style="color:#d48300">Open light: '+cursorValue('light_open',index)+' · biomass: '+cursorValue('fresh_open',index)+'</span><br><span style="color:#2f82b9">Between light: '+cursorValue('light_between',index)+' · biomass: '+cursorValue('fresh_between',index)+'</span><br><span style="color:#a33c70">Under light: '+cursorValue('light_under',index)+' · biomass: '+cursorValue('fresh_under',index)+'</span><br><span style="color:#2f82b9">PV power: '+cursorValue('pv',index)+'</span>'}
function hideCursor(){document.getElementById('cursor-line').style.display='none';document.getElementById('cursor-readout').style.display='none'}
document.getElementById('timeline').addEventListener('pointermove',showCursor);document.getElementById('timeline').addEventListener('pointerleave',hideCursor);
function draw(){return drawGrouped()}
</script></body></html>'''


def render_report_template(
    model_data: dict,
    synthetic_notice: str,
    cycle_frames: dict[str, pd.DataFrame],
) -> str:
    return (
        TEMPLATE.replace("__DATA__", json.dumps(model_data, separators=(",", ":")))
        .replace("__NOTICE__", html.escape(synthetic_notice))
        .replace("__CYCLE_SUMMARY__", cycle_summary_html(cycle_frames))
        .replace(
            "crop biomass withheld (uncalibrated)",
            "modeled fresh-mass equivalent (uncalibrated)",
        )
        .replace(
            "Crop biomass curves are withheld.",
            "Curves are uncalibrated modeled fresh-mass equivalents; see the cycle table below.",
        )
    )


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    build_report(args.input, args.output)


if __name__ == "__main__":
    main()
