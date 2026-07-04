"""S5.2 tests — cross-node correlation in ClusterSentinelOrchestrator.

Verifies that the orchestrator correctly detects anomalies across multiple
nodes, correlates shared anomaly types, and produces ``SentinelDecision``
objects with appropriate action types and confidence scores.
"""

from __future__ import annotations

from datetime import UTC, datetime

from neosentinel.contracts.decision import ActionType
from neosentinel.contracts.telemetry import NodeSnapshot, NodeStatus
from neosentinel.orchestrator.cluster import (
    ClusterSentinelOrchestrator,
    correlate_cross_node,
    detect_node_anomalies,
)


def _healthy_node(
    node_id: str = "node-001",
    **overrides,
) -> NodeSnapshot:
    defaults = {
        "node_id": node_id,
        "status": NodeStatus.HEALTHY,
        "timestamp": datetime.now(UTC),
        "ttft_p99_ms": 120.0,
        "tokens_per_sec": 45.0,
        "sve2_utilization_pct": 80.0,
        "dram_bandwidth_pct": 55.0,
        "cache_miss_rate_pct": 12.0,
        "kv_eviction_rate": 0.5,
        "requests_per_min": 350.0,
    }
    defaults.update(overrides)
    return NodeSnapshot(**defaults)


class TestDetectNodeAnomalies:
    def test_healthy_node_has_no_anomalies(self) -> None:
        node = _healthy_node()
        assert detect_node_anomalies(node) == []

    def test_sve2_underutilization_detected(self) -> None:
        node = _healthy_node(
            sve2_utilization_pct=25.0,
            status=NodeStatus.DEGRADED,
        )
        signals = detect_node_anomalies(node)
        assert len(signals) == 1
        assert signals[0].anomaly_type == "sve2_underutilization"
        assert signals[0].suggested_action == ActionType.ARM_PERFORMIX_ANALYZE

    def test_ttft_spike_detected(self) -> None:
        node = _healthy_node(
            ttft_p99_ms=320.0,
            status=NodeStatus.DEGRADED,
        )
        signals = detect_node_anomalies(node)
        assert len(signals) == 1
        assert signals[0].anomaly_type == "ttft_spike"
        assert signals[0].suggested_action == ActionType.ADJUST_VLLM_CONFIG

    def test_kv_eviction_flood_detected(self) -> None:
        node = _healthy_node(
            kv_eviction_rate=8.5,
            status=NodeStatus.DEGRADED,
        )
        signals = detect_node_anomalies(node)
        assert len(signals) == 1
        assert signals[0].anomaly_type == "kv_eviction_flood"
        assert signals[0].suggested_action == ActionType.TRIGGER_REQUANTIZE

    def test_multiple_anomalies_on_single_node(self) -> None:
        node = _healthy_node(
            sve2_utilization_pct=20.0,
            ttft_p99_ms=400.0,
            kv_eviction_rate=12.0,
            status=NodeStatus.UNHEALTHY,
        )
        signals = detect_node_anomalies(node)
        types = {s.anomaly_type for s in signals}
        assert types == {
            "sve2_underutilization",
            "ttft_spike",
            "kv_eviction_flood",
        }


class TestCrossNodeCorrelation:
    def test_single_node_anomaly_not_elevated(self) -> None:
        nodes = [
            _healthy_node("node-001", sve2_utilization_pct=25.0),
            _healthy_node("node-002"),
            _healthy_node("node-003"),
        ]
        signals = correlate_cross_node(nodes)
        correlated = [s for s in signals if s.anomaly_type.startswith("correlated_")]
        assert len(correlated) == 0

    def test_two_node_anomaly_elevated(self) -> None:
        nodes = [
            _healthy_node("node-001", sve2_utilization_pct=25.0),
            _healthy_node("node-002", sve2_utilization_pct=30.0),
            _healthy_node("node-003"),
        ]
        signals = correlate_cross_node(nodes)
        correlated = [s for s in signals if s.anomaly_type.startswith("correlated_")]
        assert len(correlated) == 2
        assert all(s.anomaly_type == "correlated_sve2_underutilization" for s in correlated)

    def test_all_three_nodes_correlated(self) -> None:
        nodes = [
            _healthy_node("node-001", ttft_p99_ms=350.0),
            _healthy_node("node-002", ttft_p99_ms=400.0),
            _healthy_node("node-003", ttft_p99_ms=500.0),
        ]
        signals = correlate_cross_node(nodes)
        correlated = [s for s in signals if s.anomaly_type == "correlated_ttft_spike"]
        assert len(correlated) == 3


class TestOrchestratorAnalyze:
    def test_analyze_healthy_cluster_no_decisions(self) -> None:
        orch = ClusterSentinelOrchestrator()
        nodes = [
            _healthy_node("node-001"),
            _healthy_node("node-002"),
            _healthy_node("node-003"),
        ]
        decisions = orch.analyze(nodes)
        assert decisions == []
        assert orch.summary()["total_decisions"] == 0

    def test_analyze_single_degraded_node(self) -> None:
        orch = ClusterSentinelOrchestrator()
        nodes = [
            _healthy_node("node-001"),
            _healthy_node(
                "node-002",
                sve2_utilization_pct=20.0,
                status=NodeStatus.DEGRADED,
            ),
            _healthy_node("node-003"),
        ]
        decisions = orch.analyze(nodes)
        assert len(decisions) == 1
        assert decisions[0].node_id == "node-002"
        assert decisions[0].action == ActionType.ARM_PERFORMIX_ANALYZE

    def test_decisions_accumulate(self) -> None:
        orch = ClusterSentinelOrchestrator()
        nodes_a = [
            _healthy_node("node-001", sve2_utilization_pct=15.0),
            _healthy_node("node-002"),
            _healthy_node("node-003"),
        ]
        orch.analyze(nodes_a)
        nodes_b = [
            _healthy_node("node-001"),
            _healthy_node("node-002", ttft_p99_ms=350.0),
            _healthy_node("node-003"),
        ]
        orch.analyze(nodes_b)
        assert orch.summary()["total_decisions"] == 2

    def test_confidence_decreases_with_severity(self) -> None:
        orch = ClusterSentinelOrchestrator()
        nodes = [
            _healthy_node("node-001"),
            _healthy_node("node-002", sve2_utilization_pct=5.0),
            _healthy_node("node-003"),
        ]
        decisions = orch.analyze(nodes)
        assert len(decisions) == 1
        # High severity → lower confidence
        assert decisions[0].confidence < 0.9
