import pytest

from neosentinel.actions.adjust_vllm_config import AdjustVllmConfigAction
from neosentinel.actions.base import ActionContext
from neosentinel.contracts.decision import ActionType
from neosentinel.contracts.telemetry import BaselineMetrics


def _metrics() -> BaselineMetrics:
    return BaselineMetrics(
        ttft_p99_ms=400.0,
        tokens_per_sec=20.0,
        sve2_utilization_pct=70.0,
        dram_bandwidth_pct=90.0,
        cache_miss_rate_pct=20.0,
        kv_eviction_rate=4.5,
        requests_per_min=300.0,
    )


class TestAdjustVllmConfigAction:
    def test_improves_latency_and_kv_pressure(self):
        action = AdjustVllmConfigAction()
        result = action.execute(
            ActionContext(
                node_id="node-001",
                parameters={"max_num_seqs": 128},
                before_metrics=_metrics(),
                vllm_config={"max_num_seqs": 256},
            )
        )
        assert result.success is True
        assert result.action == ActionType.ADJUST_VLLM_CONFIG
        assert result.after.ttft_p99_ms < result.before.ttft_p99_ms
        assert result.after.kv_eviction_rate < result.before.kv_eviction_rate
        assert result.config_delta["max_num_seqs"] == 128

    def test_requires_before_metrics(self):
        with pytest.raises(ValueError, match="before_metrics"):
            AdjustVllmConfigAction().execute(ActionContext(node_id="node-001"))
