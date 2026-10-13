"""Regression tests for assumption labels in the model-explorer page."""

from project.scenarios.generate_model_explorer import (
    SYNTHETIC_INPUTS_NOTICE,
    TEMPLATE,
)


def test_model_explorer_qualifies_unverified_channel_group_mapping():
    assert "0A-0E assumed open" in TEMPLATE
    assert "2B assumed between" in TEMPLATE
    assert "2A/2C assumed under" in TEMPLATE
    assert "channel placements are unverified" in TEMPLATE
    assert "synthetic seasonal temperature curve" in SYNTHETIC_INPUTS_NOTICE
