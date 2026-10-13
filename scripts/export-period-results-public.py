from __future__ import annotations

from pathlib import Path
import json
import logging

import pandas as pd

from project.io.period_results import period_results_data_source
from project.scenarios.artifact_metadata import build_artifact_metadata

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "project" / "data" / "raw" / "Period_Components.csv"
TARGET = ROOT / "public" / "data" / "period-results-2026.js"


def export_records(
    source: Path,
    *,
    as_of: str | pd.Timestamp | None = None,
) -> list[dict[str, object]]:
    frame = pd.read_csv(source, usecols=["datetime", "GHI", "DNI", "DHI"])
    timestamps = pd.to_datetime(frame["datetime"], errors="coerce")
    if timestamps.isna().any() or timestamps.dt.tz is None:
        raise ValueError("Public period data must contain valid timezone-aware datetimes")
    data_sources = period_results_data_source(pd.DatetimeIndex(timestamps), as_of=as_of)

    records = []
    for timestamp, ghi, dni, dhi, data_source in zip(
        timestamps, frame["GHI"], frame["DNI"], frame["DHI"], data_sources
    ):
        records.append({
            "datetime": timestamp.isoformat(),
            "ghi": round(float(ghi), 3) if pd.notna(ghi) else None,
            "dni": round(float(dni), 3) if pd.notna(dni) else None,
            "dhi": round(float(dhi), 3) if pd.notna(dhi) else None,
            "data_source": data_source,
        })
    return records


def main() -> None:
    as_of = pd.Timestamp.now(tz="America/Sao_Paulo")
    records = export_records(SOURCE, as_of=as_of)
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(
        "window.AGRIPV_BUILD_INFO = "
        + json.dumps(build_artifact_metadata(), separators=(",", ":"))
        + ";\nwindow.AGRIPV_PERIOD_RESULTS_AS_OF = "
        + json.dumps(as_of.isoformat())
        + ";\nwindow.AGRIPV_PERIOD_RESULTS_2026 = "
        + json.dumps(records, separators=(",", ":"), allow_nan=False)
        + ";\n",
        encoding="utf-8",
    )
    logging.info("Wrote %s records to %s", len(records), TARGET.relative_to(ROOT))


if __name__ == "__main__":
    main()
