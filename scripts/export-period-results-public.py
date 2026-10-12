from __future__ import annotations

from pathlib import Path
import json
import logging

import pandas as pd

from project.scenarios.artifact_metadata import build_artifact_metadata

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "project" / "data" / "raw" / "Period_Components.csv"
TARGET = ROOT / "public" / "data" / "period-results-2026.js"


def export_records(source: Path) -> list[dict[str, object]]:
    frame = pd.read_csv(source, usecols=["datetime", "GHI", "DNI", "DHI"])
    timestamps = pd.to_datetime(frame["datetime"], errors="coerce")
    if timestamps.isna().any() or timestamps.dt.tz is None:
        raise ValueError("Public period data must contain valid timezone-aware datetimes")

    records = []
    for timestamp, ghi, dni, dhi in zip(
        timestamps, frame["GHI"], frame["DNI"], frame["DHI"]
    ):
        records.append({
            "datetime": timestamp.isoformat(),
            "ghi": round(float(ghi), 3) if pd.notna(ghi) else None,
            "dni": round(float(dni), 3) if pd.notna(dni) else None,
            "dhi": round(float(dhi), 3) if pd.notna(dhi) else None,
        })
    return records


def main() -> None:
    records = export_records(SOURCE)
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(
        "window.AGRIPV_BUILD_INFO = "
        + json.dumps(build_artifact_metadata(), separators=(",", ":"))
        + ";\nwindow.AGRIPV_PERIOD_RESULTS_2026 = "
        + json.dumps(records, separators=(",", ":"), allow_nan=False)
        + ";\n",
        encoding="utf-8",
    )
    logging.info("Wrote %s records to %s", len(records), TARGET.relative_to(ROOT))


if __name__ == "__main__":
    main()
