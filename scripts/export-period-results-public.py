from __future__ import annotations

from io import StringIO
from pathlib import Path
import json

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "project" / "data" / "raw" / "Period_Results.xlsx"
TARGET = ROOT / "public" / "data" / "period-results-2026.js"


def main() -> None:
    lines = pd.read_excel(SOURCE, sheet_name="in", header=None).iloc[:, 0].dropna().astype(str)
    header_index = next(
        index for index, line in enumerate(lines)
        if line.startswith("date,datetime,GHI,DNI,DHI,")
    )
    frame = pd.read_csv(
        StringIO("\n".join(lines.iloc[header_index:].tolist())),
        usecols=["datetime", "GHI", "DNI", "DHI"],
    )
    records = [
        {
            "datetime": str(row.datetime),
            "ghi": round(float(row.GHI), 3),
            "dni": round(float(row.DNI), 3),
            "dhi": round(float(row.DHI), 3),
        }
        for row in frame.itertuples(index=False)
    ]
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(
        "window.AGRIPV_PERIOD_RESULTS_2026 = "
        + json.dumps(records, separators=(",", ":"))
        + ";\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(records)} records to {TARGET.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
