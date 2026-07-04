from datetime import UTC, datetime

from neosentinel.agent.brain import (
    CPU_BUDGET_PCT,
    MODEL_NAME,
    MODEL_QUANT,
    AgentBrain,
    MockLlamaCppBackend,
)
from neosentinel.agent.decision_tree import DecisionCandidate
from neosentinel.contracts.decision import ActionType
from neosentinel.contracts.telemetry import NodeSnapshot, NodeStatus, TelemetrySnapshot


def _snapshot(node_id: str = "node-002", **metrics: float) -> TelemetrySnapshot:
    node = NodeSnapshot(
        node_id=node_id,
        status=NodeStatus.DEGRADED,
        timestamp=datetime.now(UTC),
        ttft_p99_ms=metrics.get("ttft_p99_ms", 312.0),
        tokens_per_sec=metrics.get("tokens_per_sec", 18.4),
        sve2_utilization_pct=metrics.get("sve2_utilization_pct", 29.0),
        dram_bandwidth_pct=metrics.get("dram_bandwidth_pct", 88.5),
        cache_miss_rate_pct=metrics.get("cache_miss_rate_pct", 45.0),
        kv_eviction_rate=metrics.get("kv_eviction_rate", 4.2),
        requests_per_min=metrics.get("requests_per_min", 340.0),
        hotspots=[],
    )
    return TelemetrySnapshot(
        cluster_id="cluster-graviton4",
        timestamp=datetime.now(UTC),
        nodes=[node],
    )


class TestAgentBrainMockLlm:
    def test_mock_backend_produces_valid_decision(self):
        backend = MockLlamaCppBackend(simulate_cpu_ms=0.0)
        brain = AgentBrain(backend)
        decision = brain.decide(_snapshot())
        assert decision.action == ActionType.TRIGGER_REQUANTIZE
        assert decision.node_id == "node-002"
        assert decision.confidence >= 0.9
        assert decision.snapshot_hash
        assert len(backend.calls) == 1

    def test_model_metadata_documented(self):
        assert "Llama-3.2-3B" in MODEL_NAME
        assert MODEL_QUANT == "INT4"
        assert CPU_BUDGET_PCT == 5.0

    def test_cpu_budget_stays_under_five_percent(self):
        backend = MockLlamaCppBackend(simulate_cpu_ms=1.0)
        brain = AgentBrain(backend)
        for _ in range(10):
            brain.decide(_snapshot())
        assert brain.avg_cpu_pct < CPU_BUDGET_PCT

    def test_grammar_rejection_falls_back_to_tree(self):
        def bad_responder(_prompt: str, candidate: DecisionCandidate) -> dict:
            return {
                "decision_id": "bad",
                "cluster_id": "cluster-graviton4",
                "node_id": candidate.node_id,
                "timestamp": datetime.now(UTC).isoformat(),
                "action": "restart_worker",
                "confidence": 0.5,
                "reasoning": "invalid action",
            }

        backend = MockLlamaCppBackend(responder=bad_responder, simulate_cpu_ms=0.0)
        brain = AgentBrain(backend)
        decision = brain.decide(_snapshot())
        assert decision.action == ActionType.TRIGGER_REQUANTIZE
        assert brain.stats.grammar_rejections == 1

    def test_healthy_cluster_returns_noop(self):
        backend = MockLlamaCppBackend(simulate_cpu_ms=0.0)
        brain = AgentBrain(backend)
        snapshot = _snapshot(
            sve2_utilization_pct=82.0,
            ttft_p99_ms=120.0,
            dram_bandwidth_pct=55.0,
            cache_miss_rate_pct=12.0,
            kv_eviction_rate=0.5,
        )
        decision = brain.decide(snapshot)
        assert decision.action == ActionType.NOOP
