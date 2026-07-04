from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from neosentinel.contracts.decision import ActionType
from neosentinel.contracts.telemetry import NodeSnapshot, NodeStatus, TelemetrySnapshot

SVE2_LOW_THRESHOLD = 50.0
TTFT_HIGH_THRESHOLD = 250.0
DRAM_HIGH_THRESHOLD = 85.0
KV_EVICTION_HIGH_THRESHOLD = 3.0
CACHE_MISS_HIGH_THRESHOLD = 40.0
SVE2_CRITICAL_THRESHOLD = 20.0
TTFT_CRITICAL_THRESHOLD = 500.0


@dataclass(frozen=True)
class DecisionCandidate:
    node_id: str
    action: ActionType
    confidence: float
    reasoning: str
    parameters: dict[str, object]
    quorum_required: bool = False


def derive_node_status(node: NodeSnapshot) -> NodeStatus:
    if (
        node.sve2_utilization_pct < SVE2_CRITICAL_THRESHOLD
        or node.ttft_p99_ms > TTFT_CRITICAL_THRESHOLD
    ):
        return NodeStatus.UNHEALTHY
    if (
        node.sve2_utilization_pct < SVE2_LOW_THRESHOLD
        or node.ttft_p99_ms > TTFT_HIGH_THRESHOLD
        or node.dram_bandwidth_pct > DRAM_HIGH_THRESHOLD
        or node.kv_eviction_rate > KV_EVICTION_HIGH_THRESHOLD
    ):
        return NodeStatus.DEGRADED
    return NodeStatus.HEALTHY


def evaluate_node(node: NodeSnapshot) -> DecisionCandidate:
    if (
        node.sve2_utilization_pct < SVE2_LOW_THRESHOLD
        and node.ttft_p99_ms > TTFT_HIGH_THRESHOLD
    ):
        return DecisionCandidate(
            node_id=node.node_id,
            action=ActionType.TRIGGER_REQUANTIZE,
            confidence=0.94,
            reasoning=(
                f"SVE2 at {node.sve2_utilization_pct:.1f}% with TTFT "
                f"{node.ttft_p99_ms:.0f}ms — INT4 requantize to restore KleidiAI SVE2 kernels."
            ),
            parameters={"target_precision": "int4", "enable_kleidiai": True},
            quorum_required=True,
        )

    if (
        node.kv_eviction_rate > KV_EVICTION_HIGH_THRESHOLD
        and node.dram_bandwidth_pct > DRAM_HIGH_THRESHOLD
    ):
        return DecisionCandidate(
            node_id=node.node_id,
            action=ActionType.ADJUST_VLLM_CONFIG,
            confidence=0.91,
            reasoning=(
                f"KV eviction {node.kv_eviction_rate:.1f}/s with DRAM "
                f"{node.dram_bandwidth_pct:.1f}% — reduce KV cache pressure."
            ),
            parameters={"max_num_batched_tokens": 2048, "gpu_memory_utilization": 0.85},
        )

    if node.kv_eviction_rate > KV_EVICTION_HIGH_THRESHOLD:
        return DecisionCandidate(
            node_id=node.node_id,
            action=ActionType.SCALE_WORKER_THREADS,
            confidence=0.86,
            reasoning=(
                f"KV eviction rate {node.kv_eviction_rate:.1f}/s exceeds "
                f"{KV_EVICTION_HIGH_THRESHOLD} — scale worker threads."
            ),
            parameters={"worker_threads_delta": 2},
        )

    if node.sve2_utilization_pct < SVE2_LOW_THRESHOLD:
        return DecisionCandidate(
            node_id=node.node_id,
            action=ActionType.ARM_PERFORMIX_ANALYZE,
            confidence=0.88,
            reasoning=(
                f"SVE2 utilization {node.sve2_utilization_pct:.1f}% below "
                f"{SVE2_LOW_THRESHOLD}% — run Performix hotspot analysis."
            ),
            parameters={"recipe": "code_hotspots", "sample_ms": 5000},
        )

    if node.ttft_p99_ms > TTFT_HIGH_THRESHOLD:
        return DecisionCandidate(
            node_id=node.node_id,
            action=ActionType.ADJUST_VLLM_CONFIG,
            confidence=0.87,
            reasoning=(
                f"TTFT P99 {node.ttft_p99_ms:.0f}ms exceeds "
                f"{TTFT_HIGH_THRESHOLD}ms — tune batch and scheduling."
            ),
            parameters={"max_num_seqs": 128, "enable_chunked_prefill": True},
        )

    if node.dram_bandwidth_pct > DRAM_HIGH_THRESHOLD:
        return DecisionCandidate(
            node_id=node.node_id,
            action=ActionType.ADJUST_VLLM_CONFIG,
            confidence=0.84,
            reasoning=(
                f"DRAM bandwidth {node.dram_bandwidth_pct:.1f}% exceeds "
                f"{DRAM_HIGH_THRESHOLD}% — reduce memory footprint."
            ),
            parameters={"swap_space": 4, "block_size": 16},
        )

    if node.cache_miss_rate_pct > CACHE_MISS_HIGH_THRESHOLD:
        return DecisionCandidate(
            node_id=node.node_id,
            action=ActionType.ARM_PERFORMIX_ANALYZE,
            confidence=0.82,
            reasoning=(
                f"Cache miss rate {node.cache_miss_rate_pct:.1f}% exceeds "
                f"{CACHE_MISS_HIGH_THRESHOLD}% — profile memory access patterns."
            ),
            parameters={"recipe": "memory_bandwidth"},
        )

    return DecisionCandidate(
        node_id=node.node_id,
        action=ActionType.NOOP,
        confidence=0.99,
        reasoning="All metrics within baseline thresholds.",
        parameters={},
    )


def _severity(node: NodeSnapshot) -> float:
    status = derive_node_status(node)
    if status == NodeStatus.UNHEALTHY:
        base = 1000.0
    elif status == NodeStatus.DEGRADED:
        base = 500.0
    else:
        base = 0.0
    return (
        base
        + max(0.0, node.ttft_p99_ms - TTFT_HIGH_THRESHOLD)
        + max(0.0, SVE2_LOW_THRESHOLD - node.sve2_utilization_pct) * 2
        + max(0.0, node.kv_eviction_rate - KV_EVICTION_HIGH_THRESHOLD) * 10
        + max(0.0, node.dram_bandwidth_pct - DRAM_HIGH_THRESHOLD)
    )


def select_worst_node(snapshot: TelemetrySnapshot) -> NodeSnapshot:
    return max(snapshot.nodes, key=_severity)


def evaluate_snapshot(snapshot: TelemetrySnapshot) -> DecisionCandidate:
    worst = select_worst_node(snapshot)
    return evaluate_node(worst)


def new_decision_id(*, prefix: str = "dec") -> str:
    ts = datetime.now(UTC).strftime("%Y%m%d%H%M%S%f")
    return f"{prefix}-{ts}"
