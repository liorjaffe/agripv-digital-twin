"""Tracker optimization: choose a tilt schedule from pvlib-evaluated candidates."""

from __future__ import annotations

import pandas as pd


def _light_objective(crop_ppfd_umol_m2_s: float, target_ppfd_umol_m2_s: float) -> float:
    """Score candidate orientations by DLI deficit and crop-light surplus.

    Below the target, smaller deficit is better. Above the target, higher crop PPFD is
    preferred, so the score becomes more negative as the candidate provides more light.
    The objective stays dimensionally consistent because it compares all candidates at the
    same timestamp and target band.
    """
    if target_ppfd_umol_m2_s <= 0.0:
        return -crop_ppfd_umol_m2_s
    if crop_ppfd_umol_m2_s < target_ppfd_umol_m2_s:
        return target_ppfd_umol_m2_s - crop_ppfd_umol_m2_s
    return -crop_ppfd_umol_m2_s / max(target_ppfd_umol_m2_s, 1.0e-9)


def optimize_tilt_schedule(
    candidates: dict[float, pd.DataFrame],
    target_ppfd: pd.Series,
    *,
    previous_tilt: float | None = None,
    max_move_deg: float | None = None,
    pv_loss_weight: float = 0.0,
    movement_weight: float = 0.0,
) -> pd.DataFrame:
    """Choose a tilt at each timestep from pvlib-evaluated candidate results.

    Each candidate frame must contain ``crop_ppfd_umol_m2_s``, ``poa_global_w_m2``
    and ``pv_power_w``. The objective is a light-deficit-first formulation with an
    optional PV-loss and movement penalty. This deliberately separates candidate physics
    from control policy, making it usable with historical or later live weather streams.
    """
    if not candidates:
        raise ValueError("candidates must contain at least one tilt")
    tilts = sorted(float(tilt) for tilt in candidates)
    index = target_ppfd.index
    selected = []
    last_tilt = previous_tilt
    for timestamp in index:
        target = float(target_ppfd.loc[timestamp])
        max_power = max(float(candidate["pv_power_w"].get(timestamp, 0.0)) for candidate in candidates.values())
        scored = []
        for tilt in tilts:
            values = candidates[tilt].loc[timestamp]
            move = 0.0 if last_tilt is None else abs(tilt - last_tilt)
            if max_move_deg is not None and move > max_move_deg:
                continue
            crop_ppfd = float(values["crop_ppfd_umol_m2_s"])
            pv_loss = max_power - float(values["pv_power_w"])
            score = _light_objective(crop_ppfd, target)
            score += pv_loss_weight * pv_loss + movement_weight * move
            scored.append((score, tilt))
        if not scored:
            chosen = last_tilt if last_tilt is not None else tilts[0]
        else:
            chosen = min(scored)[1]
        selected.append(chosen)
        last_tilt = chosen

    return pd.DataFrame({"tilt_deg": selected}, index=index)
