"""Example entry point: process the bundled sample multi-logger station export.

Run with:
    PYTHONPATH=. .venv/bin/python3 project/scenarios/run_sample_field_export.py

This exercises the full real-data chain end to end on
``project/data/raw/station_export.csv``, a synthetic export that mirrors the
real Fotovoltaica/UFSC Grafana export: the same logger/column naming
(``CR1Kx-TempMod1``, ``CR310_01-Ws``/``CR310_01_-Ws`` after a mid-deployment
channel rename, ...) and the same sensor-fault patterns (a module-temperature
dropout to -300 degC, a PAR spike to 8000 umol/m2/s, a wind-speed sentinel of
-100, and a pressure dropout/spike) seen in the field.
"""

from __future__ import annotations

from pathlib import Path

from project.config import make_site_location
from project.io.commands import DryRunCommandSink
from project.io.field_data import classify_columns, raw_probe_quality_report, to_canonical_frames
from project.io.ingestion import load_timeseries
from project.io.service import process_field_export
from project.qc.cleaning import quality_report

SAMPLE_EXPORT = Path(__file__).resolve().parents[1] / "data" / "raw" / "station_export.csv"


def main() -> None:
    location = make_site_location()

    print(f"Loading {SAMPLE_EXPORT.name} ...")
    raw = load_timeseries(SAMPLE_EXPORT, time_column="TIMESTAMP")
    mapping = classify_columns(raw.columns)
    canonical_frames = to_canonical_frames(raw, mapping)
    print(f"Recognized {len(canonical_frames)} logger/subzone(s): {sorted(canonical_frames)}\n")

    print("--- Per-probe faults (before median aggregation can hide a lone bad sensor) ---")
    probe_report = raw_probe_quality_report(raw, mapping)
    print(probe_report[probe_report["rejected_samples"] > 0].to_string())
    print()

    for subzone_id, canonical in canonical_frames.items():
        report = quality_report(canonical)
        print(f"--- Sensor quality for {subzone_id} (aggregated canonical value) ---")
        print(report.to_string() if not report.empty else "(no recognized roles)")
        print()

    sink = DryRunCommandSink()
    outputs = process_field_export(SAMPLE_EXPORT, location, command_sink=sink)

    for subzone_id, (results, daily, *_) in outputs.items():
        print(f"=== {subzone_id}: {len(results)} timesteps, {len(daily)} day(s) ===")
        print(daily.round(2).to_string())
        print()

    print(f"Dry-run tracker commands emitted: {len(sink.commands)}")


if __name__ == "__main__":
    main()
