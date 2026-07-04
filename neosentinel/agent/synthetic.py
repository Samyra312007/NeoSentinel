from __future__ import annotations

import random
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from neosentinel.agent.snapshot import NODE_IDS
from neosentinel.contracts.telemetry import NodeSnapshot, NodeStatus, TelemetrySnapshot

SYNTHETIC_INTERVAL_S = 30.0
SYNTHETIC_72HR_TICKS = int((72 * 3600) / SYNTHETIC_INTERVAL_S)


@dataclass(frozen=True)
class HealthyEnvelope:
    sve2_min: float = 58.0
    sve2_max: float = 88.0
    ttft_min: float = 110.0
    ttft_max: float = 210.0
    dram_min: float = 32.0
    dram_max: float = 72.0
    cache_miss_min: float = 1.5
    cache_miss_max: float = 12.0
    kv_eviction_min: float = 0.05
    kv_eviction_max: float = 1.8
    tokens_per_sec: float = 842.0
    requests_per_min: float = 400.0


DEFAULT_HEALTHY_ENVELOPE = HealthyEnvelope()


class HealthyTelemetryGenerator:
    def __init__(
        self,
        *,
        envelope: HealthyEnvelope = DEFAULT_HEALTHY_ENVELOPE,
        seed: int | None = None,
        cluster_id: str = "cluster-graviton4",
    ) -> None:
        self.envelope = envelope
        self.cluster_id = cluster_id
        self._rng = random.Random(seed)

    def _jitter(self, low: float, high: float) -> float:
        return round(self._rng.uniform(low, high), 2)

    def generate_node(self, node_id: str, timestamp: datetime) -> NodeSnapshot:
        env = self.envelope
        return NodeSnapshot(
            node_id=node_id,
            status=NodeStatus.HEALTHY,
            timestamp=timestamp,
            ttft_p99_ms=self._jitter(env.ttft_min, env.ttft_max),
            tokens_per_sec=env.tokens_per_sec,
            sve2_utilization_pct=self._jitter(env.sve2_min, env.sve2_max),
            dram_bandwidth_pct=self._jitter(env.dram_min, env.dram_max),
            cache_miss_rate_pct=self._jitter(env.cache_miss_min, env.cache_miss_max),
            kv_eviction_rate=self._jitter(env.kv_eviction_min, env.kv_eviction_max),
            requests_per_min=env.requests_per_min,
            hotspots=[],
        )

    def generate_snapshot(self, timestamp: datetime | None = None) -> TelemetrySnapshot:
        ts = timestamp or datetime.now(UTC)
        nodes = [self.generate_node(node_id, ts) for node_id in NODE_IDS]
        return TelemetrySnapshot(
            cluster_id=self.cluster_id,
            timestamp=ts,
            nodes=nodes,
        )

    def stream_72hr(
        self,
        *,
        ticks: int = SYNTHETIC_72HR_TICKS,
        interval_s: float = SYNTHETIC_INTERVAL_S,
        start: datetime | None = None,
    ) -> Iterator[TelemetrySnapshot]:
        base = start or datetime.now(UTC)
        for tick in range(ticks):
            ts = base + timedelta(seconds=tick * interval_s)
            yield self.generate_snapshot(ts)
