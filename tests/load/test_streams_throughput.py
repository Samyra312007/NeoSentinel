import pytest

from neosentinel.distributed.benchmark import run_stream_load_benchmark
from tests.conftest import requires_docker

TARGET_EVENTS_PER_SEC = 3000

pytestmark = pytest.mark.load


class TestStreamsThroughput:
    def test_fakeredis_meets_3000_events_per_sec(self, telemetry_pipeline):
        result = run_stream_load_benchmark(
            telemetry_pipeline,
            target_events=3000,
            use_retention_trim=False,
        )
        assert result.events_published == 3000
        assert result.met_target, (
            f"Published {result.events_per_sec:.0f} evt/s, target {TARGET_EVENTS_PER_SEC}"
        )

    def test_scaled_batch_throughput(self, telemetry_pipeline):
        result = run_stream_load_benchmark(
            telemetry_pipeline,
            target_events=6000,
            use_retention_trim=False,
        )
        assert result.events_published == 6000
        assert result.events_per_sec >= TARGET_EVENTS_PER_SEC

    @requires_docker
    def test_docker_redis_cluster_throughput(self, compose_stack):
        from redis.cluster import RedisCluster

        from neosentinel.distributed.streams import TelemetryPipeline

        client = RedisCluster(host="127.0.0.1", port=6379, decode_responses=True)
        pipeline = TelemetryPipeline(client)
        result = run_stream_load_benchmark(
            pipeline,
            target_events=3000,
            workers=8,
        )
        assert result.events_published == 3000
        assert result.met_target
