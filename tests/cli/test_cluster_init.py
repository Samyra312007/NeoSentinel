from click.testing import CliRunner

from neosentinel.cli.main import cli
from neosentinel.cli.provision import MockSshRunner, provision_cluster


def test_provision_cluster_mock_ssh() -> None:
    result = provision_cluster(3, runner=MockSshRunner(), sleeper=lambda _s: None)
    assert result.nodes == 3
    assert result.steps_completed == 9
    assert len(result.hosts) == 3


def test_cluster_init_command_mock_ssh() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["cluster-init", "--nodes", "3", "--mock-ssh"])
    assert result.exit_code == 0
    assert "Bootstrapping NeoSentinel on 3 cluster nodes" in result.output
    assert "[SUCCESS] Cluster bootstrap complete via mock SSH." in result.output


def test_cluster_init_rejects_zero_nodes() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["cluster-init", "--nodes", "0"])
    assert result.exit_code != 0
