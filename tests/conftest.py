from pathlib import Path

import pytest

DOCKER_DIR = Path(__file__).resolve().parents[1] / "docker"
TRAEFIK_DYNAMIC = DOCKER_DIR / "traefik" / "dynamic" / "vllm.yml"
TRAEFIK_STATIC = DOCKER_DIR / "traefik" / "traefik.yml"
COMPOSE_FILE = DOCKER_DIR / "docker-compose.yml"
DEBUG_LOG = Path(__file__).resolve().parents[1] / "debug-60562a.log"


def _debug_log(hypothesis_id: str, location: str, message: str, data: dict) -> None:
    import json
    import time

    payload = {
        "sessionId": "60562a",
        "hypothesisId": hypothesis_id,
        "location": location,
        "message": message,
        "data": data,
        "timestamp": int(time.time() * 1000),
    }
    # #region agent log
    with DEBUG_LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload) + "\n")
    # #endregion


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
    import http.client
    import time
    import urllib.error
    import urllib.request

    deadline = time.monotonic() + timeout_s
    last_error: Exception | None = None
    attempt = 0
    while time.monotonic() < deadline:
        attempt += 1
        try:
            with urllib.request.urlopen(url, timeout=5) as resp:
                if resp.status == 200:
                    # #region agent log
                    _debug_log(
                        "H2",
                        "conftest.py:_wait_for_url",
                        "url ready",
                        {"url": url, "attempt": attempt, "status": resp.status},
                    )
                    # #endregion
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
            # #region agent log
            _debug_log(
                "H1",
                "conftest.py:_wait_for_url",
                "url not ready",
                {
                    "url": url,
                    "attempt": attempt,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                },
            )
            # #endregion
        time.sleep(2)
    raise TimeoutError(f"URL {url} not ready after {timeout_s}s: {last_error}")


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
        "redis",
    )
    # #region agent log
    _debug_log(
        "H3",
        "conftest.py:compose_stack",
        "compose up finished",
        {
            "returncode": up.returncode,
            "stdout_tail": up.stdout[-2000:],
            "stderr_tail": up.stderr[-2000:],
        },
    )
    # #endregion
    if up.returncode != 0:
        pytest.skip(f"docker compose up failed: {up.stderr}")
    ps = _compose("ps", "--format", "json")
    # #region agent log
    _debug_log(
        "H4",
        "conftest.py:compose_stack",
        "compose ps after up",
        {"returncode": ps.returncode, "output": ps.stdout[-3000:]},
    )
    # #endregion
    try:
        _wait_for_url("http://127.0.0.1:8081/ping", timeout_s=60.0)
        _wait_for_url("http://127.0.0.1/health", timeout_s=120.0)
        yield
    finally:
        _compose("down", "-v", "--remove-orphans")
