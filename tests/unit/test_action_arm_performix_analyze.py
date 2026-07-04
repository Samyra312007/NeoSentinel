import pytest

from neosentinel.actions.arm_performix_analyze import ArmPerformixAnalyzeAction
from neosentinel.actions.base import ActionContext
from neosentinel.contracts.decision import ActionType
from neosentinel.contracts.telemetry import BaselineMetrics


def _metrics(**overrides: float) -> BaselineMetrics:
    base = {
        "ttft_p99_ms": 312.0,
        "tokens_per_sec": 18.4,
        "sve2_utilization_pct": 29.0,
        "dram_bandwidth_pct": 88.5,
        "cache_miss_rate_pct": 45.0,
        "kv_eviction_rate": 4.2,
        "requests_per_min": 340.0,
    }
    base.update(overrides)
    return BaselineMetrics(**base)


class TestArmPerformixAnalyzeAction:
    def test_code_hotspots_recipe(self):
        action = ArmPerformixAnalyzeAction()
        result = action.execute(
            ActionContext(
                node_id="node-002",
                parameters={"recipe": "code_hotspots", "sample_ms": 5000},
                before_metrics=_metrics(),
            )
        )
        assert result.success is True
        assert result.action == ActionType.ARM_PERFORMIX_ANALYZE
        assert "performix_report" in result.config_delta
        assert result.after.sve2_utilization_pct > result.before.sve2_utilization_pct

    def test_memory_bandwidth_recipe(self):
        action = ArmPerformixAnalyzeAction()
        result = action.execute(
            ActionContext(
                node_id="node-002",
                parameters={"recipe": "memory_bandwidth"},
                before_metrics=_metrics(),
            )
        )
        assert result.success is True
        assert result.config_delta["performix_report"]["recipe"] == "memory_bandwidth"

    def test_requires_before_metrics(self):
        with pytest.raises(ValueError, match="before_metrics"):
            ArmPerformixAnalyzeAction().execute(ActionContext(node_id="node-001"))
