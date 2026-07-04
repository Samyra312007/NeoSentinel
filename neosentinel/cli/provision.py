from __future__ import annotations

import time
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
    ProvisionStep("Installing Performix PMU SVE2 instrumentation", "apx --version"),
    ProvisionStep(
        "Starting vLLM inference workers and Traefik ingress",
        "systemctl is-active vllm",
    ),
)


class MockSshRunner:
    def run(self, host: str, command: str) -> tuple[int, str]:
        _ = command
        return 0, f"ok@{host}"


def node_hosts(count: int) -> tuple[str, ...]:
    return tuple(f"node-{i:03d}.graviton4.local" for i in range(1, count + 1))


def provision_cluster(
    nodes: int,
    *,
    runner: SshRunner | None = None,
    sleeper: Callable[[float], None] | None = None,
) -> ProvisionResult:
    if nodes < 1:
        raise ValueError("Node count must be at least 1")
    ssh = runner or MockSshRunner()
    sleep = sleeper or time.sleep
    hosts = node_hosts(nodes)
    completed = 0
    for host in hosts:
        for step in DEFAULT_STEPS:
            code, _output = ssh.run(host, step.command)
            if code != 0:
                raise RuntimeError(f"Provision failed on {host}: {step.label}")
            completed += 1
            sleep(0.01)
    return ProvisionResult(nodes=nodes, steps_completed=completed, hosts=hosts)
