"""CLI unit tests for 'neosentinel inject' and 'replay' commands (D4.2, D4.3)."""

from click.testing import CliRunner

from neosentinel.cli.main import cli


def test_inject_command_success() -> None:
    """Verify synthetic anomaly injection on target node."""
    runner = CliRunner()
    result = runner.invoke(cli, ["inject", "--node", "node-002", "--anomaly", "kv_eviction_flood"])
    assert result.exit_code == 0
    assert "[INJECTED]" in result.output
    assert "node-002" in result.output


def test_inject_command_missing_node() -> None:
    """Verify error when node parameter is omitted."""
    runner = CliRunner()
    result = runner.invoke(cli, ["inject"])
    assert result.exit_code != 0
    assert "Missing option" in result.output or "required" in result.output.lower()


def test_replay_command_success() -> None:
    """Verify historical stream replay at scaled speed."""
    runner = CliRunner()
    result = runner.invoke(cli, ["replay", "--stream", "cluster:telemetry", "--speed", "10.0"])
    assert result.exit_code == 0
    assert "Replaying stream 'cluster:telemetry'" in result.output
    assert "[SUCCESS] Replayed 3 events" in result.output
