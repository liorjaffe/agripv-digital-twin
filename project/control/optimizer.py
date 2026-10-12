"""Tracker optimization: choose a tilt schedule from pvlib-evaluated candidates."""

from __future__ import annotations

import math

import pandas as pd


def _light_objective(
    crop_ppfd_umol_m2_s: float,
    minimum_ppfd_umol_m2_s: float,
    maximum_ppfd_umol_m2_s: float,
) -> float:
    """Penalize falling below a daily-light target or exceeding its ceiling."""
    if crop_ppfd_umol_m2_s < minimum_ppfd_umol_m2_s:
        return minimum_ppfd_umol_m2_s - crop_ppfd_umol_m2_s
    if crop_ppfd_umol_m2_s > maximum_ppfd_umol_m2_s:
        return crop_ppfd_umol_m2_s - maximum_ppfd_umol_m2_s
    return 0.0


def optimize_tilt_schedule(
    candidates: dict[float, pd.DataFrame],
    target_ppfd: pd.Series,
    *,
    previous_tilt: float | None = None,
    max_move_deg: float | None = None,
    pv_loss_weight: float = 0.0,
    movement_weight: float = 0.0,
    dli_target_mol_m2_day: float | None = None,
    dli_max_mol_m2_day: float | None = None,
    daylight_seconds: pd.Series | None = None,
) -> pd.DataFrame:
    """Choose a tilt at each timestep from pvlib-evaluated candidate results.

    Each candidate frame must contain ``crop_ppfd_umol_m2_s`` and ``pv_power_w``.
    Optional daily DLI bounds use feedback from the day's accumulated light and
    remaining daylight. This avoids rewarding excess light after the configured
    DLI ceiling has been reached.
    """
    if not candidates:
        raise ValueError("candidates must contain at least one tilt")
    tilts = sorted(float(tilt) for tilt in candidates)
    index = target_ppfd.index
    dynamic_dli = dli_target_mol_m2_day is not None or dli_max_mol_m2_day is not None
    if dynamic_dli:
        if dli_target_mol_m2_day is None or dli_max_mol_m2_day is None or daylight_seconds is None:
            raise ValueError("daily DLI target, maximum, and daylight_seconds must be supplied together")
        if dli_target_mol_m2_day <= 0.0 or dli_max_mol_m2_day < dli_target_mol_m2_day:
            raise ValueError("daily DLI bounds must satisfy 0 < target <= maximum")
        if not isinstance(daylight_seconds.index, pd.DatetimeIndex):
            raise TypeError("daylight_seconds must use a DatetimeIndex")
        if not index.equals(daylight_seconds.index):
            raise ValueError("daylight_seconds must align with target_ppfd")
        daylight_seconds = daylight_seconds.astype(float).clip(lower=0.0)
        daily_daylight_seconds = daylight_seconds.groupby(daylight_seconds.index.normalize()).sum()
    selected = []
    last_tilt = previous_tilt
    accumulated_dli_by_day: dict[pd.Timestamp, float] = {}
    elapsed_daylight_by_day: dict[pd.Timestamp, float] = {}
    for timestamp in index:
        target = float(target_ppfd.loc[timestamp])
        minimum_ppfd = target
        maximum_ppfd = target
        if dynamic_dli:
            day = timestamp.normalize()
            interval_daylight = float(daylight_seconds.loc[timestamp])
            total_daylight = float(daily_daylight_seconds.get(day, 0.0))
            accumulated_dli = accumulated_dli_by_day.get(day, 0.0)
            elapsed_daylight = elapsed_daylight_by_day.get(day, 0.0)
            remaining_daylight = max(0.0, total_daylight - elapsed_daylight)
            if interval_daylight > 0.0 and remaining_daylight > 0.0:
                minimum_ppfd = max(
                    0.0,
                    (dli_target_mol_m2_day * 1_000_000.0 - accumulated_dli)
                    / remaining_daylight,
                )
                maximum_ppfd = max(
                    0.0,
                    (dli_max_mol_m2_day * 1_000_000.0 - accumulated_dli)
                    / remaining_daylight,
                )
                minimum_ppfd = min(minimum_ppfd, maximum_ppfd)
            else:
                minimum_ppfd = maximum_ppfd = 0.0
        valid_candidates = {}
        for tilt, candidate in candidates.items():
            values = candidate.loc[timestamp]
            crop_ppfd = float(values["crop_ppfd_umol_m2_s"])
            power = float(values["pv_power_w"])
            if math.isfinite(crop_ppfd) and math.isfinite(power):
                valid_candidates[float(tilt)] = values
        max_power = max(
            (float(values["pv_power_w"]) for values in valid_candidates.values()),
            default=0.0,
        )
        scored = []
        for tilt in tilts:
            move = 0.0 if last_tilt is None else abs(tilt - last_tilt)
            if max_move_deg is not None and move > max_move_deg:
                continue
            values = valid_candidates.get(tilt)
            if values is None:
                continue
            crop_ppfd = float(values["crop_ppfd_umol_m2_s"])
            pv_loss = max_power - float(values["pv_power_w"])
            score = _light_objective(crop_ppfd, minimum_ppfd, maximum_ppfd)
            score += pv_loss_weight * pv_loss + movement_weight * move
            scored.append((score, tilt))
        if not scored:
            chosen = last_tilt if last_tilt is not None else tilts[0]
        else:
            chosen = min(scored)[1]
        selected.append(chosen)
        last_tilt = chosen
        if dynamic_dli:
            chosen_ppfd = float(candidates[chosen].loc[timestamp, "crop_ppfd_umol_m2_s"])
            interval_daylight = float(daylight_seconds.loc[timestamp])
            day = timestamp.normalize()
            if math.isfinite(chosen_ppfd):
                accumulated_dli_by_day[day] = (
                    accumulated_dli_by_day.get(day, 0.0)
                    + chosen_ppfd * interval_daylight / 1_000_000.0
                )
            elapsed_daylight_by_day[day] = (
                elapsed_daylight_by_day.get(day, 0.0) + interval_daylight
            )

    return pd.DataFrame({"tilt_deg": selected}, index=index)
