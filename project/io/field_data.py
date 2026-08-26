"""Map raw datalogger exports (Campbell Scientific style) to canonical sensor roles.

The Fotovoltaica/UFSC station exports columns named after the logger and probe,
for example ``CR1Kx-TempMod1``, ``CR310-04-Par``, or ``CR310_01-Ws``. Several
probes of the same physical quantity are common (redundant module-temperature
sensors, several PAR quantum sensors, etc.), and a mid-deployment channel
rename can leave two historical column names for the same instrument (e.g.
``CR310_01-Ws`` and ``CR310_01_-Ws``). This module recognizes those naming
patterns, groups columns by logger/subzone, and aggregates redundant probes
into one physically meaningful value per role so the rest of the pipeline
never has to know about raw logger column names.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import pandas as pd

from project.qc.cleaning import (
    AIR_TEMP_C,
    FIELD_BOUNDS,
    MODULE_TEMP_C,
    PPFD_UMOL_M2_S,
    PRECIPITATION_MM,
    PRESSURE_HPA,
    RELATIVE_HUMIDITY_PCT,
    WIND_SPEED_MS,
    reject_series,
)

__all__ = [
    "MODULE_TEMP_C",
    "AIR_TEMP_C",
    "PPFD_UMOL_M2_S",
    "RELATIVE_HUMIDITY_PCT",
    "PRECIPITATION_MM",
    "WIND_SPEED_MS",
    "PRESSURE_HPA",
    "FieldMapping",
    "classify_column",
    "classify_columns",
    "to_canonical_frames",
    "raw_probe_quality_report",
]

# Checked in order: "TempMod"/"TempAr" must be tested before the generic "Par"
# pattern, since e.g. "TempAr1" ends in a substring that would otherwise be
# mistaken for a PAR channel.
_FIELD_KEYWORDS: tuple[tuple[str, str], ...] = (
    (MODULE_TEMP_C, "TempMod"),
    (AIR_TEMP_C, "TempAr"),
    (PPFD_UMOL_M2_S, "Par"),
    (RELATIVE_HUMIDITY_PCT, "RH"),
    (PRECIPITATION_MM, "RA"),
    (WIND_SPEED_MS, "Ws"),
    (PRESSURE_HPA, "Pressure"),
)
_KEYWORD_PATTERNS = [
    (role, re.compile(re.escape(keyword) + r"\d*$", re.IGNORECASE))
    for role, keyword in _FIELD_KEYWORDS
]


def _normalize_logger_id(raw_prefix: str) -> str:
    """Collapse separator/rename noise so the same physical logger always groups together.

    Strips a trailing "-"/"_" run (e.g. the "CR310_01_-Ws" rename artifact) and
    unifies "_" and "-" separators so "CR310_04" and "CR310-04" are one subzone.
    """
    return raw_prefix.strip("-_").replace("_", "-")


def classify_column(column: str) -> tuple[str, str] | None:
    """Return ``(logger_id, role)`` for a recognized raw column, else ``None``."""
    for role, pattern in _KEYWORD_PATTERNS:
        match = pattern.search(column)
        if match:
            logger_id = _normalize_logger_id(column[: match.start()])
            if not logger_id:
                continue
            return logger_id, role
    return None


@dataclass
class FieldMapping:
    """Grouped raw columns per logger/subzone and canonical role."""

    subzones: dict[str, dict[str, list[str]]] = field(default_factory=dict)
    unmapped_columns: list[str] = field(default_factory=list)


def classify_columns(columns) -> FieldMapping:
    """Classify every column name into (subzone, role) or record it as unmapped."""
    mapping = FieldMapping()
    for column in columns:
        classified = classify_column(str(column))
        if classified is None:
            mapping.unmapped_columns.append(str(column))
            continue
        logger_id, role = classified
        roles = mapping.subzones.setdefault(logger_id, {})
        roles.setdefault(role, []).append(column)
    return mapping


def to_canonical_frames(
    frame: pd.DataFrame, mapping: FieldMapping | None = None
) -> dict[str, pd.DataFrame]:
    """Aggregate redundant probes per logger into one canonical wide frame per subzone.

    Each canonical role is the median across the probes recognized for that role
    and timestamp (ignoring missing probes). A ``<role>_n_probes`` column records
    how many probes contributed at each timestamp, which is useful for quality
    reporting and for spotting a station-wide outage versus a single dead probe.
    """
    mapping = mapping or classify_columns(frame.columns)
    canonical_frames: dict[str, pd.DataFrame] = {}
    for subzone_id, roles in mapping.subzones.items():
        canonical = pd.DataFrame(index=frame.index)
        for role, raw_columns in roles.items():
            values = frame[raw_columns].apply(pd.to_numeric, errors="coerce")
            canonical[role] = values.median(axis=1, skipna=True)
            canonical[f"{role}_n_probes"] = values.notna().sum(axis=1)
        canonical_frames[subzone_id] = canonical
    return canonical_frames


def raw_probe_quality_report(frame: pd.DataFrame, mapping: FieldMapping | None = None) -> pd.DataFrame:
    """Per raw sensor column fault counts, before multi-probe aggregation can hide them.

    A single faulty probe among several redundant ones (e.g. one of four
    ``TempMod`` sensors) is correctly outvoted by the median in
    :func:`to_canonical_frames`, which is the right behavior for the canonical
    value. But that same averaging means :func:`project.qc.cleaning.quality_report`,
    run on the already-aggregated frame, can under-report how many individual
    probes actually failed. This checks every raw column individually against
    the same physical bounds so a lone bad probe stays visible for maintenance.
    """
    mapping = mapping or classify_columns(frame.columns)
    rows = []
    for subzone_id, roles in mapping.subzones.items():
        for role, raw_columns in roles.items():
            bounds = FIELD_BOUNDS.get(role)
            if bounds is None:
                continue
            for column in raw_columns:
                series = pd.to_numeric(frame[column], errors="coerce")
                valid = series.notna()
                cleaned = reject_series(series, bounds)
                rows.append(
                    {
                        "subzone_id": subzone_id,
                        "column": column,
                        "role": role,
                        "raw_samples": int(valid.sum()),
                        "rejected_samples": int((valid & cleaned.isna()).sum()),
                    }
                )
    return pd.DataFrame(rows).set_index(["subzone_id", "column"]) if rows else pd.DataFrame(
        columns=["role", "raw_samples", "rejected_samples"]
    )

