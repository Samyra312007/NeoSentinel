"""CLI unit tests for rollback and report commands (D5.4)."""

import os

from click.testing import CliRunner

from neosentinel.cli.main import cli


def test_rollback_command() -> None:
    """Verify node rollback to specified checkpoint."""
    runner = CliRunner()
    args = ["rollback", "--node", "node-001", "--checkpoint", "chk-graviton4-991"]
    result = runner.invoke(cli, args)
    assert result.exit_code == 0
    assert "restored to 'chk-graviton4-991'" in result.output


def test_report_command(tmp_path) -> None:
    """Verify HTML cluster report generation."""
    runner = CliRunner()
    output_file = tmp_path / "test_report.html"
    result = runner.invoke(cli, ["report", "--output", str(output_file)])
    assert result.exit_code == 0
    assert "[SUCCESS] Generated cluster report" in result.output
    assert os.path.exists(output_file)
    content = output_file.read_text(encoding="utf-8")
    assert "NeoSentinel Cluster Health" in content
    assert "Graviton4 Control Plane Nominal" in content
