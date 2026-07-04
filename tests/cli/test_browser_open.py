from unittest.mock import patch
from click.testing import CliRunner
from neosentinel.cli.main import cli


def test_start_opens_browser():
    runner = CliRunner()
    with patch("webbrowser.open") as mock_open:
        result = runner.invoke(cli, ["start", "--port", "8081"])
        assert result.exit_code == 0
        mock_open.assert_called_once_with("http://localhost:8081")


def test_start_no_open_browser():
    runner = CliRunner()
    with patch("webbrowser.open") as mock_open:
        result = runner.invoke(cli, ["start", "--no-open-browser"])
        assert result.exit_code == 0
        mock_open.assert_not_called()
