"""Cluster report data provider (Sahil · Week 6).

Turns the frozen telemetry / healing / audit contract objects into a single
typed ``ClusterReport``. This is the backend data source that feeds Divyansh's
``neosentinel report`` CLI (D5.4) — the CLI stays a thin renderer while all the
aggregation and health-verdict logic lives here.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

from pydantic import BaseModel, Field

from neosentinel.contracts.telemetry import NodeSnapshot, NodeStatus, TelemetrySnapshot
from neosentinel.contracts.websocket import AuditEvent, HealingEvent


class NodeReport(BaseModel):
    """Flattened per-node view for the report."""

    node_id: str
    status: NodeStatus
    ttft_p99_ms: float
    tokens_per_sec: float
    sve2_utilization_pct: float
    dram_bandwidth_pct: float
    requests_per_min: float
    top_hotspot: str | None = None


class HealingSummary(BaseModel):
    """Aggregate outcome of the autonomous recovery actions in the window."""

    total: int = 0
    succeeded: int = 0
    failed: int = 0
    rolled_back: int = 0
    success_rate: float = 0.0
    avg_ttft_improvement_ms: float = 0.0
    avg_sve2_gain_pct: float = 0.0


class AuditRecord(BaseModel):
    """One GitOps audit entry, ready to render."""

    timestamp: datetime
    commit_sha: str
    short_sha: str
    node_id: str
    action: str
    message: str
    checkpoint_id: str


class ClusterReport(BaseModel):
    """Complete health + audit report for a cluster at a point in time."""

    generated_at: datetime
    cluster_id: str
    total_nodes: int
    healthy_nodes: int
    degraded_nodes: int
    unhealthy_nodes: int
    overall_status: str = Field(description="HEALTHY | DEGRADED | CRITICAL")
    headline: str
    nodes: list[NodeReport] = Field(default_factory=list)
    healing: HealingSummary = Field(default_factory=HealingSummary)
    audit: list[AuditRecord] = Field(default_factory=list)


def _node_report(node: NodeSnapshot) -> NodeReport:
    return NodeReport(
        node_id=node.node_id,
        status=node.status,
        ttft_p99_ms=node.ttft_p99_ms,
        tokens_per_sec=node.tokens_per_sec,
        sve2_utilization_pct=node.sve2_utilization_pct,
        dram_bandwidth_pct=node.dram_bandwidth_pct,
        requests_per_min=node.requests_per_min,
        top_hotspot=node.hotspots[0].symbol if node.hotspots else None,
    )


def _healing_summary(events: Sequence[HealingEvent]) -> HealingSummary:
    if not events:
        return HealingSummary()

    succeeded = [e for e in events if e.status == "success"]
    failed = sum(1 for e in events if e.status == "failed")
    rolled_back = sum(1 for e in events if e.status == "rolled_back")

    def _avg(values: list[float]) -> float:
        return round(sum(values) / len(values), 2) if values else 0.0

    return HealingSummary(
        total=len(events),
        succeeded=len(succeeded),
        failed=failed,
        rolled_back=rolled_back,
        success_rate=round(len(succeeded) / len(events), 4),
        avg_ttft_improvement_ms=_avg(
            [e.before.ttft_p99_ms - e.after.ttft_p99_ms for e in succeeded]
        ),
        avg_sve2_gain_pct=_avg(
            [e.after.sve2_utilization_pct - e.before.sve2_utilization_pct for e in succeeded]
        ),
    )


def _audit_record(event: AuditEvent) -> AuditRecord:
    return AuditRecord(
        timestamp=event.timestamp,
        commit_sha=event.commit_sha,
        short_sha=event.commit_sha[:7],
        node_id=event.node_id,
        action=str(event.action),
        message=event.message,
        checkpoint_id=event.checkpoint_id,
    )


def _verdict(healthy: int, degraded: int, unhealthy: int) -> tuple[str, str]:
    """Return (overall_status, headline) from the node status breakdown."""
    if unhealthy > 0:
        return "CRITICAL", f"Graviton4 Control Plane Critical — {unhealthy} node(s) unhealthy"
    if degraded > 0:
        return "DEGRADED", f"Graviton4 Control Plane Degraded — {degraded} node(s) degraded"
    return "HEALTHY", "Graviton4 Control Plane Nominal"


def build_cluster_report(
    snapshot: TelemetrySnapshot,
    healing_events: Sequence[HealingEvent] = (),
    audit_events: Sequence[AuditEvent] = (),
    *,
    generated_at: datetime | None = None,
) -> ClusterReport:
    """Aggregate a telemetry snapshot + healing/audit history into a report."""
    healthy = sum(1 for n in snapshot.nodes if n.status == NodeStatus.HEALTHY)
    degraded = sum(1 for n in snapshot.nodes if n.status == NodeStatus.DEGRADED)
    unhealthy = sum(1 for n in snapshot.nodes if n.status == NodeStatus.UNHEALTHY)
    overall_status, headline = _verdict(healthy, degraded, unhealthy)

    return ClusterReport(
        generated_at=generated_at or datetime.now(UTC),
        cluster_id=snapshot.cluster_id,
        total_nodes=len(snapshot.nodes),
        healthy_nodes=healthy,
        degraded_nodes=degraded,
        unhealthy_nodes=unhealthy,
        overall_status=overall_status,
        headline=headline,
        nodes=[_node_report(n) for n in snapshot.nodes],
        healing=_healing_summary(healing_events),
        audit=[_audit_record(a) for a in audit_events],
    )


def nominal_cluster_report(
    cluster_id: str = "cluster-graviton4",
    *,
    generated_at: datetime | None = None,
) -> ClusterReport:
    """A healthy 3-node report — the offline default for the ``report`` CLI."""
    now = generated_at or datetime.now(UTC)
    nodes = [
        NodeSnapshot(
            node_id=f"node-{i:03d}",
            status=NodeStatus.HEALTHY,
            timestamp=now,
            ttft_p99_ms=120.0,
            tokens_per_sec=45.0,
            sve2_utilization_pct=80.0,
            dram_bandwidth_pct=55.0,
            cache_miss_rate_pct=12.0,
            kv_eviction_rate=0.5,
            requests_per_min=350.0,
        )
        for i in range(1, 4)
    ]
    snapshot = TelemetrySnapshot(cluster_id=cluster_id, timestamp=now, nodes=nodes)
    return build_cluster_report(snapshot, generated_at=now)
