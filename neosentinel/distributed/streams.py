from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

import redis
from redis.cluster import RedisCluster

from neosentinel.contracts.decision import SentinelDecision
from neosentinel.contracts.streams import (
    ALL_STREAMS,
    CONSUMER_GROUPS,
    STREAM_DECISIONS,
    STREAM_HEALING,
    STREAM_PMU,
    STREAM_RETENTION_MS,
    STREAM_VLLM,
)
from neosentinel.telemetry.performix import PmuFrame
from neosentinel.telemetry.vllm_scraper import VllmMetricsFrame

if TYPE_CHECKING:
    from neosentinel.actions.base import ActionResult

RedisClient = redis.Redis | RedisCluster


class TelemetryPipeline:
    def __init__(
        self,
        client: RedisClient,
        *,
        retention_ms: int = STREAM_RETENTION_MS,
    ) -> None:
        self._client = client
        self._retention_ms = retention_ms

    def _minid(self) -> str:
        cutoff_ms = int((time.time() * 1000) - self._retention_ms)
        return f"{cutoff_ms}-0"

    def ensure_streams(self) -> None:
        for stream in ALL_STREAMS:
            group = CONSUMER_GROUPS[stream]
            try:
                self._client.xgroup_create(stream, group, id="0", mkstream=True)
            except redis.ResponseError as exc:
                if "BUSYGROUP" not in str(exc):
                    raise

    def publish_pmu(self, frame: PmuFrame) -> str:
        frame.validate_stream_fields()
        return self._client.xadd(
            STREAM_PMU,
            frame.to_stream_fields(),
            minid=self._minid(),
            approximate=True,
        )

    def publish_vllm(self, frame: VllmMetricsFrame) -> str:
        frame.validate_stream_fields()
        return self._client.xadd(
            STREAM_VLLM,
            frame.to_stream_fields(),
            minid=self._minid(),
            approximate=True,
        )

    def publish_decision(self, decision: SentinelDecision) -> str:
        import json

        fields = {
            "decision_id": decision.decision_id,
            "cluster_id": decision.cluster_id,
            "node_id": decision.node_id,
            "timestamp": decision.timestamp.isoformat(),
            "action": decision.action.value,
            "confidence": str(decision.confidence),
            "reasoning": decision.reasoning,
            "parameters_json": json.dumps(decision.parameters, separators=(",", ":")),
            "snapshot_hash": decision.snapshot_hash,
            "quorum_required": "true" if decision.quorum_required else "false",
        }
        return self._client.xadd(
            STREAM_DECISIONS,
            fields,
            minid=self._minid(),
            approximate=True,
        )

    def read_decisions(self, *, count: int = 10) -> list[tuple[str, dict[str, str]]]:
        entries = self._client.xrevrange(STREAM_DECISIONS, "+", "-", count=count)
        return [(entry_id, dict(fields)) for entry_id, fields in entries]

    def publish_healing(
        self,
        *,
        decision_id: str,
        result: ActionResult,
        checkpoint_id: str,
        status: str,
    ) -> str:
        import json
        from datetime import UTC, datetime

        healing_id = f"heal-{datetime.now(UTC).strftime('%Y%m%d%H%M%S%f')}"
        fields = {
            "healing_id": healing_id,
            "decision_id": decision_id,
            "node_id": result.node_id,
            "timestamp": datetime.now(UTC).isoformat(),
            "action": result.action.value,
            "status": status,
            "before_json": json.dumps(result.before.model_dump(), separators=(",", ":")),
            "after_json": json.dumps(result.after.model_dump(), separators=(",", ":")),
            "duration_ms": str(result.duration_ms),
            "checkpoint_id": checkpoint_id,
        }
        self._client.xadd(
            STREAM_HEALING,
            fields,
            minid=self._minid(),
            approximate=True,
        )
        return healing_id

    def read_healing(self, *, count: int = 10) -> list[tuple[str, dict[str, str]]]:
        entries = self._client.xrevrange(STREAM_HEALING, "+", "-", count=count)
        return [(entry_id, dict(fields)) for entry_id, fields in entries]

    def publish_fields(self, stream: str, fields: dict[str, str]) -> str:
        return self._client.xadd(
            stream,
            fields,
            minid=self._minid(),
            approximate=True,
        )

    def read_group(
        self,
        stream: str,
        group: str,
        consumer: str,
        *,
        count: int = 10,
        block_ms: int | None = None,
    ) -> list[tuple[str, dict[str, str]]]:
        kwargs: dict[str, Any] = {stream: ">"}
        messages = self._client.xreadgroup(
            group,
            consumer,
            kwargs,
            count=count,
            block=block_ms,
        )
        if not messages:
            return []
        return [(entry_id, dict(fields)) for entry_id, fields in messages[0][1]]

    def read_pending(
        self,
        stream: str,
        group: str,
        consumer: str,
        *,
        count: int = 10,
    ) -> list[tuple[str, dict[str, str]]]:
        start_id = "0-0"
        collected: list[tuple[str, dict[str, str]]] = []
        while len(collected) < count:
            pending = self._client.xreadgroup(
                group,
                consumer,
                {stream: start_id},
                count=count - len(collected),
            )
            if not pending:
                break
            batch = pending[0][1]
            if not batch:
                break
            for entry_id, fields in batch:
                collected.append((entry_id, dict(fields)))
                start_id = entry_id
            if len(batch) < count - len(collected):
                break
        return collected

    def ack(self, stream: str, group: str, *message_ids: str) -> int:
        if not message_ids:
            return 0
        return int(self._client.xack(stream, group, *message_ids))

    def pending_count(self, stream: str, group: str) -> int:
        info = self._client.xpending(stream, group)
        return int(info["pending"])
