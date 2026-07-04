from neosentinel.actions.base import ActionContext
from neosentinel.actions.send_alert import SendAlertAction
from neosentinel.contracts.decision import ActionType
from neosentinel.contracts.telemetry import BaselineMetrics


def _metrics() -> BaselineMetrics:
    return BaselineMetrics(
        ttft_p99_ms=500.0,
        tokens_per_sec=10.0,
        sve2_utilization_pct=15.0,
        dram_bandwidth_pct=95.0,
        cache_miss_rate_pct=50.0,
        kv_eviction_rate=6.0,
        requests_per_min=200.0,
    )


class TestSendAlertAction:
    def test_dispatches_alert_without_metric_change(self):
        received: list[tuple[str, str, dict]] = []

        def handler(node_id: str, severity: str, payload: dict) -> None:
            received.append((node_id, severity, payload))

        action = SendAlertAction(handler=handler)
        result = action.execute(
            ActionContext(
                node_id="node-001",
                parameters={"severity": "critical", "message": "TTFT spike"},
                before_metrics=_metrics(),
            )
        )
        assert result.success is True
        assert result.action == ActionType.SEND_ALERT
        assert result.before == result.after
        assert len(received) == 1
        assert received[0][1] == "critical"
        assert len(action.alerts) == 1
