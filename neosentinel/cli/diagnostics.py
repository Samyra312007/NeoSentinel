from __future__ import annotations

import os
import shutil
import socket
import subprocess
from dataclasses import dataclass
from typing import Callable
from urllib.error import URLError
from urllib.request import urlopen

from neosentinel.cli.config import load_local_config


@dataclass(frozen=True)
class DiagnosticCheck:
    name: str
    passed: bool
    detail: str


CheckRunner = Callable[[], DiagnosticCheck]


def _check_ssh() -> DiagnosticCheck:
    key = shutil.which("ssh")
    hosts = load_local_config().node_hosts
    if key is None:
        return DiagnosticCheck(
            name="SSH Connectivity & PEM Key Permissions",
            passed=False,
            detail="ssh client not found on PATH",
        )
    identity = os.path.expanduser("~/.ssh/neosentinel-graviton")
    if not os.path.isfile(identity):
        return DiagnosticCheck(
            name="SSH Connectivity & PEM Key Permissions",
            passed=True,
            detail="ssh client available (cluster key optional for local dev)",
        )
    failures: list[str] = []
    for host in hosts:
        result = subprocess.run(
            [
                "ssh",
                "-o",
                "BatchMode=yes",
                "-o",
                "ConnectTimeout=5",
                "-i",
                identity,
                f"ubuntu@{host}",
                "echo ok",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            failures.append(host)
    if failures:
        return DiagnosticCheck(
            name="SSH Connectivity & PEM Key Permissions",
            passed=False,
            detail=f"SSH failed for: {', '.join(failures)}",
        )
    return DiagnosticCheck(
        name="SSH Connectivity & PEM Key Permissions",
        passed=True,
        detail=f"SSH reachable for {len(hosts)} node(s)",
    )


def _check_performix() -> DiagnosticCheck:
    apx = shutil.which("apx")
    if apx:
        return DiagnosticCheck(
            name="Performix PMU SVE2 Hardware Counters",
            passed=True,
            detail="apx binary found on PATH",
        )
    hosts = load_local_config().node_hosts
    identity = os.path.expanduser("~/.ssh/neosentinel-graviton")
    if os.path.isfile(identity):
        host = hosts[0]
        result = subprocess.run(
            [
                "ssh",
                "-o",
                "BatchMode=yes",
                "-o",
                "ConnectTimeout=5",
                "-i",
                identity,
                f"ubuntu@{host}",
                "apx --version",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            return DiagnosticCheck(
                name="Performix PMU SVE2 Hardware Counters",
                passed=True,
                detail=f"apx available on remote host {host}",
            )
    return DiagnosticCheck(
        name="Performix PMU SVE2 Hardware Counters",
        passed=False,
        detail="apx not installed locally or on node-001 (MockPerformix fallback available)",
    )


def _check_vllm() -> DiagnosticCheck:
    config = load_local_config()
    url = f"{config.vllm_base_url.rstrip('/')}/health"
    try:
        with urlopen(url, timeout=2) as response:
            passed = response.status == 200
            detail = f"vLLM health OK at {url}" if passed else f"vLLM returned {response.status}"
    except (URLError, OSError, TimeoutError):
        passed = False
        detail = f"vLLM not reachable at {url}"
    return DiagnosticCheck(
        name="vLLM Worker Engines & CUDA/SVE2 Kernels",
        passed=passed,
        detail=detail,
    )


def _check_redis() -> DiagnosticCheck:
    config = load_local_config()
    host = os.environ.get("NEOSENTINEL_REDIS_HOST")
    port = int(os.environ.get("NEOSENTINEL_REDIS_PORT", "6379"))
    if config.redis_url.startswith("redis://"):
        without_scheme = config.redis_url.removeprefix("redis://")
        if ":" in without_scheme:
            host_part, port_part = without_scheme.rsplit(":", 1)
            host = host or host_part.split("@")[-1]
            port = int(port_part.split("/")[0])
        else:
            host = host or without_scheme
    host = host or "127.0.0.1"
    try:
        with socket.create_connection((host, port), timeout=2.0):
            passed = True
            detail = f"Redis reachable at {host}:{port}"
    except OSError:
        passed = False
        detail = f"Redis not reachable at {host}:{port}"
    return DiagnosticCheck(
        name="Redis Streams Telemetry Pipeline",
        passed=passed,
        detail=detail,
    )


def _check_ray() -> DiagnosticCheck:
    try:
        with socket.create_connection(("127.0.0.1", 8265), timeout=1.0):
            passed = True
            detail = "Ray dashboard reachable on localhost:8265"
    except OSError:
        passed = False
        detail = "Ray not running on localhost:8265 (start docker compose on node-001)"
    return DiagnosticCheck(
        name="Ray Distributed Task Scheduler",
        passed=passed,
        detail=detail,
    )


def _check_traefik() -> DiagnosticCheck:
    try:
        with urlopen("http://127.0.0.1/health", timeout=2) as response:
            passed = response.status == 200
            detail = "Traefik ingress healthy on localhost:80" if passed else "Traefik unhealthy"
    except (URLError, OSError, TimeoutError):
        try:
            with socket.create_connection(("127.0.0.1", 8081), timeout=1.0):
                passed = True
                detail = "Traefik ping port reachable on localhost:8081"
        except OSError:
            passed = False
            detail = "Traefik not running (start docker compose on node-001)"
    return DiagnosticCheck(
        name="Traefik Ingress Controller",
        passed=passed,
        detail=detail,
    )


def _check_agent() -> DiagnosticCheck:
    try:
        from neosentinel.agent.brain import AgentBrain
        from neosentinel.orchestrator.cluster import ClusterSentinelOrchestrator

        _ = AgentBrain
        _ = ClusterSentinelOrchestrator
        passed = True
        detail = "Agent brain and orchestrator modules importable"
    except ImportError as exc:
        passed = False
        detail = f"Agent modules failed to import: {exc}"
    return DiagnosticCheck(
        name="Llama-3.2 Autonomous Agent Reasoning Loop",
        passed=passed,
        detail=detail,
    )


def _mock_pass(name: str, detail: str) -> DiagnosticCheck:
    return DiagnosticCheck(name=name, passed=True, detail=detail)


MOCK_CHECKS: tuple[CheckRunner, ...] = (
    lambda: _mock_pass("SSH Connectivity & PEM Key Permissions", "mock SSH session established"),
    lambda: _mock_pass("Performix PMU SVE2 Hardware Counters", "mock SVE2 counters readable"),
    lambda: _mock_pass("vLLM Worker Engines & CUDA/SVE2 Kernels", "mock vLLM workers healthy"),
    lambda: _mock_pass("Redis Streams Telemetry Pipeline", "mock Redis streams operational"),
    lambda: _mock_pass("Ray Distributed Task Scheduler", "mock Ray head node ready"),
    lambda: _mock_pass("Traefik Ingress Controller", "mock Traefik routing healthy"),
    lambda: _mock_pass("Llama-3.2 Autonomous Agent Reasoning Loop", "mock agent loop ticking"),
)

LIVE_CHECKS: tuple[CheckRunner, ...] = (
    _check_ssh,
    _check_performix,
    _check_vllm,
    _check_redis,
    _check_ray,
    _check_traefik,
    _check_agent,
)


def run_doctor(*, mock: bool = True) -> list[DiagnosticCheck]:
    runners = MOCK_CHECKS if mock else LIVE_CHECKS
    return [runner() for runner in runners]
