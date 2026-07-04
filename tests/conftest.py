from __future__ import annotations

import subprocess
import time
from pathlib import Path

import pytest

DOCKER_DIR = Path(__file__).resolve().parents[1] / "docker"
TRAEFIK_DYNAMIC = DOCKER_DIR / "traefik" / "dynamic" / "vllm.yml"
TRAEFIK_STATIC = DOCKER_DIR / "traefik" / "traefik.yml"
COMPOSE_FILE = DOCKER_DIR / "docker-compose.yml"

REDIS_CLUSTER_NODES = tuple(f"redis-node-{i}" for i in range(1, 7))


def docker_available() -> bool:
    import shutil

    if shutil.which("docker") is None:
        return False
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            timeout=10,
            check=False,
        )
        return result.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


requires_docker = pytest.mark.skipif(
    not docker_available(),
    reason="Docker is not available",
)

COMPOSE_PROJECT = "neosentinel-test"


def _compose(*args: str):
    import subprocess

    return subprocess.run(
        ["docker", "compose", "-f", str(COMPOSE_FILE), "-p", COMPOSE_PROJECT, *args],
        cwd=COMPOSE_FILE.parent,
        capture_output=True,
        text=True,
        check=False,
        timeout=300,
    )


def _wait_for_url(url: str, timeout_s: float = 120.0) -> None:
    import http.client
    import urllib.error
    import urllib.request

    deadline = time.monotonic() + timeout_s
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=5) as resp:
                if resp.status == 200:
                    return
        except (
            urllib.error.URLError,
            urllib.error.HTTPError,
            TimeoutError,
            http.client.RemoteDisconnected,
            ConnectionError,
            OSError,
        ) as exc:
            last_error = exc
        time.sleep(2)
    raise TimeoutError(f"URL {url} not ready after {timeout_s}s: {last_error}")


def _wait_for_redis_cluster(timeout_s: float = 120.0) -> None:
    deadline = time.monotonic() + timeout_s
    last_output = ""
    while time.monotonic() < deadline:
        result = subprocess.run(
            [
                "docker",
                "exec",
                "neosentinel-redis-node-1",
                "redis-cli",
                "cluster",
                "info",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        last_output = result.stdout
        if "cluster_state:ok" in last_output:
            return
        time.sleep(2)
    raise TimeoutError(f"Redis cluster not ready after {timeout_s}s: {last_output}")


@pytest.fixture(scope="session")
def compose_stack():
    if not docker_available():
        pytest.skip("Docker is not available")
    _compose("down", "-v", "--remove-orphans")
    up = _compose(
        "up",
        "-d",
        "--build",
        "--wait",
        "traefik",
        "vllm-worker-1",
        "vllm-worker-2",
        "vllm-worker-3",
        *REDIS_CLUSTER_NODES,
        "redis-cluster-init",
    )
    if up.returncode != 0:
        pytest.skip(f"docker compose up failed: {up.stderr}")
    try:
        _wait_for_url("http://127.0.0.1:8081/ping", timeout_s=60.0)
        _wait_for_url("http://127.0.0.1/health", timeout_s=120.0)
        _wait_for_redis_cluster(timeout_s=120.0)
        yield
    finally:
        _compose("down", "-v", "--remove-orphans")


@pytest.fixture
def fake_redis():
    import fakeredis

    client = fakeredis.FakeRedis(decode_responses=True)
    yield client
    client.flushall()


@pytest.fixture
def telemetry_pipeline(fake_redis):
    from neosentinel.distributed.streams import TelemetryPipeline

    pipeline = TelemetryPipeline(fake_redis)
    pipeline.ensure_streams()
    return pipeline
