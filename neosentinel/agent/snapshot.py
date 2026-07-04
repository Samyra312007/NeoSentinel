from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

import redis
from redis.cluster import RedisCluster

from neosentinel.agent.decision_tree import derive_node_status
from neosentinel.contracts.streams import STREAM_PMU, STREAM_VLLM
from neosentinel.contracts.telemetry import (
    HotspotEntry,
    NodeSnapshot,
    NodeStatus,
    TelemetrySnapshot,
)

RedisClient = redis.Redis | RedisCluster

NODE_IDS = ("node-001", "node-002", "node-003")


def _parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _latest_stream_entry(
    client: RedisClient,
    stream: str,
    node_id: str,
    *,
    scan_count: int = 50,
) -> dict[str, str] | None:
    entries = client.xrevrange(stream, "+", "-", count=scan_count)
    for _entry_id, fields in entries:
        if fields.get("node_id") == node_id:
            return dict(fields)
    return None


def _build_node_snapshot(
    node_id: str,
    pmu: dict[str, str] | None,
    vllm: dict[str, str] | None,
) -> NodeSnapshot | None:
    if pmu is None and vllm is None:
        return None

    timestamp = datetime.now(UTC)
    sve2 = dram = cache_miss = 0.0
    hotspots: list[HotspotEntry] = []
    ttft = tokens = kv_eviction = requests = 0.0

    if pmu:
        timestamp = _parse_timestamp(pmu["timestamp"])
        sve2 = float(pmu["sve2_utilization_pct"])
        dram = float(pmu["dram_bandwidth_pct"])
        cache_miss = float(pmu["cache_miss_rate_pct"])
        raw_hotspots = json.loads(pmu.get("hotspots_json", "[]"))
        hotspots = [HotspotEntry.model_validate(item) for item in raw_hotspots[:5]]

    if vllm:
        vllm_ts = _parse_timestamp(vllm["timestamp"])
        if pmu is None:
            timestamp = vllm_ts
        ttft = float(vllm["ttft_p99_ms"])
        tokens = float(vllm["tokens_per_sec"])
        kv_eviction = float(vllm["kv_eviction_rate"])
        requests = float(vllm["requests_per_min"])

    node = NodeSnapshot(
        node_id=node_id,
        status=NodeStatus.UNKNOWN,
        timestamp=timestamp,
        ttft_p99_ms=ttft,
        tokens_per_sec=tokens,
        sve2_utilization_pct=sve2,
        dram_bandwidth_pct=dram,
        cache_miss_rate_pct=cache_miss,
        kv_eviction_rate=kv_eviction,
        requests_per_min=requests,
        hotspots=hotspots,
    )
    return node.model_copy(update={"status": derive_node_status(node)})


def build_snapshot_from_redis(
    client: RedisClient,
    *,
    cluster_id: str = "cluster-graviton4",
    node_ids: tuple[str, ...] = NODE_IDS,
) -> TelemetrySnapshot | None:
    nodes: list[NodeSnapshot] = []
    for node_id in node_ids:
        pmu = _latest_stream_entry(client, STREAM_PMU, node_id)
        vllm = _latest_stream_entry(client, STREAM_VLLM, node_id)
        node = _build_node_snapshot(node_id, pmu, vllm)
        if node is not None:
            nodes.append(node)
    if not nodes:
        return None
    return TelemetrySnapshot(
        cluster_id=cluster_id,
        timestamp=max(node.timestamp for node in nodes),
        nodes=nodes,
    )


def seed_node_telemetry(
    client: RedisClient,
    *,
    node_id: str,
    sve2_utilization_pct: float,
    dram_bandwidth_pct: float,
    cache_miss_rate_pct: float,
    ttft_p99_ms: float,
    tokens_per_sec: float,
    kv_eviction_rate: float,
    requests_per_min: float,
    hotspots: list[dict[str, Any]] | None = None,
    timestamp: datetime | None = None,
) -> tuple[str, str]:
    ts = (timestamp or datetime.now(UTC)).isoformat()
    pmu_id = client.xadd(
        STREAM_PMU,
        {
            "node_id": node_id,
            "timestamp": ts,
            "sve2_utilization_pct": str(sve2_utilization_pct),
            "dram_bandwidth_pct": str(dram_bandwidth_pct),
            "cache_miss_rate_pct": str(cache_miss_rate_pct),
            "hotspots_json": json.dumps(hotspots or [], separators=(",", ":")),
        },
    )
    vllm_id = client.xadd(
        STREAM_VLLM,
        {
            "node_id": node_id,
            "timestamp": ts,
            "ttft_p99_ms": str(ttft_p99_ms),
            "tokens_per_sec": str(tokens_per_sec),
            "kv_eviction_rate": str(kv_eviction_rate),
            "requests_per_min": str(requests_per_min),
        },
    )
    return pmu_id, vllm_id
