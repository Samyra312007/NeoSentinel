from datetime import UTC, datetime

from neosentinel.contracts.decision import ActionType
from neosentinel.contracts.telemetry import NodeSnapshot, NodeStatus, TelemetrySnapshot
from neosentinel.orchestrator.correlation import (
    CORRELATION_HEALTHY,
    CORRELATION_SINGLE_NODE,
    CORRELATION_SVE2_UNDERUTILIZATION,
    correlate_snapshot,
    primary_finding,
)


def _node(
    node_id: str,
    *,
    sve2: float = 79.0,
    ttft: float = 131.0,
    dram: float = 45.0,
    kv: float = 0.5,
    status: NodeStatus = NodeStatus.HEALTHY,
) -> NodeSnapshot:
    return NodeSnapshot(
        node_id=node_id,
        status=status,
        timestamp=datetime.now(UTC),
        ttft_p99_ms=ttft,
        tokens_per_sec=42.0,
        sve2_utilization_pct=sve2,
        dram_bandwidth_pct=dram,
        cache_miss_rate_pct=3.0,
        kv_eviction_rate=kv,
        requests_per_min=350.0,
        hotspots=[],
    )


def _snapshot(*nodes: NodeSnapshot) -> TelemetrySnapshot:
    return TelemetrySnapshot(
        cluster_id="cluster-graviton4",
        timestamp=datetime.now(UTC),
        nodes=list(nodes),
    )


class TestCrossNodeCorrelation:
    def test_single_node_degradation(self):
        degraded = _node(
            "node-002",
            sve2=29.0,
            ttft=312.0,
            dram=88.5,
            kv=4.2,
            status=NodeStatus.DEGRADED,
        )
        finding = primary_finding(_snapshot(_node("node-001"), degraded, _node("node-003")))
        assert finding.pattern == CORRELATION_SINGLE_NODE
        assert finding.affected_nodes == ("node-002",)
        assert finding.recommended_action == ActionType.TRIGGER_REQUANTIZE
        assert finding.cluster_wide is False

    def test_cluster_wide_sve2_underutilization(self):
        findings = correlate_snapshot(
            _snapshot(
                _node("node-001", sve2=35.0, ttft=280.0, status=NodeStatus.DEGRADED),
                _node("node-002", sve2=29.0, ttft=312.0, status=NodeStatus.DEGRADED),
                _node("node-003"),
            )
        )
        assert findings[0].pattern == CORRELATION_SVE2_UNDERUTILIZATION
        assert len(findings[0].affected_nodes) >= 2
        assert findings[0].cluster_wide is True

    def test_healthy_cluster(self):
        finding = primary_finding(
            _snapshot(_node("node-001"), _node("node-002"), _node("node-003"))
        )
        assert finding.pattern == CORRELATION_HEALTHY
        assert finding.recommended_action == ActionType.NOOP

    def test_kv_eviction_flood_correlation(self):
        findings = correlate_snapshot(
            _snapshot(
                _node("node-001", kv=4.5, dram=90.0, status=NodeStatus.DEGRADED),
                _node("node-002", kv=5.0, dram=92.0, status=NodeStatus.DEGRADED),
                _node("node-003", kv=4.2, dram=88.0, status=NodeStatus.DEGRADED),
            )
        )
        patterns = {finding.pattern for finding in findings}
        assert "kv_eviction_flood" in patterns
