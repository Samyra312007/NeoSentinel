from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from neosentinel.agent.decision_tree import derive_node_status
from neosentinel.agent.snapshot import NODE_IDS
from neosentinel.contracts.streams import (
    STREAM_DECISIONS,
    STREAM_HEALING,
    STREAM_PMU,
    STREAM_VLLM,
)
from neosentinel.contracts.telemetry import HotspotEntry, NodeSnapshot, NodeStatus

STREAM_EVENT_MAP = {
    STREAM_PMU: "pmu",
    STREAM_VLLM: "vllm",
    STREAM_DECISIONS: "decision",
    STREAM_HEALING: "healing",
}


@dataclass
class RedisStreamAdapter:
    cluster_id: str = "cluster-graviton4"
    node_ids: tuple[str, ...] = NODE_IDS
    _pmu: dict[str, dict[str, str]] = field(default_factory=dict)
    _vllm: dict[str, dict[str, str]] = field(default_factory=dict)
    _seen_decisions: set[str] = field(default_factory=set)
    _seen_healing: set[str] = field(default_factory=set)

    def ingest(self, stream_name: str, fields: dict[str, str]) -> list[dict[str, Any]]:
        kind = STREAM_EVENT_MAP.get(stream_name)
        if kind == "pmu":
            node_id = fields.get("node_id", "")
            if node_id:
                self._pmu[node_id] = dict(fields)
            metrics = self._build_metrics_event()
            flame = self._build_flame_graph_event(node_id, fields) if node_id else None
            events: list[dict[str, Any]] = []
            if metrics:
                events.append(metrics)
            if flame:
                events.append(flame)
            return events
        if kind == "vllm":
            node_id = fields.get("node_id", "")
            if node_id:
                self._vllm[node_id] = dict(fields)
            metrics = self._build_metrics_event()
            return [metrics] if metrics else []
        if kind == "decision":
            decision_id = fields.get("decision_id", "")
            if not decision_id or decision_id in self._seen_decisions:
                return []
            self._seen_decisions.add(decision_id)
            return [self._decision_to_agent_thought(fields)]
        if kind == "healing":
            healing_id = fields.get("healing_id", "")
            if not healing_id or healing_id in self._seen_healing:
                return []
            self._seen_healing.add(healing_id)
            events = [self._healing_to_event(fields)]
            audit = self._healing_to_audit(fields)
            if audit:
                events.append(audit)
            return events
        return []

    def _build_node_dict(self, node_id: str) -> dict[str, Any] | None:
        pmu = self._pmu.get(node_id)
        vllm = self._vllm.get(node_id)
        if pmu is None and vllm is None:
            return None

        sve2 = dram = cache_miss = 0.0
        hotspots: list[dict[str, Any]] = []
        ttft = tokens = kv_eviction = requests = 0.0
        timestamp = ""

        if pmu:
            timestamp = pmu.get("timestamp", timestamp)
            sve2 = float(pmu.get("sve2_utilization_pct", 0))
            dram = float(pmu.get("dram_bandwidth_pct", 0))
            cache_miss = float(pmu.get("cache_miss_rate_pct", 0))
            hotspots = json.loads(pmu.get("hotspots_json", "[]"))

        if vllm:
            if not timestamp:
                timestamp = vllm.get("timestamp", "")
            ttft = float(vllm.get("ttft_p99_ms", 0))
            tokens = float(vllm.get("tokens_per_sec", 0))
            kv_eviction = float(vllm.get("kv_eviction_rate", 0))
            requests = float(vllm.get("requests_per_min", 0))

        ts = datetime.now(UTC)
        if timestamp:
            ts = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))

        hotspot_entries = [HotspotEntry.model_validate(item) for item in hotspots[:5]]
        node = NodeSnapshot(
            node_id=node_id,
            status=NodeStatus.UNKNOWN,
            timestamp=ts,
            ttft_p99_ms=ttft,
            tokens_per_sec=tokens,
            sve2_utilization_pct=sve2,
            dram_bandwidth_pct=dram,
            cache_miss_rate_pct=cache_miss,
            kv_eviction_rate=kv_eviction,
            requests_per_min=requests,
            hotspots=hotspot_entries,
        )
        status = derive_node_status(node)
        return {
            "node_id": node_id,
            "status": status.value,
            "timestamp": timestamp,
            "ttft_p99_ms": ttft,
            "tokens_per_sec": tokens,
            "sve2_utilization_pct": sve2,
            "dram_bandwidth_pct": dram,
            "cache_miss_rate_pct": cache_miss,
            "kv_eviction_rate": kv_eviction,
            "requests_per_min": requests,
            "hotspots": [h.model_dump() if hasattr(h, "model_dump") else h for h in node.hotspots],
        }

    def _build_metrics_event(self) -> dict[str, Any] | None:
        nodes: list[dict[str, Any]] = []
        latest_ts = ""
        for node_id in self.node_ids:
            node_dict = self._build_node_dict(node_id)
            if node_dict:
                nodes.append(node_dict)
                if node_dict.get("timestamp"):
                    latest_ts = str(node_dict["timestamp"])
        if not nodes:
            return None
        return {
            "type": "metrics",
            "timestamp": latest_ts or "1970-01-01T00:00:00+00:00",
            "cluster_id": self.cluster_id,
            "nodes": nodes,
        }

    def _build_flame_graph_event(
        self,
        node_id: str,
        fields: dict[str, str],
    ) -> dict[str, Any] | None:
        raw = fields.get("hotspots_json", "[]")
        hotspots = json.loads(raw)
        if not hotspots:
            return None
        return {
            "type": "flame_graph",
            "timestamp": fields.get("timestamp", ""),
            "node_id": node_id,
            "hotspots": hotspots[:5],
        }

    def _decision_to_agent_thought(self, fields: dict[str, str]) -> dict[str, Any]:
        return {
            "type": "agent_thought",
            "timestamp": fields.get("timestamp", ""),
            "decision_id": fields.get("decision_id", ""),
            "node_id": fields.get("node_id", ""),
            "chunk": fields.get("reasoning", ""),
            "done": True,
        }

    def _healing_to_event(self, fields: dict[str, str]) -> dict[str, Any]:
        before = json.loads(fields.get("before_json", "{}"))
        after = json.loads(fields.get("after_json", "{}"))
        return {
            "type": "healing",
            "timestamp": fields.get("timestamp", ""),
            "healing_id": fields.get("healing_id", ""),
            "node_id": fields.get("node_id", ""),
            "action": fields.get("action", ""),
            "status": fields.get("status", "success"),
            "before": before,
            "after": after,
            "duration_ms": int(fields.get("duration_ms", "0")),
        }

    def _healing_to_audit(self, fields: dict[str, str]) -> dict[str, Any] | None:
        if fields.get("status") != "success":
            return None
        checkpoint_id = fields.get("checkpoint_id", "")
        if not checkpoint_id:
            return None
        commit_sha = hashlib.sha1(checkpoint_id.encode()).hexdigest()
        action = fields.get("action", "")
        node_id = fields.get("node_id", "")
        return {
            "type": "audit",
            "timestamp": fields.get("timestamp", ""),
            "commit_sha": commit_sha,
            "message": f"Auto-heal: applied {action} on {node_id}",
            "node_id": node_id,
            "action": action,
            "checkpoint_id": checkpoint_id,
        }
