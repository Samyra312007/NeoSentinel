from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

from neosentinel.contracts.streams import STREAM_PMU
from neosentinel.distributed.streams import TelemetryPipeline

TARGET_EVENTS_PER_SEC = 3000.0


@dataclass(frozen=True)
class LoadBenchmarkResult:
    events_published: int
    duration_s: float
    events_per_sec: float

    @property
    def met_target(self) -> bool:
        return self.events_per_sec >= TARGET_EVENTS_PER_SEC


def _precompute_pmu_fields(
    node_ids: tuple[str, ...],
    count: int,
) -> list[dict[str, str]]:
    fields: list[dict[str, str]] = []
    for i in range(count):
        node_id = node_ids[i % len(node_ids)]
        fields.append(
            {
                "node_id": node_id,
                "timestamp": "2026-07-04T10:00:00+00:00",
                "sve2_utilization_pct": "79.0",
                "dram_bandwidth_pct": "45.0",
                "cache_miss_rate_pct": "3.2",
                "hotspots_json": "[]",
            }
        )
    return fields


def _publish_precomputed(
    pipeline: TelemetryPipeline,
    batch: list[dict[str, str]],
    *,
    minid: str | None = None,
) -> int:
    client = pipeline._client
    for fields in batch:
        if minid is None:
            client.xadd(STREAM_PMU, fields)
        else:
            client.xadd(STREAM_PMU, fields, minid=minid, approximate=True)
    return len(batch)


def run_stream_load_benchmark(
    pipeline: TelemetryPipeline,
    *,
    target_events: int = 3000,
    workers: int = 1,
    node_ids: tuple[str, ...] = ("node-001", "node-002", "node-003"),
    use_retention_trim: bool = True,
) -> LoadBenchmarkResult:
    pipeline.ensure_streams()
    payloads = _precompute_pmu_fields(node_ids, target_events)
    minid = pipeline._minid() if use_retention_trim else None

    started = time.perf_counter()
    if workers <= 1:
        total = _publish_precomputed(pipeline, payloads, minid=minid)
    else:
        per_worker = target_events // workers
        remainder = target_events % workers
        batches: list[list[dict[str, str]]] = []
        offset = 0
        for i in range(workers):
            size = per_worker + (1 if i < remainder else 0)
            if size > 0:
                batches.append(payloads[offset : offset + size])
                offset += size
        total = 0
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [
                pool.submit(_publish_precomputed, pipeline, batch, minid=minid)
                for batch in batches
            ]
            for future in as_completed(futures):
                total += future.result()
    elapsed = time.perf_counter() - started
    rate = total / elapsed if elapsed > 0 else 0.0
    return LoadBenchmarkResult(
        events_published=total,
        duration_s=elapsed,
        events_per_sec=rate,
    )
