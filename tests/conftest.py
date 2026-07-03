from pathlib import Path

import pytest

DOCKER_DIR = Path(__file__).resolve().parents[1] / "docker"
TRAEFIK_DYNAMIC = DOCKER_DIR / "traefik" / "dynamic" / "vllm.yml"
TRAEFIK_STATIC = DOCKER_DIR / "traefik" / "traefik.yml"
COMPOSE_FILE = DOCKER_DIR / "docker-compose.yml"


def docker_available() -> bool:
    import shutil
    import subprocess

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
    import time
    import urllib.error
    import urllib.request

    deadline = time.monotonic() + timeout_s
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=5) as resp:
                if resp.status == 200:
                    return
        except (urllib.error.URLError, TimeoutError) as exc:
            last_error = exc
        time.sleep(2)
    raise TimeoutError(f"URL {url} not ready after {timeout_s}s: {last_error}")


@pytest.fixture(scope="session")
def compose_stack():
    if not docker_available():
        pytest.skip("Docker is not available")
    _compose("down", "-v", "--remove-orphans")
    up = _compose("up", "-d", "--build")
    if up.returncode != 0:
        pytest.skip(f"docker compose up failed: {up.stderr}")
    try:
        _wait_for_url("http://localhost/health")
        yield
    finally:
        _compose("down", "-v", "--remove-orphans")
