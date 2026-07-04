from datetime import UTC, datetime

import pytest

from neosentinel.agent.decision_tree import (
    DRAM_HIGH_THRESHOLD,
    KV_EVICTION_HIGH_THRESHOLD,
    SVE2_LOW_THRESHOLD,
    TTFT_HIGH_THRESHOLD,
    DecisionCandidate,
    evaluate_node,
    evaluate_snapshot,
    select_worst_node,
)
from neosentinel.contracts.decision import ActionType
from neosentinel.contracts.telemetry import NodeSnapshot, NodeStatus, TelemetrySnapshot


def _node(
    node_id: str,
    *,
    sve2: float = 79.0,
    ttft: float = 131.0,
    dram: float = 45.0,
    cache_miss: float = 3.0,
    kv_eviction: float = 0.1,
) -> NodeSnapshot:
    node = NodeSnapshot(
        node_id=node_id,
        status=NodeStatus.HEALTHY,
        timestamp=datetime.now(UTC),
        ttft_p99_ms=ttft,
        tokens_per_sec=842.0,
        sve2_utilization_pct=sve2,
        dram_bandwidth_pct=dram,
        cache_miss_rate_pct=cache_miss,
        kv_eviction_rate=kv_eviction,
        requests_per_min=400.0,
        hotspots=[],
    )
    return node


def _snapshot(*nodes: NodeSnapshot) -> TelemetrySnapshot:
    return TelemetrySnapshot(
        cluster_id="cluster-graviton4",
        timestamp=datetime.now(UTC),
        nodes=list(nodes),
    )


class TestDecisionTree:
    @pytest.mark.parametrize(
        ("metrics", "expected_action"),
        [
            (
                {"sve2": 29.0, "ttft": 312.0, "dram": 88.5, "kv_eviction": 4.2},
                ActionType.TRIGGER_REQUANTIZE,
            ),
            (
                {"sve2": 79.0, "ttft": 131.0, "dram": 45.0, "kv_eviction": 0.1},
                ActionType.NOOP,
            ),
            (
                {"sve2": 79.0, "ttft": 131.0, "dram": 45.0, "kv_eviction": 4.5},
                ActionType.SCALE_WORKER_THREADS,
            ),
            (
                {"sve2": 79.0, "ttft": 131.0, "dram": 90.0, "kv_eviction": 4.5},
                ActionType.ADJUST_VLLM_CONFIG,
            ),
            (
                {"sve2": 35.0, "ttft": 131.0, "dram": 45.0, "kv_eviction": 0.1},
                ActionType.ARM_PERFORMIX_ANALYZE,
            ),
            (
                {"sve2": 79.0, "ttft": 400.0, "dram": 45.0, "kv_eviction": 0.1},
                ActionType.ADJUST_VLLM_CONFIG,
            ),
            (
                {"sve2": 79.0, "ttft": 131.0, "dram": 90.0, "kv_eviction": 0.1},
                ActionType.ADJUST_VLLM_CONFIG,
            ),
            (
                {"sve2": 79.0, "ttft": 131.0, "dram": 45.0, "cache_miss": 55.0},
                ActionType.ARM_PERFORMIX_ANALYZE,
            ),
        ],
    )
    def test_branching_scenarios(self, metrics: dict[str, float], expected_action: ActionType):
        candidate = evaluate_node(
            _node(
                "node-002",
                sve2=metrics.get("sve2", 79.0),
                ttft=metrics.get("ttft", 131.0),
                dram=metrics.get("dram", 45.0),
                cache_miss=metrics.get("cache_miss", 3.0),
                kv_eviction=metrics.get("kv_eviction", 0.1),
            )
        )
        assert candidate.action == expected_action

    def test_sve2_underutilization_fixture_matches_expected_action(self):
        candidate = evaluate_node(
            _node("node-002", sve2=29.0, ttft=312.0, dram=88.5, kv_eviction=4.2, cache_miss=45.0)
        )
        assert candidate.action == ActionType.TRIGGER_REQUANTIZE
        assert candidate.quorum_required is True

    def test_select_worst_node_picks_degraded_node(self):
        healthy = _node("node-001")
        degraded = _node("node-002", sve2=29.0, ttft=312.0, dram=88.5, kv_eviction=4.2)
        worst = select_worst_node(_snapshot(healthy, degraded))
        assert worst.node_id == "node-002"

    def test_evaluate_snapshot_uses_worst_node(self):
        result = evaluate_snapshot(
            _snapshot(
                _node("node-001"),
                _node("node-002", sve2=29.0, ttft=312.0, dram=88.5, kv_eviction=4.2),
                _node("node-003"),
            )
        )
        assert isinstance(result, DecisionCandidate)
        assert result.node_id == "node-002"
        assert result.action == ActionType.TRIGGER_REQUANTIZE

    def test_threshold_constants(self):
        assert SVE2_LOW_THRESHOLD == 50.0
        assert TTFT_HIGH_THRESHOLD == 250.0
        assert DRAM_HIGH_THRESHOLD == 85.0
        assert KV_EVICTION_HIGH_THRESHOLD == 3.0
