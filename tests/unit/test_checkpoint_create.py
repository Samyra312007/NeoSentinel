from pathlib import Path

import pytest

from neosentinel.audit.checkpoints import CheckpointStore
from neosentinel.contracts.decision import ActionType
from neosentinel.contracts.telemetry import BaselineMetrics


def _metrics() -> BaselineMetrics:
    return BaselineMetrics(
        ttft_p99_ms=312.0,
        tokens_per_sec=18.4,
        sve2_utilization_pct=29.0,
        dram_bandwidth_pct=88.5,
        cache_miss_rate_pct=45.0,
        kv_eviction_rate=4.2,
        requests_per_min=340.0,
    )


@pytest.fixture
def checkpoint_store(tmp_path: Path) -> CheckpointStore:
    return CheckpointStore(tmp_path / "checkpoints")


class TestCheckpointCreate:
    def test_create_persists_snapshot(self, checkpoint_store: CheckpointStore):
        checkpoint = checkpoint_store.create(
            decision_id="dec-001",
            node_id="node-002",
            action=ActionType.TRIGGER_REQUANTIZE,
            metrics=_metrics(),
            vllm_config={"max_num_seqs": 256},
            parameters={"target_precision": "int4"},
        )
        assert checkpoint.checkpoint_id.startswith("chk-node-002-")
        assert checkpoint.metrics.sve2_utilization_pct == 29.0

        loaded = checkpoint_store.get(checkpoint.checkpoint_id)
        assert loaded.decision_id == "dec-001"
        assert loaded.vllm_config["max_num_seqs"] == 256

    def test_restore_returns_same_metrics(self, checkpoint_store: CheckpointStore):
        checkpoint = checkpoint_store.create(
            decision_id="dec-002",
            node_id="node-001",
            action=ActionType.ADJUST_VLLM_CONFIG,
            metrics=_metrics(),
            vllm_config={},
            parameters={},
        )
        restored = checkpoint_store.restore(checkpoint.checkpoint_id)
        assert restored.metrics == checkpoint.metrics

    def test_missing_checkpoint_raises(self, checkpoint_store: CheckpointStore):
        with pytest.raises(KeyError):
            checkpoint_store.get("chk-missing")
