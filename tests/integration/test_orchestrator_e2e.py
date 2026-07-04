from pathlib import Path

import fakeredis

from neosentinel.agent.snapshot import seed_node_telemetry
from neosentinel.contracts.decision import ActionType
from neosentinel.contracts.streams import STREAM_DECISIONS, STREAM_HEALING
from neosentinel.distributed.ray_tasks import MockRayTaskDispatcher
from neosentinel.distributed.streams import TelemetryPipeline
from neosentinel.orchestrator.cluster import ClusterSentinelOrchestrator
from neosentinel.orchestrator.restart import ROLLING_RESTART_ORDER


def _seed_cluster(client) -> None:
    seed_node_telemetry(
        client,
        node_id="node-001",
        sve2_utilization_pct=82.0,
        dram_bandwidth_pct=55.0,
        cache_miss_rate_pct=12.0,
        ttft_p99_ms=120.0,
        tokens_per_sec=45.0,
        kv_eviction_rate=0.5,
        requests_per_min=350.0,
    )
    seed_node_telemetry(
        client,
        node_id="node-002",
        sve2_utilization_pct=29.0,
        dram_bandwidth_pct=88.5,
        cache_miss_rate_pct=45.0,
        ttft_p99_ms=312.0,
        tokens_per_sec=18.4,
        kv_eviction_rate=4.2,
        requests_per_min=340.0,
    )
    seed_node_telemetry(
        client,
        node_id="node-003",
        sve2_utilization_pct=80.5,
        dram_bandwidth_pct=54.0,
        cache_miss_rate_pct=11.8,
        ttft_p99_ms=118.0,
        tokens_per_sec=46.0,
        kv_eviction_rate=0.4,
        requests_per_min=355.0,
    )


class TestOrchestratorE2E:
    def test_full_cycle_reads_redis_dispatches_ray_and_heals(self, tmp_path: Path):
        client = fakeredis.FakeRedis(decode_responses=True)
        pipeline = TelemetryPipeline(client)
        pipeline.ensure_streams()
        _seed_cluster(client)

        ray = MockRayTaskDispatcher()
        orchestrator = ClusterSentinelOrchestrator(
            pipeline=pipeline,
            ray=ray,
            audit_root=tmp_path / "audit",
            checkpoint_root=tmp_path / "checkpoints",
        )

        result = orchestrator.run_cycle()
        assert result is not None
        assert len(result.snapshot.nodes) == 3
        assert result.finding.target_node == "node-002"
        assert result.decision.action == ActionType.TRIGGER_REQUANTIZE
        assert result.quorum is not None
        assert result.quorum.quorum_met is True
        assert result.executed is True
        assert result.heal_outcome is not None
        assert result.heal_outcome.result.after.sve2_utilization_pct >= 79.0
        assert result.restart_order == ROLLING_RESTART_ORDER
        assert result.restarted_nodes == list(ROLLING_RESTART_ORDER)

        assert client.xlen(STREAM_DECISIONS) >= 1
        assert client.xlen(STREAM_HEALING) >= 1
        assert any(call[0] == "performix" for call in ray.calls)

    def test_reads_all_three_node_streams(self, tmp_path: Path):
        client = fakeredis.FakeRedis(decode_responses=True)
        pipeline = TelemetryPipeline(client)
        pipeline.ensure_streams()
        _seed_cluster(client)

        orchestrator = ClusterSentinelOrchestrator(
            pipeline=pipeline,
            ray=MockRayTaskDispatcher(),
            audit_root=tmp_path / "audit",
            checkpoint_root=tmp_path / "checkpoints",
        )
        snapshot = orchestrator.read_cluster_snapshot()
        assert snapshot is not None
        assert {node.node_id for node in snapshot.nodes} == {"node-001", "node-002", "node-003"}
