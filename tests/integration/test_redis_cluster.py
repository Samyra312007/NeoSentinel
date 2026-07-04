import subprocess
import time

from redis.cluster import RedisCluster

from neosentinel.contracts.streams import STREAM_PMU
from neosentinel.distributed.streams import TelemetryPipeline
from tests.conftest import requires_docker


def _cluster_info() -> str:
    result = subprocess.run(
        ["docker", "exec", "neosentinel-redis-node-1", "redis-cli", "cluster", "info"],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    return result.stdout


def _cluster_nodes() -> str:
    result = subprocess.run(
        ["docker", "exec", "neosentinel-redis-node-1", "redis-cli", "cluster", "nodes"],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    return result.stdout


def _parse_cluster_nodes(text: str) -> list[dict[str, str]]:
    nodes: list[dict[str, str]] = []
    for line in text.splitlines():
        if not line.strip():
            continue
        parts = line.split()
        nodes.append(
            {
                "id": parts[0],
                "endpoint": parts[1],
                "flags": parts[2],
                "master_id": parts[3] if len(parts) > 3 else "-",
            }
        )
    return nodes


@requires_docker
class TestRedisCluster:
    def test_cluster_state_ok(self, compose_stack):
        info = _cluster_info()
        assert "cluster_state:ok" in info

    def test_slot_coverage(self, compose_stack):
        info = _cluster_info()
        assert "cluster_slots_assigned:16384" in info
        assert "cluster_slots_ok:16384" in info

    def test_three_shards_with_replicas(self, compose_stack):
        nodes = _parse_cluster_nodes(_cluster_nodes())
        masters = [node for node in nodes if "master" in node["flags"]]
        replicas = [node for node in nodes if "slave" in node["flags"]]
        assert len(masters) == 3
        assert len(replicas) == 3
        for master in masters:
            master_replicas = [
                node for node in replicas if node["master_id"] == master["id"]
            ]
            assert len(master_replicas) == 1

    def test_stream_write_across_cluster(self, compose_stack):
        client = RedisCluster(host="127.0.0.1", port=6379, decode_responses=True)
        pipeline = TelemetryPipeline(client)
        pipeline.ensure_streams()
        message_id = pipeline.publish_fields(
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
        assert message_id
        length = client.xlen(STREAM_PMU)
        assert length >= 1

    def test_failover_replica_promoted(self, compose_stack):
        nodes_before = _parse_cluster_nodes(_cluster_nodes())
        target_master = next(node for node in nodes_before if "myself,master" in node["flags"])
        replica = next(
            node for node in nodes_before if node["master_id"] == target_master["id"]
        )

        container = "neosentinel-redis-node-1"
        subprocess.run(
            ["docker", "stop", container],
            capture_output=True,
            timeout=30,
            check=False,
        )
        try:
            promoted = False
            for _ in range(45):
                client = RedisCluster(
                    host="127.0.0.1",
                    port=6380,
                    decode_responses=True,
                    socket_connect_timeout=2,
                )
                pipeline = TelemetryPipeline(client)
                message_id = pipeline.publish_fields(
                    STREAM_PMU,
                    {
                        "node_id": "node-002",
                        "timestamp": "2026-07-04T10:00:00+00:00",
                        "sve2_utilization_pct": "55.0",
                        "dram_bandwidth_pct": "35.0",
                        "cache_miss_rate_pct": "2.0",
                        "hotspots_json": "[]",
                    },
                )
                if message_id:
                    promoted = True
                    break
                time.sleep(2)

                nodes_after = _parse_cluster_nodes(
                    subprocess.run(
                        [
                            "docker",
                            "exec",
                            "neosentinel-redis-node-2",
                            "redis-cli",
                            "cluster",
                            "nodes",
                        ],
                        capture_output=True,
                        text=True,
                        timeout=10,
                        check=False,
                    ).stdout
                )
                for node in nodes_after:
                    if node["id"] == replica["id"] and "master" in node["flags"]:
                        promoted = True
                        break
                if promoted:
                    break
                time.sleep(2)
            assert promoted
        finally:
            subprocess.run(
                ["docker", "start", container],
                capture_output=True,
                timeout=30,
                check=False,
            )
            for _ in range(45):
                info = _cluster_info()
                if "cluster_state:ok" in info:
                    break
                time.sleep(2)
