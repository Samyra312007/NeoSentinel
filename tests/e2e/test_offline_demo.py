"""E2E test for offline demo simulation mode (D4.5)."""

from click.testing import CliRunner

from neosentinel.cli.main import cli


def test_offline_demo_e2e() -> None:
    """Verify full offline demo simulation run with zero cloud dependency."""
    runner = CliRunner()
    result = runner.invoke(
        cli, ["simulate", "--scenario", "sve2_underutilization", "--speed", "20.0"]
    )
    assert result.exit_code == 0
    assert "[SUCCESS] Simulation finished" in result.output
    assert "trigger_requantize executed on node-002" in result.output
