"""Unit tests for the simulation scenario catalog."""

import pytest

from neosentinel.simulation.catalog import get_scenario, list_scenarios


def test_list_scenarios() -> None:
    """Verify that all 5 required scenarios are present in the catalog."""
    scenarios = list_scenarios()
    assert len(scenarios) == 5
    names = {s["name"] for s in scenarios}
    assert "sve2_underutilization" in names
    assert "kv_eviction_flood" in names
    assert "thermal_throttling" in names
    assert "memory_leak_degradation" in names
    assert "network_partition_latency" in names


def test_get_scenario_valid() -> None:
    """Verify scenario retrieval and metadata attributes."""
    scenario = get_scenario("sve2_underutilization")
    assert scenario.name == "sve2_underutilization"
    assert scenario.target_node == "node-002"
    assert scenario.expected_action == "trigger_requantize"
    assert scenario.initial_sve2_pct == 29.0
    assert scenario.recovered_sve2_pct == 79.0


def test_get_scenario_invalid() -> None:
    """Verify ValueError when retrieving an non-existent scenario."""
    with pytest.raises(ValueError, match="Unknown scenario"):
        get_scenario("non_existent_scenario")
