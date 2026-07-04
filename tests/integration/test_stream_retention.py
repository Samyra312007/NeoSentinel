import time

from neosentinel.contracts.streams import ALL_STREAMS, CONSUMER_GROUPS, STREAM_PMU
from neosentinel.distributed.streams import TelemetryPipeline
from tests.conftest import requires_docker


class TestStreamRetentionFakeredis:
    def test_streams_and_consumer_groups_created(self, telemetry_pipeline):
        for stream in ALL_STREAMS:
            groups = telemetry_pipeline._client.xinfo_groups(stream)
            names = {group["name"] for group in groups}
            assert CONSUMER_GROUPS[stream] in names

    def test_retention_trims_old_entries(self, fake_redis):
        pipeline = TelemetryPipeline(fake_redis, retention_ms=1_000)
        pipeline.ensure_streams()
        old_id = fake_redis.xadd(
            STREAM_PMU,
            {
                "node_id": "node-001",
                "timestamp": "2026-01-01T00:00:00+00:00",
                "sve2_utilization_pct": "10.0",
                "dram_bandwidth_pct": "10.0",
                "cache_miss_rate_pct": "1.0",
                "hotspots_json": "[]",
            },
            id="1000-0",
        )
        assert old_id == "1000-0"
        time.sleep(1.1)
        pipeline.publish_fields(
            STREAM_PMU,
            {
                "node_id": "node-001",
                "timestamp": "2026-07-04T10:00:00+00:00",
                "sve2_utilization_pct": "79.0",
                "dram_bandwidth_pct": "45.0",
                "cache_miss_rate_pct": "3.2",
                "hotspots_json": "[]",
            },
        )
        entries = fake_redis.xrange(STREAM_PMU, "-", "+")
        ids = [entry_id for entry_id, _fields in entries]
        assert "1000-0" not in ids
        assert len(ids) >= 1


@requires_docker
class TestStreamRetentionCluster:
    def test_cluster_stream_retention(self, compose_stack):
        from redis.cluster import RedisCluster

        client = RedisCluster(host="127.0.0.1", port=6379, decode_responses=True)
        pipeline = TelemetryPipeline(client, retention_ms=2_000)
        pipeline.ensure_streams()
        client.xadd(
            STREAM_PMU,
            {
                "node_id": "node-001",
                "timestamp": "2026-01-01T00:00:00+00:00",
                "sve2_utilization_pct": "10.0",
                "dram_bandwidth_pct": "10.0",
                "cache_miss_rate_pct": "1.0",
                "hotspots_json": "[]",
            },
            id="2000-0",
        )
        time.sleep(2.1)
        pipeline.publish_fields(
            STREAM_PMU,
            {
                "node_id": "node-001",
                "timestamp": "2026-07-04T10:00:00+00:00",
                "sve2_utilization_pct": "79.0",
                "dram_bandwidth_pct": "45.0",
                "cache_miss_rate_pct": "3.2",
                "hotspots_json": "[]",
            },
        )
        entries = client.xrange(STREAM_PMU, "-", "+")
        ids = [entry_id for entry_id, _fields in entries]
        assert "2000-0" not in ids
