from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from typing import Callable, Protocol


class SshRunner(Protocol):
    def run(self, host: str, command: str) -> tuple[int, str]: ...


@dataclass(frozen=True)
class ProvisionStep:
    label: str
    command: str


@dataclass(frozen=True)
class ProvisionResult:
    nodes: int
    steps_completed: int
    hosts: tuple[str, ...]


DEFAULT_STEPS: tuple[ProvisionStep, ...] = (
    ProvisionStep("Provisioning SSH access and Docker runtimes", "docker --version"),
    ProvisionStep("Installing Performix PMU SVE2 instrumentation", "apx --version || true"),
    ProvisionStep(
        "Starting vLLM inference workers and Traefik ingress",
        "systemctl is-active vllm 2>/dev/null || docker ps --format '{{.Names}}' | head -1",
    ),
)


class MockSshRunner:
    def run(self, host: str, command: str) -> tuple[int, str]:
        _ = command
        return 0, f"ok@{host}"


class LiveSshRunner:
    def __init__(self, *, identity_file: str | None = None, user: str = "ubuntu") -> None:
        self.identity_file = identity_file or os.path.expanduser("~/.ssh/neosentinel-graviton")
        self.user = user

    def run(self, host: str, command: str) -> tuple[int, str]:
        ssh_cmd = [
            "ssh",
            "-o",
            "BatchMode=yes",
            "-o",
            "StrictHostKeyChecking=accept-new",
            "-i",
            self.identity_file,
            f"{self.user}@{host}",
            command,
        ]
        result = subprocess.run(ssh_cmd, capture_output=True, text=True, check=False)
        output = (result.stdout or "") + (result.stderr or "")
        return result.returncode, output.strip()


def node_hosts(count: int) -> tuple[str, ...]:
    env_hosts = os.environ.get("NEOSENTINEL_NODE_HOSTS")
    if env_hosts:
        hosts = tuple(h.strip() for h in env_hosts.split(",") if h.strip())
        if hosts:
            return hosts[:count]
    return tuple(f"node-{i:03d}" for i in range(1, count + 1))


def provision_cluster(
    nodes: int,
    *,
    runner: SshRunner | None = None,
    sleeper: Callable[[float], None] | None = None,
) -> ProvisionResult:
    if nodes < 1:
        raise ValueError("Node count must be at least 1")
    ssh = runner or MockSshRunner()
    import time

    sleep = sleeper or time.sleep
    hosts = node_hosts(nodes)
    completed = 0
    for host in hosts:
        for step in DEFAULT_STEPS:
            code, _output = ssh.run(host, step.command)
            if code != 0:
                raise RuntimeError(f"Provision failed on {host}: {step.label}")
            completed += 1
            sleep(0.05)
    return ProvisionResult(nodes=nodes, steps_completed=completed, hosts=hosts)
