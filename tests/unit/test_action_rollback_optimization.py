from neosentinel.actions.base import ActionContext
from neosentinel.actions.rollback_optimization import RollbackOptimizationAction
from neosentinel.contracts.decision import ActionType
from neosentinel.contracts.telemetry import BaselineMetrics


def _worsened() -> BaselineMetrics:
    return BaselineMetrics(
        ttft_p99_ms=450.0,
        tokens_per_sec=12.0,
        sve2_utilization_pct=20.0,
        dram_bandwidth_pct=90.0,
        cache_miss_rate_pct=40.0,
        kv_eviction_rate=5.0,
        requests_per_min=250.0,
    )


def _restored() -> BaselineMetrics:
    return BaselineMetrics(
        ttft_p99_ms=131.0,
        tokens_per_sec=44.8,
        sve2_utilization_pct=79.0,
        dram_bandwidth_pct=56.0,
        cache_miss_rate_pct=14.0,
        kv_eviction_rate=0.6,
        requests_per_min=340.0,
    )


class TestRollbackOptimizationAction:
    def test_restores_checkpoint_metrics(self):
        action = RollbackOptimizationAction()
        result = action.execute(
            ActionContext(
                node_id="node-002",
                before_metrics=_worsened(),
                parameters={
                    "restored_metrics": _restored().model_dump(),
                    "restored_config": {"max_num_seqs": 256},
                },
            )
        )
        assert result.success is True
        assert result.action == ActionType.ROLLBACK_OPTIMIZATION
        assert result.after.sve2_utilization_pct == 79.0
        assert result.after.ttft_p99_ms == 131.0

    def test_fails_without_restored_metrics(self):
        action = RollbackOptimizationAction()
        result = action.execute(
            ActionContext(node_id="node-002", before_metrics=_worsened())
        )
        assert result.success is False
