import pandas as pd

from project.scenarios.export_model_timeline import (
    SYNTHETIC_INPUTS_NOTICE,
    build_scenario_series,
    build_timeline_metadata,
)


def test_timeline_only_exports_variables_with_explicit_scenario_labels():
    index = pd.date_range("2026-01-01", periods=1, tz="America/Sao_Paulo")
    hourly = pd.DataFrame(
        {
            "light_open_w_m2": [100.0],
            "t_folha_c": [24.0],
            "fresh_open_g_m2": [125.0],
        },
        index=index,
    )

    series = build_scenario_series(hourly, "light_open_w_m2", "fresh_open_g_m2")
    metadata = build_timeline_metadata(hourly)

    assert set(series) == {"par_wm2", "t_folha", "fm"}
    assert series["par_wm2"] == [45.0]
    assert metadata["synthetic_inputs_notice"].startswith(SYNTHETIC_INPUTS_NOTICE)
    assert "Generated from commit " in metadata["synthetic_inputs_notice"]
    assert "unverified" in metadata["canteiros"]["between"]
    assert "synthetic" in metadata["vars"]["t_folha"]["rot"]
    assert "not measured" in metadata["vars"]["fm"]["rot"]
    assert "harvest markers are generated" in metadata["synthetic_inputs_notice"]
    assert "not measured site air temperature" in metadata["synthetic_inputs_notice"]
    assert "not harvest predictions" in metadata["synthetic_inputs_notice"]
