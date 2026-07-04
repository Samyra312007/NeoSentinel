import fakeredis

from neosentinel.agent.brain import AgentBrain, MockLlamaCppBackend
from neosentinel.agent.loop import DecisionLoop
from neosentinel.agent.snapshot import seed_node_telemetry
from neosentinel.contracts.decision import ActionType
from neosentinel.contracts.streams import STREAM_DECISIONS
from neosentinel.distributed.streams import TelemetryPipeline


class TestDecisionLoop:
    def test_publishes_decision_from_redis_snapshot(self):
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

        brain = AgentBrain(MockLlamaCppBackend(simulate_cpu_ms=0.0))
        loop = DecisionLoop(pipeline, brain, interval_s=30.0)
        decision = loop.tick()

        assert decision is not None
        assert decision.action == ActionType.TRIGGER_REQUANTIZE
        assert decision.node_id == "node-002"
        assert loop.stats.decisions_published == 1

        entries = pipeline.read_decisions(count=1)
        assert len(entries) == 1
        _entry_id, fields = entries[0]
        assert fields["action"] == "trigger_requantize"
        assert fields["node_id"] == "node-002"
        assert client.xlen(STREAM_DECISIONS) == 1

    def test_skips_tick_when_no_telemetry(self):
        client = fakeredis.FakeRedis(decode_responses=True)
        pipeline = TelemetryPipeline(client)
        pipeline.ensure_streams()
        brain = AgentBrain(MockLlamaCppBackend(simulate_cpu_ms=0.0))
        loop = DecisionLoop(pipeline, brain, interval_s=30.0)

        assert loop.tick() is None
        assert loop.stats.skipped_ticks == 1
        assert client.xlen(STREAM_DECISIONS) == 0

    def test_run_for_30s_interval(self):
        client = fakeredis.FakeRedis(decode_responses=True)
        pipeline = TelemetryPipeline(client)
        pipeline.ensure_streams()
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

        clock = {"t": 0.0}
        sleeps: list[float] = []

        def monotonic() -> float:
            return clock["t"]

        def sleeper(duration: float) -> None:
            sleeps.append(duration)
            clock["t"] += duration

        brain = AgentBrain(MockLlamaCppBackend(simulate_cpu_ms=0.0))
        loop = DecisionLoop(pipeline, brain, interval_s=30.0)
        stats = loop.run_for(60.0, clock=monotonic, sleeper=sleeper)

        assert stats.ticks == 2
        assert stats.decisions_published == 2
        assert sleeps == [30.0, 30.0]
