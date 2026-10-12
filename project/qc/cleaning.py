"""QC helpers for agrivoltaic sensor data.

This is structured to support a historical data workflow and a future live stream workflow.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

# Canonical sensor roles shared with project.io.field_data. Defined here because
# the physical plausibility bounds below are this module's authoritative
# contract for what each role means; field_data.py imports these names instead
# of redefining them.
MODULE_TEMP_C = "module_temp_c"
AIR_TEMP_C = "air_temp_c"
PPFD_UMOL_M2_S = "ppfd_umol_m2_s"
RELATIVE_HUMIDITY_PCT = "relative_humidity_pct"
PRECIPITATION_MM = "precipitation_mm"
WIND_SPEED_MS = "wind_speed_ms"
PRESSURE_HPA = "pressure_hpa"


@dataclass(frozen=True)
class FieldBounds:
    """Physical plausibility envelope for one canonical sensor role."""

    lower: float
    upper: float
    max_step: float | None = None  # largest plausible change between consecutive samples


# Bounds are intentionally generous so genuine weather extremes always survive,
# but tight enough to catch the datalogger fault patterns seen in real field
# exports: temperature dropouts to roughly -300 degC, PAR spikes to roughly
# 8000 umol/m2/s (physically full sun tops out near 2200), wind-speed dropouts
# to negative sentinel values, and pressure dropouts to 0 hPa or spikes near
# 600 hPa. ``max_step`` is a slew-rate limit used only where real physics
# changes slowly (temperature, pressure); PPFD can legitimately jump within one
# sample when a cloud edge passes, so it is bounded but not slew-limited.
FIELD_BOUNDS: dict[str, FieldBounds] = {
    MODULE_TEMP_C: FieldBounds(lower=-15.0, upper=85.0, max_step=25.0),
    AIR_TEMP_C: FieldBounds(lower=5.0, upper=40.0, max_step=12.0),
    PPFD_UMOL_M2_S: FieldBounds(lower=0.0, upper=2500.0),
    RELATIVE_HUMIDITY_PCT: FieldBounds(lower=0.0, upper=100.0),
    PRECIPITATION_MM: FieldBounds(lower=0.0, upper=50.0),
    WIND_SPEED_MS: FieldBounds(lower=0.0, upper=60.0),
    PRESSURE_HPA: FieldBounds(lower=850.0, upper=1100.0, max_step=12.0),
}


def _require_tz_aware_index(frame: pd.DataFrame) -> None:
    if not isinstance(frame.index, pd.DatetimeIndex):
        raise TypeError("frame must use a DatetimeIndex")
    if frame.index.tz is None:
        raise ValueError("frame timestamps must be timezone-aware")


def reject_series(series: pd.Series, bounds: FieldBounds) -> pd.Series:
    """Replace physically impossible samples with NaN instead of clipping them.

    Clipping would silently rewrite an obviously broken reading (e.g. -300 degC)
    into a plausible-looking boundary value; treating it as missing keeps the
    fault visible so the gap-limited interpolation downstream can decide
    whether it is even bridgeable.
    """
    clean = series.where((series >= bounds.lower) & (series <= bounds.upper))
    if bounds.max_step is not None and clean.notna().any():
        elapsed_hours = clean.index.to_series().diff().dt.total_seconds() / 3600.0
        allowed = bounds.max_step * elapsed_hours.clip(lower=1.0 / 60.0)
        spike = clean.diff().abs() > allowed
        clean = clean.where(~spike.fillna(False))
    return clean


def reject_out_of_bounds(frame: pd.DataFrame) -> pd.DataFrame:
    """Apply physical-bounds and spike rejection to every recognized canonical role.

    Unrecognized columns are passed through untouched. This does not resample or
    interpolate, so it is safe to compare against the input index-for-index
    (see :func:`quality_report`).
    """
    _require_tz_aware_index(frame)
    out = frame.sort_index().copy()
    for role, bounds in FIELD_BOUNDS.items():
        if role in out.columns:
            out[role] = reject_series(pd.to_numeric(out[role], errors="coerce"), bounds)
    return out


def clean_field_frame(
    frame: pd.DataFrame,
    *,
    interval: str = "15min",
    max_gap_periods: int = 4,
) -> pd.DataFrame:
    """Clean one canonical per-subzone sensor frame produced by ``project.io.field_data``.

    Steps: reject physically-impossible or spiky samples (as NaN, not clipped),
    resample to a uniform interval, then bridge only short gaps (up to
    ``max_gap_periods`` consecutive missing samples, one hour by default at
    15-minute resolution). Longer comms outages are deliberately left as NaN
    rather than invented, so a multi-day station outage never masquerades as
    real data downstream.
    """
    rejected = reject_out_of_bounds(frame)
    out = rejected.resample(interval).mean()
    out = out.interpolate(method="time", limit=max_gap_periods, limit_area="inside")
    return out


def quality_report(raw: pd.DataFrame) -> pd.DataFrame:
    """Summarize, per canonical role, how many raw samples were physically implausible.

    Useful for surfacing sensor health (e.g. in a dashboard or log) instead of
    silently trusting a mostly-faulty channel.
    """
    rejected = reject_out_of_bounds(raw)
    rows = []
    for role in FIELD_BOUNDS:
        if role not in raw.columns:
            continue
        raw_valid = pd.to_numeric(raw[role], errors="coerce").notna()
        still_valid = rejected[role].notna()
        total = len(raw)
        rows.append(
            {
                "role": role,
                "raw_samples": int(raw_valid.sum()),
                "rejected_samples": int((raw_valid & ~still_valid).sum()),
                "valid_fraction_after_qc": float(still_valid.sum() / total) if total else float("nan"),
            }
        )
    return pd.DataFrame(rows).set_index("role")
