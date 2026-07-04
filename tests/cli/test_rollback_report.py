"""CLI unit tests for rollback and report commands (D5.4)."""

import os

from click.testing import CliRunner

from neosentinel.audit.checkpoints import CheckpointStore
from neosentinel.cli.main import cli
from neosentinel.contracts.decision import ActionType
from neosentinel.contracts.telemetry import BaselineMetrics


def test_rollback_command(tmp_path) -> None:
    store = CheckpointStore(tmp_path / "checkpoints")
    checkpoint = store.create(
        decision_id="dec-rollback-test",
        node_id="node-001",
        action=ActionType.NOOP,
        metrics=BaselineMetrics(
            ttft_p99_ms=131.0,
            tokens_per_sec=842.0,
            sve2_utilization_pct=79.0,
            dram_bandwidth_pct=45.0,
            cache_miss_rate_pct=3.0,
            kv_eviction_rate=0.1,
            requests_per_min=400.0,
        ),
        vllm_config={},
        parameters={},
    )
    runner = CliRunner()
    args = [
        "rollback",
        "--node",
        "node-001",
        "--checkpoint",
        checkpoint.checkpoint_id,
        "--store",
        str(tmp_path / "checkpoints"),
    ]
    result = runner.invoke(cli, args)
    assert result.exit_code == 0
    assert checkpoint.checkpoint_id in result.output


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
