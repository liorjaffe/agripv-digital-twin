"""Regression tests for assumption labels in the model-explorer page."""

import pandas as pd

from project.scenarios.generate_model_explorer import (
    SYNTHETIC_INPUTS_NOTICE,
    TEMPLATE,
    cycle_summary_html,
    finite_values,
    fresh_mass_values,
    render_report_template,
    stage_values,
    transplant_indices,
)


def test_model_explorer_qualifies_unverified_channel_group_mapping():
    assert "0A-0E assumed open" in TEMPLATE
    assert "2B assumed between" in TEMPLATE
    assert "2A/2C assumed under" in TEMPLATE
    assert "channel placements are unverified" in TEMPLATE
    assert "typical-year air temperature" in SYNTHETIC_INPUTS_NOTICE
    assert "Unrecorded irradiance timestamps are assumed to have zero light" in SYNTHETIC_INPUTS_NOTICE
    assert "uncalibrated model-derived scenario estimates" in SYNTHETIC_INPUTS_NOTICE
    empty_cycles = pd.DataFrame(
        columns=["cycle_id", "cycle_model_fresh_biomass_g_m2", "harvest"]
    )
    rendered = render_report_template({}, "notice", {"open": empty_cycles})
    assert "Curves are uncalibrated modeled fresh-mass equivalents" in rendered
    assert "modeled fresh-mass equivalent (uncalibrated)" in rendered
    assert "crop biomass withheld (uncalibrated)" not in rendered
    assert "paintStageOverlay(ctx,0,dates.length-1" in rendered
    assert "paintStageOverlay(ctx,left,right" in rendered
    assert "pathOpen=false;return" in rendered
    assert "Nursery (seedling not in bed, not modeled)" in rendered
    assert (
        "Field biomass starts at final transplant from the measured 0.90 g seedling "
        "(SITE-003). Known limitation: the growth model has no maturity slowdown, "
        "so curves stay steep until the GDD harvest date (CROP-004)."
    ) in rendered


def test_model_explorer_exports_uncalibrated_values_and_marks_incomplete_cycles():
    assert finite_values(pd.Series([1.0, float("nan"), 3.0])) == [1.0, None, 3.0]
    index = pd.date_range("2026-01-01", periods=2, freq="D", tz="America/Sao_Paulo")
    cycle = pd.DataFrame(
        {
            "cycle_id": [1, 1],
            "cycle_model_fresh_biomass_g_m2": [4000.0, 5072.5],
            "harvest": [False, False],
        },
        index=index,
    )
    summary = cycle_summary_html({"open": cycle})
    assert "5072.5" in summary
    assert "594.4" in summary
    assert "not compared (cycle incomplete)" in summary
    assert "in progress at data end" in summary
    assert "GDD clock sets cycle duration" in summary

    harvested = cycle.assign(harvest=[False, True])
    assert "above user-reported range" in cycle_summary_html({"open": harvested})


def test_model_explorer_exports_nursery_gaps_and_stage_markers():
    index = pd.date_range("2026-01-01", periods=3, freq="D", tz="America/Sao_Paulo")
    cycle = pd.DataFrame(
        {
            "cycle_stage": ["nursery", "field", "field"],
            "cycle_model_fresh_biomass_g_m2": [0.0, 10.0, 15.0],
        },
        index=index,
    )

    assert fresh_mass_values(
        cycle["cycle_model_fresh_biomass_g_m2"], cycle
    ) == [None, 10.0, 15.0]
    assert stage_values(cycle) == ["nursery", "field", "field"]
    assert transplant_indices(cycle) == [1]
