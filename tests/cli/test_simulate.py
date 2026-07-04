"""CLI unit tests for 'neosentinel simulate' command (D4.1)."""

import pytest
from click.testing import CliRunner

from neosentinel.cli.main import cli
from neosentinel.simulation.catalog import list_scenarios


@pytest.mark.parametrize("scenario_dict", list_scenarios())
def test_simulate_all_scenarios(scenario_dict: dict) -> None:
    """Verify that 'neosentinel simulate' runs successfully for all 5 core scenarios."""
    runner = CliRunner()
    scenario_name = scenario_dict["name"]
    result = runner.invoke(cli, ["simulate", "--scenario", scenario_name, "--speed", "10.0"])
    
    assert result.exit_code == 0, f"Simulation failed for {scenario_name}: {result.output}"
    assert "Starting simulation scenario" in result.output
    assert "[AGENT THOUGHT]" in result.output
    assert "[HEALING ACTION]" in result.output
    assert "[GITOPS AUDIT]" in result.output
    assert "[SUCCESS] Simulation finished" in result.output
