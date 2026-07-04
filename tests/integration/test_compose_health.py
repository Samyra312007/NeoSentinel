import json
import subprocess
import urllib.request

import yaml

from tests.conftest import COMPOSE_FILE, requires_docker

REQUIRED_SERVICES = {
    "traefik",
    "vllm-worker-1",
    "vllm-worker-2",
    "vllm-worker-3",
    "redis-node-1",
    "redis-node-2",
    "redis-node-3",
    "redis-node-4",
    "redis-node-5",
    "redis-node-6",
    "redis-cluster-init",
    "ray-head",
}


BASE_URL = "http://127.0.0.1"


@requires_docker
class TestComposeHealth:
    def test_compose_file_defines_required_services(self):
        compose = yaml.safe_load(COMPOSE_FILE.read_text())
        services = set(compose["services"])
        assert REQUIRED_SERVICES <= services

    def test_traefik_health_returns_200(self, compose_stack):
        with urllib.request.urlopen(f"{BASE_URL}/health", timeout=10) as resp:
            assert resp.status == 200
            body = json.loads(resp.read())
            assert body["status"] == "ok"

    def test_redis_cluster_responds_to_ping(self, compose_stack):
        result = subprocess.run(
            ["docker", "exec", "neosentinel-redis-node-1", "redis-cli", "ping"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        assert "PONG" in result.stdout

    def test_all_vllm_workers_healthy(self, compose_stack):
        seen_nodes: set[str] = set()
        for _ in range(6):
            with urllib.request.urlopen(f"{BASE_URL}/health", timeout=10) as resp:
                body = json.loads(resp.read())
                assert body["status"] == "ok"
                seen_nodes.add(body["node_id"])
        assert len(seen_nodes) >= 1
