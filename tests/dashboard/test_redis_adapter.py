import json

import fakeredis

from neosentinel.agent.snapshot import seed_node_telemetry
from neosentinel.contracts.streams import (
    STREAM_DECISIONS,
    STREAM_HEALING,
    STREAM_PMU,
    STREAM_VLLM,
)
from neosentinel.dashboard.redis_adapter import RedisStreamAdapter
from neosentinel.distributed.streams import TelemetryPipeline
from neosentinel.orchestrator.cluster import ClusterSentinelOrchestrator


class TestRedisStreamAdapter:
    def test_pmu_and_vllm_produce_metrics_event(self) -> None:
        adapter = RedisStreamAdapter()
        adapter.ingest(
            STREAM_PMU,
            {
                "node_id": "node-002",
                "timestamp": "2026-07-04T12:00:00+00:00",
                "sve2_utilization_pct": "29.0",
                "dram_bandwidth_pct": "88.5",
                "cache_miss_rate_pct": "45.0",
                "hotspots_json": json.dumps(
                    [
                        {
                            "symbol": "unoptimized_gemm_kernel",
                            "samples_pct": 72.5,
                            "module": "vllm_engine",
                        }
                    ]
                ),
            },
        )
        events = adapter.ingest(
            STREAM_VLLM,
            {
                "node_id": "node-002",
                "timestamp": "2026-07-04T12:00:00+00:00",
                "ttft_p99_ms": "312.0",
                "tokens_per_sec": "18.4",
                "kv_eviction_rate": "4.2",
                "requests_per_min": "340.0",
            },
        )
        assert len(events) == 1
        metrics = events[0]
        assert metrics["type"] == "metrics"
        node = next(n for n in metrics["nodes"] if n["node_id"] == "node-002")
        assert node["sve2_utilization_pct"] == 29.0
        assert node["ttft_p99_ms"] == 312.0
        assert node["status"] == "degraded"

    def test_decision_produces_agent_thought(self) -> None:
        adapter = RedisStreamAdapter()
        events = adapter.ingest(
            STREAM_DECISIONS,
            {
                "decision_id": "dec-001",
                "cluster_id": "cluster-graviton4",
                "node_id": "node-002",
                "timestamp": "2026-07-04T12:00:02+00:00",
                "action": "trigger_requantize",
                "confidence": "0.92",
                "reasoning": "SVE2 underutilized on node-002",
                "quorum_required": "true",
            },
        )
        assert events[0]["type"] == "agent_thought"
        assert events[0]["chunk"] == "SVE2 underutilized on node-002"

    def test_healing_produces_healing_and_audit(self) -> None:
        adapter = RedisStreamAdapter()
        before = {
            "ttft_p99_ms": 312.0,
            "tokens_per_sec": 18.4,
            "sve2_utilization_pct": 29.0,
            "dram_bandwidth_pct": 88.5,
            "cache_miss_rate_pct": 45.0,
            "kv_eviction_rate": 4.2,
            "requests_per_min": 340.0,
        }
        after = dict(before)
        after.update({"ttft_p99_ms": 131.0, "sve2_utilization_pct": 79.0})
        events = adapter.ingest(
            STREAM_HEALING,
            {
                "healing_id": "heal-001",
                "decision_id": "dec-001",
                "node_id": "node-002",
                "timestamp": "2026-07-04T12:00:05+00:00",
                "action": "trigger_requantize",
                "status": "success",
                "before_json": json.dumps(before),
                "after_json": json.dumps(after),
                "duration_ms": "1500",
                "checkpoint_id": "chk-node-002-test",
            },
        )
        types = {event["type"] for event in events}
        assert types == {"healing", "audit"}


class TestLiveRedisWiringE2E:
    def test_orchestrator_populates_streams_for_adapter(self, tmp_path) -> None:
        client = fakeredis.FakeRedis(decode_responses=True)
        pipeline = TelemetryPipeline(client)
        pipeline.ensure_streams()
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

        orchestrator = ClusterSentinelOrchestrator(
            pipeline=pipeline,
            audit_root=tmp_path / "audit",
            checkpoint_root=tmp_path / "checkpoints",
        )
        result = orchestrator.run_cycle()
        assert result is not None
        assert result.executed is True
        assert client.xlen(STREAM_DECISIONS) >= 1
        assert client.xlen(STREAM_HEALING) >= 1

        adapter = RedisStreamAdapter()
        for _entry_id, fields in client.xrevrange(STREAM_DECISIONS, count=1):
            events = adapter.ingest(STREAM_DECISIONS, dict(fields))
            assert any(e["type"] == "agent_thought" for e in events)
        for _entry_id, fields in client.xrevrange(STREAM_HEALING, count=1):
            events = adapter.ingest(STREAM_HEALING, dict(fields))
            assert any(e["type"] == "healing" for e in events)
