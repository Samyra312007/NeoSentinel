from click.testing import CliRunner

from neosentinel.cli.main import cli


def test_cli_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "init" in result.output
    assert "cluster-init" in result.output
    assert "start" in result.output
    assert "doctor" in result.output


def test_init_command(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(cli, ["init"])
        assert result.exit_code == 0
        assert "[SUCCESS] Initialized NeoSentinel config" in result.output


def test_cluster_init_command():
    runner = CliRunner()
    result = runner.invoke(cli, ["cluster-init", "--nodes", "5"])
    assert result.exit_code == 0
    assert "5 cluster nodes" in result.output


def test_doctor_command():
    runner = CliRunner()
    result = runner.invoke(cli, ["doctor", "--mock"])
    assert result.exit_code == 0
    assert "[OK]" in result.output
