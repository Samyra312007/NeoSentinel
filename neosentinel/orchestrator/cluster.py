"""S5.2 ClusterSentinelOrchestrator — cross-node correlation engine.

Reads telemetry snapshots from all 3 Graviton4 nodes, detects cluster-wide
anomalies (correlated SVE2 under-utilisation, TTFT spikes, KV eviction floods),
and proposes ``SentinelDecision`` objects that may require quorum approval.

S5.3 Quorum voting — 2/3 agree before cluster-wide actions.
S5.4 Rolling restart logic — node-002 first pattern from spec.
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from neosentinel.contracts.decision import ActionType, SentinelDecision
from neosentinel.contracts.telemetry import NodeSnapshot

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Thresholds — taken from the NeoSentinel spec
# ---------------------------------------------------------------------------
SVE2_LOW_THRESHOLD = 40.0  # pct — below this triggers investigation
TTFT_HIGH_THRESHOLD = 250.0  # ms — above this = degraded latency
KV_EVICTION_HIGH = 5.0  # evictions/s — above = KV cache pressure
QUORUM_SIZE = 3  # total voters
QUORUM_MAJORITY = 2  # must agree

# Rolling restart ordering (spec: node-002 first, then 003, then 001)
ROLLING_RESTART_ORDER = ("node-002", "node-003", "node-001")


# ---------------------------------------------------------------------------
# Vote / Quorum types
# ---------------------------------------------------------------------------
class VoteValue(StrEnum):
    APPROVE = "approve"
    REJECT = "reject"
    ABSTAIN = "abstain"


@dataclass
class Vote:
    voter_id: str
    value: VoteValue
    reason: str = ""


@dataclass
class QuorumResult:
    """Outcome of a quorum vote."""

    decision_id: str
    votes: list[Vote] = field(default_factory=list)

    @property
    def approvals(self) -> int:
        return sum(1 for v in self.votes if v.value == VoteValue.APPROVE)

    @property
    def rejections(self) -> int:
        return sum(1 for v in self.votes if v.value == VoteValue.REJECT)

    @property
    def passed(self) -> bool:
        return self.approvals >= QUORUM_MAJORITY

    @property
    def total(self) -> int:
        return len(self.votes)


# ---------------------------------------------------------------------------
# Anomaly detection helpers
# ---------------------------------------------------------------------------
@dataclass
class AnomalySignal:
    """One detected anomaly on a single node."""

    node_id: str
    anomaly_type: str
    severity: float  # 0.0–1.0
    metric_value: float
    threshold: float
    suggested_action: ActionType


def detect_node_anomalies(node: NodeSnapshot) -> list[AnomalySignal]:
    """Return anomaly signals for a single node snapshot."""
    signals: list[AnomalySignal] = []

    if node.sve2_utilization_pct < SVE2_LOW_THRESHOLD:
        severity = 1.0 - (node.sve2_utilization_pct / SVE2_LOW_THRESHOLD)
        signals.append(
            AnomalySignal(
                node_id=node.node_id,
                anomaly_type="sve2_underutilization",
                severity=round(severity, 3),
                metric_value=node.sve2_utilization_pct,
                threshold=SVE2_LOW_THRESHOLD,
                suggested_action=ActionType.ARM_PERFORMIX_ANALYZE,
            )
        )

    if node.ttft_p99_ms > TTFT_HIGH_THRESHOLD:
        severity = min(
            (node.ttft_p99_ms - TTFT_HIGH_THRESHOLD) / TTFT_HIGH_THRESHOLD,
            1.0,
        )
        signals.append(
            AnomalySignal(
                node_id=node.node_id,
                anomaly_type="ttft_spike",
                severity=round(severity, 3),
                metric_value=node.ttft_p99_ms,
                threshold=TTFT_HIGH_THRESHOLD,
                suggested_action=ActionType.ADJUST_VLLM_CONFIG,
            )
        )

    if node.kv_eviction_rate > KV_EVICTION_HIGH:
        severity = min(
            (node.kv_eviction_rate - KV_EVICTION_HIGH) / KV_EVICTION_HIGH,
            1.0,
        )
        signals.append(
            AnomalySignal(
                node_id=node.node_id,
                anomaly_type="kv_eviction_flood",
                severity=round(severity, 3),
                metric_value=node.kv_eviction_rate,
                threshold=KV_EVICTION_HIGH,
                suggested_action=ActionType.TRIGGER_REQUANTIZE,
            )
        )

    return signals


def correlate_cross_node(
    nodes: Sequence[NodeSnapshot],
) -> list[AnomalySignal]:
    """Cross-node correlation: if ≥2 nodes share the same anomaly type,
    elevate severity and flag for cluster-wide action."""
    per_node: dict[str, list[AnomalySignal]] = {}
    for node in nodes:
        per_node[node.node_id] = detect_node_anomalies(node)

    # Flatten and group by anomaly type
    by_type: dict[str, list[AnomalySignal]] = {}
    for signals in per_node.values():
        for sig in signals:
            by_type.setdefault(sig.anomaly_type, []).append(sig)

    correlated: list[AnomalySignal] = []
    for anomaly_type, sigs in by_type.items():
        if len(sigs) >= 2:
            # Cluster-wide anomaly — elevate severity
            avg_severity = sum(s.severity for s in sigs) / len(sigs)
            for sig in sigs:
                elevated = AnomalySignal(
                    node_id=sig.node_id,
                    anomaly_type=f"correlated_{anomaly_type}",
                    severity=min(round(avg_severity * 1.5, 3), 1.0),
                    metric_value=sig.metric_value,
                    threshold=sig.threshold,
                    suggested_action=sig.suggested_action,
                )
                correlated.append(elevated)
        else:
            correlated.extend(sigs)

    return correlated


# ---------------------------------------------------------------------------
# S5.3 Quorum
# ---------------------------------------------------------------------------
def run_quorum(decision_id: str, votes: Sequence[Vote]) -> QuorumResult:
    """Run a 2-of-3 quorum vote and return the result."""
    result = QuorumResult(decision_id=decision_id, votes=list(votes))
    logger.info(
        "Quorum for %s: %d/%d approve → %s",
        decision_id,
        result.approvals,
        result.total,
        "PASSED" if result.passed else "REJECTED",
    )
    return result


# ---------------------------------------------------------------------------
# S5.4 Rolling restart
# ---------------------------------------------------------------------------
@dataclass
class RestartStep:
    node_id: str
    order: int
    status: str = "pending"  # pending | in_progress | completed | failed


def plan_rolling_restart(
    node_ids: Sequence[str] | None = None,
) -> list[RestartStep]:
    """Return the ordered restart plan following the node-002-first pattern.

    If *node_ids* is provided, only those nodes are included (preserving the
    canonical order).  Otherwise all three canonical nodes are used.
    """
    order = list(ROLLING_RESTART_ORDER)
    if node_ids is not None:
        order = [nid for nid in order if nid in node_ids]
    return [RestartStep(node_id=nid, order=idx) for idx, nid in enumerate(order)]


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------
class ClusterSentinelOrchestrator:
    """Central orchestrator that correlates telemetry across all nodes and
    produces healing decisions, potentially gated behind quorum votes.
    """

    def __init__(
        self,
        cluster_id: str = "cluster-graviton4",
    ) -> None:
        self.cluster_id = cluster_id
        self._decisions: list[SentinelDecision] = []
        self._quorum_results: list[QuorumResult] = []

    @property
    def decisions(self) -> list[SentinelDecision]:
        return list(self._decisions)

    @property
    def quorum_results(self) -> list[QuorumResult]:
        return list(self._quorum_results)

    def analyze(
        self,
        nodes: Sequence[NodeSnapshot],
        *,
        auto_quorum_votes: (dict[str, Sequence[Vote]] | None) = None,
    ) -> list[SentinelDecision]:
        """Analyze a set of node snapshots and produce decisions.

        If *auto_quorum_votes* is given, it maps decision IDs to pre-cast
        votes (useful in tests).  In production, votes arrive asynchronously.
        """
        signals = correlate_cross_node(nodes)
        decisions: list[SentinelDecision] = []
        is_correlated = any(s.anomaly_type.startswith("correlated_") for s in signals)

        for sig in signals:
            decision_id = f"dec-{uuid.uuid4().hex[:8]}"
            needs_quorum = is_correlated and sig.severity > 0.5
            decision = SentinelDecision(
                decision_id=decision_id,
                cluster_id=self.cluster_id,
                node_id=sig.node_id,
                timestamp=datetime.now(UTC),
                action=sig.suggested_action,
                confidence=round(1.0 - sig.severity * 0.3, 3),
                reasoning=(
                    f"Detected {sig.anomaly_type} on {sig.node_id}: "
                    f"{sig.metric_value} vs threshold {sig.threshold}"
                ),
                quorum_required=needs_quorum,
            )

            if needs_quorum:
                votes = auto_quorum_votes.get(decision_id, []) if auto_quorum_votes else []
                qr = run_quorum(decision_id, votes)
                self._quorum_results.append(qr)
                if not qr.passed:
                    logger.info("Decision %s rejected by quorum", decision_id)
                    continue

            decisions.append(decision)

        self._decisions.extend(decisions)
        return decisions

    def plan_restart(
        self,
        node_ids: Sequence[str] | None = None,
    ) -> list[RestartStep]:
        """Delegate to the rolling-restart planner."""
        return plan_rolling_restart(node_ids)

    def summary(self) -> dict[str, Any]:
        """Return a dict summarising orchestrator state."""
        return {
            "cluster_id": self.cluster_id,
            "total_decisions": len(self._decisions),
            "quorum_votes": len(self._quorum_results),
            "last_decision": (self._decisions[-1].decision_id if self._decisions else None),
        }
