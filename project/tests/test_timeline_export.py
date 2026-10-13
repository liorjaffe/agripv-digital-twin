import pandas as pd

from project.scenarios.export_model_timeline import (
    SYNTHETIC_INPUTS_NOTICE,
    build_cycle_markers,
    build_scenario_series,
    build_timeline_metadata,
)


def test_timeline_only_exports_variables_with_explicit_scenario_labels():
    index = pd.date_range("2026-01-01", periods=1, tz="America/Sao_Paulo")
    hourly = pd.DataFrame(
        {
            "light_open_w_m2": [100.0],
            "t_folha_c": [24.0],
            "model_air_temp_c": [14.0],
            "fresh_open_g_m2": [125.0],
        },
        index=index,
    )

    series = build_scenario_series(hourly, "light_open_w_m2", "fresh_open_g_m2")
    metadata = build_timeline_metadata(hourly)

    assert set(series) == {"par_wm2", "t_folha", "t_air", "fm", "fp"}
    assert series["par_wm2"] == [45.0]
    assert series["t_air"] == [14.0]
    assert series["fm"] == [125.0]
    assert abs(series["fp"][0] - (125.0 / (96 / 11.25))) < 0.01
    assert metadata["synthetic_inputs_notice"].startswith(SYNTHETIC_INPUTS_NOTICE)
    assert "Generated from commit " in metadata["synthetic_inputs_notice"]
    assert "unverified" in metadata["canteiros"]["between"]
    assert "synthetic" in metadata["vars"]["t_folha"]["rot"]
    assert "uncalibrated" in metadata["vars"]["fm"]["rot"]
    assert "uncalibrated model-derived scenario estimates" in SYNTHETIC_INPUTS_NOTICE
    assert "harvest markers are generated" in metadata["synthetic_inputs_notice"]
    assert "not measured site air temperature" in metadata["synthetic_inputs_notice"]
    assert "not calibrated or observed harvest predictions" in metadata["synthetic_inputs_notice"]
    assert "Unrecorded irradiance timestamps are assumed to have zero light" in SYNTHETIC_INPUTS_NOTICE


def test_timeline_marks_open_final_cycle_as_in_progress_not_a_harvest():
    index = pd.date_range("2026-12-30", periods=2, freq="D", tz="America/Sao_Paulo")
    cycle = pd.DataFrame(
        {"cycle_id": [7, 7], "harvest": [False, False]},
        index=index,
    )
    cycles = {setup: cycle for setup in ("open", "between", "under")}

    markers = build_cycle_markers(cycles, pd.DataFrame(index=index))

    assert len(markers) == 1
    assert markers[0]["colheita"] == "in progress"
    assert markers[0]["maturidade_gdd"] is False
