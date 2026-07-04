from click.testing import CliRunner

from neosentinel.cli.diagnostics import run_doctor
from neosentinel.cli.main import cli


def test_doctor_mock_mode_passes() -> None:
    checks = run_doctor(mock=True)
    assert len(checks) == 7
    assert all(check.passed for check in checks)


def test_doctor_cli_mock() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["doctor", "--mock"])
    assert result.exit_code == 0
    assert "[SUCCESS] All 7 cluster diagnostic checks operational." in result.output


def test_doctor_cli_live_may_warn_without_services() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["doctor", "--live"])
    assert result.exit_code in {0, 1}
    assert "Running NeoSentinel diagnostics" in result.output
