from click.testing import CliRunner

from neosentinel.cli.main import cli


def test_replay_fixture_scenario() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["replay", "--stream", "sve2_underutilization", "--speed", "50.0"])
    assert result.exit_code == 0
    assert "Replaying stream 'sve2_underutilization'" in result.output
    assert "[SUCCESS] Replayed 5 events" in result.output


def test_replay_all_catalog_scenarios() -> None:
    runner = CliRunner()
    for scenario in (
        "sve2_underutilization",
        "kv_eviction_flood",
        "thermal_throttling",
        "memory_leak_degradation",
        "network_partition_latency",
    ):
        result = runner.invoke(cli, ["replay", "--stream", scenario, "--speed", "100.0"])
        assert result.exit_code == 0, result.output
        assert "[SUCCESS] Replayed 5 events" in result.output
