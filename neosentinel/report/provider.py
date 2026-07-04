from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import redis
from redis.cluster import RedisCluster

from neosentinel.agent.snapshot import build_snapshot_from_redis
from neosentinel.audit.checkpoints import CheckpointStore
from neosentinel.contracts.decision import ActionType
from neosentinel.contracts.telemetry import TelemetrySnapshot
from neosentinel.distributed.streams import TelemetryPipeline

RedisClient = redis.Redis | RedisCluster


@dataclass
class DecisionSummary:
    decision_id: str
    node_id: str
    timestamp: datetime
    action: ActionType
    confidence: float
    reasoning: str
    quorum_required: bool


@dataclass
class HealingSummary:
    healing_id: str
    decision_id: str
    node_id: str
    timestamp: datetime
    action: ActionType
    status: str
    duration_ms: int
    checkpoint_id: str
    before: dict[str, Any]
    after: dict[str, Any]


@dataclass
class CheckpointSummary:
    checkpoint_id: str
    decision_id: str
    node_id: str
    action: ActionType
    created_at: datetime


@dataclass
class ClusterReportData:
    generated_at: datetime
    cluster_id: str
    snapshot: TelemetrySnapshot | None
    decisions: list[DecisionSummary] = field(default_factory=list)
    healing_events: list[HealingSummary] = field(default_factory=list)
    checkpoints: list[CheckpointSummary] = field(default_factory=list)
    healthy_node_count: int = 0
    degraded_node_count: int = 0
    unhealthy_node_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at.isoformat(),
            "cluster_id": self.cluster_id,
            "snapshot": self.snapshot.model_dump(mode="json") if self.snapshot else None,
            "decisions": [
                {
                    "decision_id": item.decision_id,
                    "node_id": item.node_id,
                    "timestamp": item.timestamp.isoformat(),
                    "action": item.action.value,
                    "confidence": item.confidence,
                    "reasoning": item.reasoning,
                    "quorum_required": item.quorum_required,
                }
                for item in self.decisions
            ],
            "healing_events": [
                {
                    "healing_id": item.healing_id,
                    "decision_id": item.decision_id,
                    "node_id": item.node_id,
                    "timestamp": item.timestamp.isoformat(),
                    "action": item.action.value,
                    "status": item.status,
                    "duration_ms": item.duration_ms,
                    "checkpoint_id": item.checkpoint_id,
                    "before": item.before,
                    "after": item.after,
                }
                for item in self.healing_events
            ],
            "checkpoints": [
                {
                    "checkpoint_id": item.checkpoint_id,
                    "decision_id": item.decision_id,
                    "node_id": item.node_id,
                    "action": item.action.value,
                    "created_at": item.created_at.isoformat(),
                }
                for item in self.checkpoints
            ],
            "healthy_node_count": self.healthy_node_count,
            "degraded_node_count": self.degraded_node_count,
            "unhealthy_node_count": self.unhealthy_node_count,
        }


class ReportDataProvider:
    def __init__(
        self,
        client: RedisClient,
        *,
        cluster_id: str = "cluster-graviton4",
        checkpoint_root: Path | None = None,
    ) -> None:
        self._client = client
        self._cluster_id = cluster_id
        self._pipeline = TelemetryPipeline(client)
        self._checkpoints = CheckpointStore(checkpoint_root)

    def collect(
        self,
        *,
        decision_count: int = 50,
        healing_count: int = 50,
    ) -> ClusterReportData:
        snapshot = build_snapshot_from_redis(self._client, cluster_id=self._cluster_id)
        decisions = self._load_decisions(decision_count)
        healing = self._load_healing(healing_count)
        checkpoints = self._load_checkpoints()

        healthy = degraded = unhealthy = 0
        if snapshot is not None:
            from neosentinel.contracts.telemetry import NodeStatus

            for node in snapshot.nodes:
                if node.status == NodeStatus.HEALTHY:
                    healthy += 1
                elif node.status == NodeStatus.DEGRADED:
                    degraded += 1
                elif node.status == NodeStatus.UNHEALTHY:
                    unhealthy += 1

        return ClusterReportData(
            generated_at=datetime.now(UTC),
            cluster_id=self._cluster_id,
            snapshot=snapshot,
            decisions=decisions,
            healing_events=healing,
            checkpoints=checkpoints,
            healthy_node_count=healthy,
            degraded_node_count=degraded,
            unhealthy_node_count=unhealthy,
        )

    def _load_decisions(self, count: int) -> list[DecisionSummary]:
        items: list[DecisionSummary] = []
        for _entry_id, fields in self._pipeline.read_decisions(count=count):
            items.append(
                DecisionSummary(
                    decision_id=fields["decision_id"],
                    node_id=fields["node_id"],
                    timestamp=datetime.fromisoformat(fields["timestamp"]),
                    action=ActionType(fields["action"]),
                    confidence=float(fields["confidence"]),
                    reasoning=fields["reasoning"],
                    quorum_required=fields.get("quorum_required", "false") == "true",
                )
            )
        return items

    def _load_healing(self, count: int) -> list[HealingSummary]:
        items: list[HealingSummary] = []
        for _entry_id, fields in self._pipeline.read_healing(count=count):
            items.append(
                HealingSummary(
                    healing_id=fields["healing_id"],
                    decision_id=fields["decision_id"],
                    node_id=fields["node_id"],
                    timestamp=datetime.fromisoformat(fields["timestamp"]),
                    action=ActionType(fields["action"]),
                    status=fields["status"],
                    duration_ms=int(fields["duration_ms"]),
                    checkpoint_id=fields["checkpoint_id"],
                    before=json.loads(fields["before_json"]),
                    after=json.loads(fields["after_json"]),
                )
            )
        return items

    def _load_checkpoints(self) -> list[CheckpointSummary]:
        root = self._checkpoints._root
        if not root.exists():
            return []
        items: list[CheckpointSummary] = []
        for path in sorted(root.glob("chk-*.json")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            items.append(
                CheckpointSummary(
                    checkpoint_id=payload["checkpoint_id"],
                    decision_id=payload["decision_id"],
                    node_id=payload["node_id"],
                    action=ActionType(payload["action"]),
                    created_at=datetime.fromisoformat(payload["created_at"]),
                )
            )
        return items
