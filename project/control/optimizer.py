"""Tracker optimization: choose a tilt schedule from pvlib-evaluated candidates."""

from __future__ import annotations

import math

import pandas as pd

from project.models.conversions import (
    dli_from_timeseries,
    dli_interval_contribution,
)


def _light_objective(
    crop_ppfd_umol_m2_s: float,
    minimum_ppfd_umol_m2_s: float,
    maximum_ppfd_umol_m2_s: float,
) -> float:
    """Penalize a light deficit and, when feasible, light above the ceiling."""
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
    previous_tracker_theta: float | None = None,
    movement_override: pd.Series | None = None,
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
    if (
        not math.isfinite(pv_loss_weight)
        or not math.isfinite(movement_weight)
        or pv_loss_weight < 0.0
        or movement_weight < 0.0
    ):
        raise ValueError("optimizer weights must be finite and non-negative")
    tilts = sorted(float(tilt) for tilt in candidates)
    index = target_ppfd.index
    if movement_override is not None and not index.equals(movement_override.index):
        raise ValueError("movement_override must align with target_ppfd")
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
        candidate_ppfd = pd.concat(
            {
                float(tilt): candidate["crop_ppfd_umol_m2_s"].reindex(index)
                for tilt, candidate in candidates.items()
            },
            axis=1,
        )
        daylight_mask = daylight_seconds.gt(0.0)
        complete_daylight_inputs = (
            candidate_ppfd.notna().all(axis=1) | ~daylight_mask
        ).groupby(index.normalize()).all()
        candidate_min_ppfd = candidate_ppfd.min(axis=1).where(daylight_mask, 0.0)
        candidate_max_ppfd = candidate_ppfd.max(axis=1).where(daylight_mask, 0.0)
        candidate_min_dli = dli_from_timeseries(candidate_min_ppfd).where(
            complete_daylight_inputs
        )
        candidate_max_dli = dli_from_timeseries(candidate_max_ppfd).where(
            complete_daylight_inputs
        )
        daily_ceiling_reachable = candidate_min_dli.le(dli_max_mol_m2_day)
        daily_minimum_reachable = candidate_max_dli.ge(dli_target_mol_m2_day)
        daily_band_reachable = daily_ceiling_reachable & daily_minimum_reachable
        daily_candidate_dli = pd.DataFrame(
            {
                "candidate_min_dli_mol_m2_day": candidate_min_dli,
                "candidate_max_dli_mol_m2_day": candidate_max_dli,
                "candidate_dli_minimum_reachable": daily_minimum_reachable,
                "candidate_dli_ceiling_reachable": daily_ceiling_reachable,
                "candidate_dli_target_band_reachable": daily_band_reachable,
            }
        )
        daily_candidate_dli["dli_ceiling_enforced"] = daily_ceiling_reachable
    selected = []
    last_tilt = previous_tilt
    last_tracker_theta = (
        previous_tracker_theta
        if previous_tracker_theta is not None
        else previous_tilt
    )
    accumulated_dli_by_day: dict[pd.Timestamp, float] = {}
    elapsed_daylight_by_day: dict[pd.Timestamp, float] = {}
    previous_selected_ppfd_by_day: dict[pd.Timestamp, float] = {}
    previous_timestamp_by_day: dict[pd.Timestamp, pd.Timestamp] = {}
    controller_dli_values = []
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
                ceiling_reachable_today = daily_ceiling_reachable.get(day, False)
                if (
                    not pd.isna(ceiling_reachable_today)
                    and not bool(ceiling_reachable_today)
                ):
                    maximum_ppfd = math.inf
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
            values = valid_candidates.get(tilt)
            if values is None:
                continue
            tracker_theta = float(values.get("tracker_theta_deg", tilt))
            move = (
                0.0
                if last_tracker_theta is None
                else abs(tracker_theta - last_tracker_theta)
            )
            override_move_limit = (
                movement_override is not None
                and bool(movement_override.loc[timestamp])
            )
            if (
                max_move_deg is not None
                and move > max_move_deg
                and not override_move_limit
            ):
                continue
            crop_ppfd = float(values["crop_ppfd_umol_m2_s"])
            pv_loss = max_power - float(values["pv_power_w"])
            score = _light_objective(crop_ppfd, minimum_ppfd, maximum_ppfd)
            if dynamic_dli:
                normalized_pv_loss = pv_loss / max(max_power, 1.0)
                normalized_move = (
                    move / max(max_move_deg, 1.0)
                    if max_move_deg is not None
                    else 0.0
                )
                operating_cost = (
                    pv_loss_weight * normalized_pv_loss
                    + movement_weight * normalized_move
                )
                scored.append(((score, operating_cost, move, tilt), tilt))
            else:
                score += pv_loss_weight * pv_loss + movement_weight * move
                scored.append(((score, move, tilt), tilt))
        if not scored:
            chosen = last_tilt if last_tilt is not None else tilts[0]
            chosen_values = valid_candidates.get(chosen)
            if chosen_values is not None:
                last_tracker_theta = float(
                    chosen_values.get("tracker_theta_deg", chosen)
                )
        else:
            chosen = min(scored)[1]
            chosen_values = valid_candidates[chosen]
            last_tracker_theta = float(
                chosen_values.get("tracker_theta_deg", chosen)
            )
        selected.append(chosen)
        last_tilt = chosen
        if dynamic_dli:
            chosen_ppfd = float(candidates[chosen].loc[timestamp, "crop_ppfd_umol_m2_s"])
            interval_daylight = float(daylight_seconds.loc[timestamp])
            day = timestamp.normalize()
            previous_ppfd = previous_selected_ppfd_by_day.get(day)
            previous_timestamp = previous_timestamp_by_day.get(day)
            elapsed_seconds = (
                (timestamp - previous_timestamp).total_seconds()
                if previous_timestamp is not None
                else None
            )
            contribution = dli_interval_contribution(
                previous_ppfd,
                chosen_ppfd,
                elapsed_seconds,
            )
            accumulated_dli_by_day[day] = (
                accumulated_dli_by_day.get(day, 0.0)
                + (contribution if contribution is not None else 0.0)
            )
            if math.isfinite(chosen_ppfd):
                previous_selected_ppfd_by_day[day] = chosen_ppfd
            else:
                previous_selected_ppfd_by_day.pop(day, None)
            previous_timestamp_by_day[day] = timestamp
            controller_dli_values.append(accumulated_dli_by_day[day])
            elapsed_daylight_by_day[day] = (
                elapsed_daylight_by_day.get(day, 0.0) + interval_daylight
            )

    schedule = pd.DataFrame({"tilt_deg": selected}, index=index)
    if dynamic_dli:
        schedule["controller_dli_mol_m2_day"] = controller_dli_values
        days = pd.Series(index.normalize(), index=index)
        for column in daily_candidate_dli:
            schedule[column] = days.map(daily_candidate_dli[column])
    return schedule
