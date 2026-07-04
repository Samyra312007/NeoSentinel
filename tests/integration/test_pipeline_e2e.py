import fakeredis

from neosentinel.contracts.streams import CONSUMER_GROUPS, STREAM_PMU, STREAM_VLLM
from neosentinel.distributed.pipeline import TelemetryIngestionPipeline
from neosentinel.distributed.streams import TelemetryPipeline
from neosentinel.telemetry.mock_performix import MockPerformix
from neosentinel.telemetry.vllm_scraper import VllmMetricsScraper

SAMPLE_METRICS = """\
vllm_ttft_p99_ms{node="node-001"} 131.0
vllm_tokens_per_sec{node="node-001"} 842.0
vllm_kv_eviction_rate{node="node-001"} 0.1
vllm_requests_per_min{node="node-001"} 400.0
"""


class TestPipelineE2E:
    def test_pmu_and_vllm_publish_to_redis(self):
        client = fakeredis.FakeRedis(decode_responses=True)
        pipeline = TelemetryPipeline(client)
        pipeline.ensure_streams()

        ingestion = TelemetryIngestionPipeline(
            pipeline,
            MockPerformix("node-001", seed=42),
            VllmMetricsScraper(
                "http://mock-vllm",
                "node-001",
                fetcher=lambda _url: SAMPLE_METRICS,
            ),
            pmu_interval_s=1.0,
            vllm_interval_s=5.0,
        )

        pmu_id, vllm_id = ingestion.tick(now=0.0)
        assert pmu_id
        assert vllm_id
        assert ingestion.stats.pmu_published == 1
        assert ingestion.stats.vllm_published == 1

        pmu_len = client.xlen(STREAM_PMU)
        vllm_len = client.xlen(STREAM_VLLM)
        assert pmu_len == 1
        assert vllm_len == 1

        pmu_group = CONSUMER_GROUPS[STREAM_PMU]
        vllm_group = CONSUMER_GROUPS[STREAM_VLLM]
        pmu_msgs = pipeline.read_group(STREAM_PMU, pmu_group, "e2e", count=1, block_ms=50)
        vllm_msgs = pipeline.read_group(STREAM_VLLM, vllm_group, "e2e", count=1, block_ms=50)
        assert pmu_msgs[0][1]["node_id"] == "node-001"
        assert float(vllm_msgs[0][1]["ttft_p99_ms"]) == 131.0

    def test_run_for_respects_pmu_1hz_and_vllm_5s_cadence(self):
        client = fakeredis.FakeRedis(decode_responses=True)
        pipeline = TelemetryPipeline(client)
        pipeline.ensure_streams()

        clock = {"t": 0.0}

        def monotonic() -> float:
            return clock["t"]

        sleeps: list[float] = []

        def sleeper(duration: float) -> None:
            sleeps.append(duration)
            clock["t"] += duration

        ingestion = TelemetryIngestionPipeline(
            pipeline,
            MockPerformix("node-001", seed=7),
            VllmMetricsScraper(
                "http://mock-vllm",
                "node-001",
                fetcher=lambda _url: SAMPLE_METRICS,
            ),
            pmu_interval_s=1.0,
            vllm_interval_s=5.0,
        )

        stats = ingestion.run_for(10.0, clock=monotonic, sleeper=sleeper)
        assert stats.pmu_published == 10
        assert stats.vllm_published == 2
        assert client.xlen(STREAM_PMU) == 10
        assert client.xlen(STREAM_VLLM) == 2
        assert sleeps == [1.0] * 10

    def test_vllm_not_republished_within_interval(self):
        client = fakeredis.FakeRedis(decode_responses=True)
        pipeline = TelemetryPipeline(client)
        pipeline.ensure_streams()

        ingestion = TelemetryIngestionPipeline(
            pipeline,
            MockPerformix("node-001", seed=9),
            VllmMetricsScraper(
                "http://mock-vllm",
                "node-001",
                fetcher=lambda _url: SAMPLE_METRICS,
            ),
            pmu_interval_s=1.0,
            vllm_interval_s=5.0,
        )

        ingestion.tick(now=0.0)
        ingestion.tick(now=1.0)
        ingestion.tick(now=2.0)
        assert ingestion.stats.pmu_published == 3
        assert ingestion.stats.vllm_published == 1
