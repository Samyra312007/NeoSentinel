from __future__ import annotations

import signal
import time
from pathlib import Path

from neosentinel.agent.snapshot import NODE_IDS, seed_node_telemetry
from neosentinel.cli.config import load_local_config
from neosentinel.distributed.pipeline import TelemetryIngestionPipeline
from neosentinel.distributed.redis_client import create_redis_client
from neosentinel.distributed.streams import TelemetryPipeline
from neosentinel.orchestrator.cluster import ClusterSentinelOrchestrator
from neosentinel.simulation.catalog import get_scenario
from neosentinel.telemetry.mock_performix import MockPerformix
from neosentinel.telemetry.performix import PerformixDaemon
from neosentinel.telemetry.vllm_scraper import VllmMetricsScraper


def _redis_client():
    config = load_local_config()
    return create_redis_client(
        url=config.redis_url,
        cluster=config.redis_cluster,
        decode_responses=True,
    )


def run_pipeline_daemon(node_id: str, *, duration_s: float | None = None) -> None:
    config = load_local_config()
    client = _redis_client()
    pipeline = TelemetryPipeline(client)
    pipeline.ensure_streams()

    import shutil

    pmu_source = (
        PerformixDaemon(node_id=node_id)
        if shutil.which("apx")
        else MockPerformix(node_id, seed=hash(node_id) % 1000)
    )
    if isinstance(pmu_source, MockPerformix) and node_id == "node-001":
        pmu_source = MockPerformix(node_id, seed=1)
    if isinstance(pmu_source, MockPerformix) and node_id == "node-002":
        pmu_source = MockPerformix(node_id, seed=2)
    if isinstance(pmu_source, MockPerformix) and node_id == "node-003":
        pmu_source = MockPerformix(node_id, seed=3)

    ingestion = TelemetryIngestionPipeline(
        pipeline,
        pmu_source,
        VllmMetricsScraper(config.vllm_base_url, node_id),
    )

    if duration_s is not None:
        ingestion.run_for(duration_s)
        return

    stop = False

    def _handle_stop(_signum, _frame) -> None:
        nonlocal stop
        stop = True

    signal.signal(signal.SIGINT, _handle_stop)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _handle_stop)

    while not stop:
        ingestion.tick()
        time.sleep(ingestion._pmu_interval_s)


def run_orchestrator_daemon(*, interval_s: float | None = None) -> None:
    config = load_local_config()
    client = _redis_client()
    pipeline = TelemetryPipeline(client)
    pipeline.ensure_streams()
    orchestrator = ClusterSentinelOrchestrator(
        pipeline=pipeline,
        cluster_id=config.cluster_id,
        audit_root=Path(".neosentinel/audit-repo"),
        checkpoint_root=Path(".neosentinel/checkpoints"),
    )
    tick = interval_s if interval_s is not None else config.orchestrator_interval_s

    stop = False

    def _handle_stop(_signum, _frame) -> None:
        nonlocal stop
        stop = True

    signal.signal(signal.SIGINT, _handle_stop)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _handle_stop)

    while not stop:
        orchestrator.run_cycle()
        time.sleep(tick)


def seed_healthy_cluster() -> None:
    client = _redis_client()
    pipeline = TelemetryPipeline(client)
    pipeline.ensure_streams()
    for node_id in NODE_IDS:
        seed = 1 if node_id == "node-001" else 2 if node_id == "node-002" else 3
        mock = MockPerformix(node_id, seed=seed)
        frame = mock.generate_frame()
        from neosentinel.telemetry.vllm_scraper import VllmMetricsFrame

        vllm = VllmMetricsScraper("http://127.0.0.1:8000", node_id)
        try:
            vllm_frame = vllm.scrape_once()
        except Exception:
            vllm_frame = VllmMetricsFrame(
                node_id=node_id,
                timestamp=frame.timestamp,
                ttft_p99_ms=120.0,
                tokens_per_sec=45.0,
                kv_eviction_rate=0.5,
                requests_per_min=350.0,
            )
        pipeline.publish_pmu(frame)
        pipeline.publish_vllm(vllm_frame)


def inject_live_anomaly(node_id: str, anomaly_type: str) -> dict[str, object]:
    scenario = get_scenario(anomaly_type)
    client = _redis_client()
    pipeline = TelemetryPipeline(client)
    pipeline.ensure_streams()

    for nid in NODE_IDS:
        if nid == node_id:
            continue
        seed_node_telemetry(
            client,
            node_id=nid,
            sve2_utilization_pct=82.0 if nid == "node-001" else 80.5,
            dram_bandwidth_pct=55.0,
            cache_miss_rate_pct=12.0,
            ttft_p99_ms=120.0 if nid == "node-001" else 118.0,
            tokens_per_sec=45.0 if nid == "node-001" else 46.0,
            kv_eviction_rate=0.5,
            requests_per_min=350.0,
        )

    hotspots = [
        {
            "symbol": "unoptimized_gemm_kernel",
            "samples_pct": 72.5,
            "module": "vllm_engine",
        }
    ]
    seed_node_telemetry(
        client,
        node_id=node_id,
        sve2_utilization_pct=scenario.initial_sve2_pct,
        dram_bandwidth_pct=88.5,
        cache_miss_rate_pct=45.0,
        ttft_p99_ms=scenario.initial_ttft_ms,
        tokens_per_sec=18.4,
        kv_eviction_rate=4.2,
        requests_per_min=340.0,
        hotspots=hotspots if node_id == scenario.target_node else None,
    )
    return {
        "status": "injected",
        "node_id": node_id,
        "anomaly_type": anomaly_type,
        "mode": "live",
        "sve2_utilization_pct": scenario.initial_sve2_pct,
        "ttft_p99_ms": scenario.initial_ttft_ms,
    }
