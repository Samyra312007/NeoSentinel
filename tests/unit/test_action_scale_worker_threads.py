from neosentinel.actions.base import ActionContext
from neosentinel.actions.scale_worker_threads import ScaleWorkerThreadsAction
from neosentinel.contracts.decision import ActionType
from neosentinel.contracts.telemetry import BaselineMetrics


def _metrics() -> BaselineMetrics:
    return BaselineMetrics(
        ttft_p99_ms=200.0,
        tokens_per_sec=30.0,
        sve2_utilization_pct=75.0,
        dram_bandwidth_pct=60.0,
        cache_miss_rate_pct=10.0,
        kv_eviction_rate=4.0,
        requests_per_min=320.0,
    )


class TestScaleWorkerThreadsAction:
    def test_scales_threads_and_throughput(self):
        action = ScaleWorkerThreadsAction()
        result = action.execute(
            ActionContext(
                node_id="node-003",
                parameters={"worker_threads_delta": 2},
                before_metrics=_metrics(),
                vllm_config={"worker_threads": 4},
            )
        )
        assert result.success is True
        assert result.action == ActionType.SCALE_WORKER_THREADS
        assert result.after.tokens_per_sec > result.before.tokens_per_sec
        assert result.after.kv_eviction_rate < result.before.kv_eviction_rate
        assert result.config_delta["worker_threads"] == 6
