"""Scenario catalog and definitions for NeoSentinel simulation and offline demo testing."""

from typing import Any, Dict, List


class ScenarioDefinition:
    """Represents a standardized cluster anomaly and recovery scenario."""

    def __init__(
        self,
        name: str,
        title: str,
        description: str,
        target_node: str,
        expected_action: str,
        initial_sve2_pct: float,
        initial_ttft_ms: float,
        recovered_sve2_pct: float,
        recovered_ttft_ms: float,
    ) -> None:
        self.name = name
        self.title = title
        self.description = description
        self.target_node = target_node
        self.expected_action = expected_action
        self.initial_sve2_pct = initial_sve2_pct
        self.initial_ttft_ms = initial_ttft_ms
        self.recovered_sve2_pct = recovered_sve2_pct
        self.recovered_ttft_ms = recovered_ttft_ms

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "title": self.title,
            "description": self.description,
            "target_node": self.target_node,
            "expected_action": self.expected_action,
            "metrics_before": {
                "sve2_utilization_pct": self.initial_sve2_pct,
                "ttft_p99_ms": self.initial_ttft_ms,
            },
            "metrics_after": {
                "sve2_utilization_pct": self.recovered_sve2_pct,
                "ttft_p99_ms": self.recovered_ttft_ms,
            },
        }


SCENARIOS: Dict[str, ScenarioDefinition] = {
    "sve2_underutilization": ScenarioDefinition(
        name="sve2_underutilization",
        title="SVE2 PMU Underutilization & GEMM Bottleneck",
        description="Sub-optimal FP16 GEMM kernel execution causing SVE2 pipeline stalls and TTFT spikes.",
        target_node="node-002",
        expected_action="trigger_requantize",
        initial_sve2_pct=29.0,
        initial_ttft_ms=312.0,
        recovered_sve2_pct=79.0,
        recovered_ttft_ms=131.0,
    ),
    "kv_eviction_flood": ScenarioDefinition(
        name="kv_eviction_flood",
        title="KV Cache Eviction Flood & DRAM Saturation",
        description="High concurrent request burst causing excessive KV cache eviction and DRAM bandwidth saturation.",
        target_node="node-001",
        expected_action="rebalance_kv_load",
        initial_sve2_pct=91.5,
        initial_ttft_ms=680.0,
        recovered_sve2_pct=82.0,
        recovered_ttft_ms=115.0,
    ),
    "thermal_throttling": ScenarioDefinition(
        name="thermal_throttling",
        title="Graviton4 Thermal Throttling & Clock Truncation",
        description="Core overheating leading to dynamic CPU clock scaling and inference latency degradation.",
        target_node="node-003",
        expected_action="migrate_workload",
        initial_sve2_pct=45.0,
        initial_ttft_ms=520.0,
        recovered_sve2_pct=85.0,
        recovered_ttft_ms=140.0,
    ),
    "memory_leak_degradation": ScenarioDefinition(
        name="memory_leak_degradation",
        title="vLLM Worker Memory Leak & Swap Thrashing",
        description="Progressive memory leak in vLLM attention buffers causing virtual memory swap thrashing.",
        target_node="node-002",
        expected_action="restart_worker",
        initial_sve2_pct=15.0,
        initial_ttft_ms=890.0,
        recovered_sve2_pct=88.0,
        recovered_ttft_ms=125.0,
    ),
    "network_partition_latency": ScenarioDefinition(
        name="network_partition_latency",
        title="Inter-Node Network Partition & Packet Drops",
        description="High packet loss on tensor-parallel interconnect causing distributed consensus timeouts.",
        target_node="node-001",
        expected_action="isolate_node",
        initial_sve2_pct=10.0,
        initial_ttft_ms=1200.0,
        recovered_sve2_pct=80.0,
        recovered_ttft_ms=110.0,
    ),
}


def get_scenario(name: str) -> ScenarioDefinition:
    """Retrieve a scenario definition by name."""
    if name not in SCENARIOS:
        raise ValueError(f"Unknown scenario '{name}'. Available: {list(SCENARIOS.keys())}")
    return SCENARIOS[name]


def list_scenarios() -> List[Dict[str, Any]]:
    """List all available simulation scenarios."""
    return [s.to_dict() for s in SCENARIOS.values()]
