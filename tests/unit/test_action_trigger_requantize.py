from neosentinel.actions.base import ActionContext
from neosentinel.actions.trigger_requantize import TriggerRequantizeAction
from neosentinel.contracts.decision import ActionType
from neosentinel.contracts.telemetry import BaselineMetrics


def _degraded_metrics() -> BaselineMetrics:
    return BaselineMetrics(
        ttft_p99_ms=312.0,
        tokens_per_sec=18.4,
        sve2_utilization_pct=29.0,
        dram_bandwidth_pct=88.5,
        cache_miss_rate_pct=45.0,
        kv_eviction_rate=4.2,
        requests_per_min=340.0,
    )


class TestTriggerRequantizeAction:
    def test_sve2_underutilization_heal_targets(self):
        action = TriggerRequantizeAction()
        result = action.execute(
            ActionContext(
                node_id="node-002",
                parameters={"target_precision": "int4", "enable_kleidiai": True},
                before_metrics=_degraded_metrics(),
            )
        )
        assert result.success is True
        assert result.action == ActionType.TRIGGER_REQUANTIZE
        assert result.after.sve2_utilization_pct >= 79.0
        assert result.after.ttft_p99_ms <= 140.0
        assert result.after.tokens_per_sec >= 44.0
