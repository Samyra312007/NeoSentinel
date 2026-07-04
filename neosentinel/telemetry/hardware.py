from __future__ import annotations

import os
import platform
import shutil
from dataclasses import dataclass

from neosentinel.telemetry.performix import PerformixDaemon, PmuFrame, parse_apx_output

SVE2_COUNTER_MIN = 0.0
SVE2_COUNTER_MAX = 100.0
HARDWARE_ENV_VAR = "NEOSENTINEL_HARDWARE"


@dataclass(frozen=True)
class HardwareValidationResult:
    available: bool
    platform_machine: str
    apx_found: bool
    sve2_readable: bool
    frame: PmuFrame | None
    message: str

    @property
    def passed(self) -> bool:
        return self.available and self.sve2_readable


def is_hardware_validation_enabled() -> bool:
    return os.environ.get(HARDWARE_ENV_VAR, "").strip() in {"1", "true", "yes"}


def is_arm64_platform() -> bool:
    machine = platform.machine().lower()
    return machine in {"aarch64", "arm64"}


def validate_graviton4_performix(
    *,
    node_id: str = "node-001",
    apx_path: str = "apx",
    runner=None,
) -> HardwareValidationResult:
    machine = platform.machine()
    apx_found = shutil.which(apx_path) is not None
    enabled = is_hardware_validation_enabled()

    if runner is not None:
        daemon = PerformixDaemon(node_id, apx_path=apx_path, runner=runner)
        frame = daemon.collect_once()
        sve2_ok = SVE2_COUNTER_MIN <= frame.sve2_utilization_pct <= SVE2_COUNTER_MAX
        return HardwareValidationResult(
            available=True,
            platform_machine=machine,
            apx_found=True,
            sve2_readable=sve2_ok,
            frame=frame,
            message="Performix PMU frame collected via injected runner.",
        )

    if not enabled:
        return HardwareValidationResult(
            available=False,
            platform_machine=machine,
            apx_found=apx_found,
            sve2_readable=False,
            frame=None,
            message=f"Set {HARDWARE_ENV_VAR}=1 to run real Graviton4 Performix validation.",
        )

    if not is_arm64_platform():
        return HardwareValidationResult(
            available=False,
            platform_machine=machine,
            apx_found=apx_found,
            sve2_readable=False,
            frame=None,
            message="Graviton4 validation requires ARM64 hardware.",
        )

    if not apx_found:
        return HardwareValidationResult(
            available=False,
            platform_machine=machine,
            apx_found=False,
            sve2_readable=False,
            frame=None,
            message=f"Performix apx binary not found at '{apx_path}'.",
        )

    try:
        daemon = PerformixDaemon(node_id, apx_path=apx_path)
        frame = daemon.collect_once()
    except Exception as exc:
        return HardwareValidationResult(
            available=True,
            platform_machine=machine,
            apx_found=True,
            sve2_readable=False,
            frame=None,
            message=f"Performix collection failed: {exc}",
        )

    sve2_ok = SVE2_COUNTER_MIN <= frame.sve2_utilization_pct <= SVE2_COUNTER_MAX
    return HardwareValidationResult(
        available=True,
        platform_machine=machine,
        apx_found=True,
        sve2_readable=sve2_ok,
        frame=frame,
        message="SVE2 counter readable on Graviton4 hardware."
        if sve2_ok
        else "SVE2 counter out of expected range.",
    )


def parse_and_validate_apx_sample(text: str, *, node_id: str = "node-001") -> PmuFrame:
    frame = parse_apx_output(text, node_id=node_id)
    if not (SVE2_COUNTER_MIN <= frame.sve2_utilization_pct <= SVE2_COUNTER_MAX):
        raise ValueError("SVE2 counter not within readable PMU range")
    return frame
