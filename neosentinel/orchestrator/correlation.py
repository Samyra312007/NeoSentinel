from __future__ import annotations

from dataclasses import dataclass

from neosentinel.agent.decision_tree import (
    DRAM_HIGH_THRESHOLD,
    SVE2_LOW_THRESHOLD,
    evaluate_node,
)
from neosentinel.contracts.decision import ActionType
from neosentinel.contracts.telemetry import NodeSnapshot, NodeStatus, TelemetrySnapshot

CORRELATION_SVE2_UNDERUTILIZATION = "sve2_underutilization"
CORRELATION_KV_EVICTION_FLOOD = "kv_eviction_flood"
CORRELATION_DRAM_SATURATION = "dram_saturation"
CORRELATION_SINGLE_NODE = "single_node_degradation"
CORRELATION_HEALTHY = "healthy_cluster"


@dataclass(frozen=True)
class CorrelationFinding:
    pattern: str
    affected_nodes: tuple[str, ...]
    severity: float
    recommended_action: ActionType
    cluster_wide: bool
    target_node: str


def _is_degraded(node: NodeSnapshot) -> bool:
    return node.status in {NodeStatus.DEGRADED, NodeStatus.UNHEALTHY}


def correlate_snapshot(snapshot: TelemetrySnapshot) -> list[CorrelationFinding]:
    findings: list[CorrelationFinding] = []
    degraded = [node for node in snapshot.nodes if _is_degraded(node)]

    sve2_nodes = tuple(
        node.node_id
        for node in snapshot.nodes
        if node.sve2_utilization_pct < SVE2_LOW_THRESHOLD
    )
    if len(sve2_nodes) >= 2:
        candidate = evaluate_node(next(n for n in snapshot.nodes if n.node_id == sve2_nodes[0]))
        findings.append(
            CorrelationFinding(
                pattern=CORRELATION_SVE2_UNDERUTILIZATION,
                affected_nodes=sve2_nodes,
                severity=100.0 - min(
                    n.sve2_utilization_pct for n in snapshot.nodes if n.node_id in sve2_nodes
                ),
                recommended_action=candidate.action,
                cluster_wide=True,
                target_node=sve2_nodes[0],
            )
        )

    kv_nodes = tuple(
        node.node_id for node in snapshot.nodes if node.kv_eviction_rate > 3.0
    )
    if len(kv_nodes) >= 2:
        kv_severity = max(
            node.kv_eviction_rate for node in snapshot.nodes if node.node_id in kv_nodes
        )
        findings.append(
            CorrelationFinding(
                pattern=CORRELATION_KV_EVICTION_FLOOD,
                affected_nodes=kv_nodes,
                severity=kv_severity,
                recommended_action=ActionType.ADJUST_VLLM_CONFIG,
                cluster_wide=True,
                target_node=kv_nodes[0],
            )
        )

    dram_nodes = tuple(
        node.node_id
        for node in snapshot.nodes
        if node.dram_bandwidth_pct > DRAM_HIGH_THRESHOLD
    )
    if len(dram_nodes) >= 2:
        findings.append(
            CorrelationFinding(
                pattern=CORRELATION_DRAM_SATURATION,
                affected_nodes=dram_nodes,
                severity=max(
                    node.dram_bandwidth_pct for node in snapshot.nodes if node.node_id in dram_nodes
                ),
                recommended_action=ActionType.ADJUST_VLLM_CONFIG,
                cluster_wide=True,
                target_node=dram_nodes[0],
            )
        )

    if not findings and degraded:
        worst = max(degraded, key=lambda node: node.ttft_p99_ms)
        candidate = evaluate_node(worst)
        findings.append(
            CorrelationFinding(
                pattern=CORRELATION_SINGLE_NODE,
                affected_nodes=(worst.node_id,),
                severity=worst.ttft_p99_ms,
                recommended_action=candidate.action,
                cluster_wide=False,
                target_node=worst.node_id,
            )
        )

    if not findings:
        findings.append(
            CorrelationFinding(
                pattern=CORRELATION_HEALTHY,
                affected_nodes=tuple(node.node_id for node in snapshot.nodes),
                severity=0.0,
                recommended_action=ActionType.NOOP,
                cluster_wide=False,
                target_node=snapshot.nodes[0].node_id,
            )
        )

    return sorted(findings, key=lambda item: item.severity, reverse=True)


def primary_finding(snapshot: TelemetrySnapshot) -> CorrelationFinding:
    return correlate_snapshot(snapshot)[0]
