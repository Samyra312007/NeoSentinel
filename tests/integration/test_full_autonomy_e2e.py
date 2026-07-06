"""Full autonomous-loop end-to-end test (pre-Week-7 confidence check).

Drives the *entire* control loop the way a live Graviton4 cluster will:

    seed telemetry in Redis
      -> ClusterSentinelOrchestrator.run_cycle()
         -> assemble snapshot -> correlate -> agent decide
            -> quorum (if cluster-wide) -> Ray dispatch -> rolling restart
               -> checkpoint -> heal -> publish :healing -> GitOps commit
                  -> publish :decisions

Everything runs against fakeredis + a temp git repo, so a green run here is the
strongest offline signal that the Week-7 live wiring will behave.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import fakeredis
import pytest

from neosentinel.agent.snapshot import seed_node_telemetry
from neosentinel.contracts.decision import ActionType
from neosentinel.contracts.streams import STREAM_DECISIONS, STREAM_HEALING
from neosentinel.contracts.telemetry import NodeStatus
from neosentinel.distributed.streams import TelemetryPipeline
from neosentinel.orchestrator import ClusterSentinelOrchestrator

TS = datetime(2026, 7, 4, 12, 0, 0, tzinfo=UTC)


def _pipeline() -> tuple[TelemetryPipeline, fakeredis.FakeRedis]:
    client = fakeredis.FakeRedis(decode_responses=True)
    pipeline = TelemetryPipeline(client)
    pipeline.ensure_streams()
    return pipeline, client


def _seed_healthy(client, node_id: str) -> None:
    seed_node_telemetry(
        client,
        node_id=node_id,
        sve2_utilization_pct=80.0,
        dram_bandwidth_pct=55.0,
        cache_miss_rate_pct=12.0,
        ttft_p99_ms=120.0,
        tokens_per_sec=45.0,
        kv_eviction_rate=0.5,
        requests_per_min=350.0,
        timestamp=TS,
    )


def _seed_degraded_node002(client) -> None:
    seed_node_telemetry(
        client,
        node_id="node-002",
        sve2_utilization_pct=29.0,
        dram_bandwidth_pct=88.5,
        cache_miss_rate_pct=45.0,
        ttft_p99_ms=312.0,
        tokens_per_sec=18.4,
        kv_eviction_rate=4.2,
        requests_per_min=340.0,
        hotspots=[{"symbol": "unoptimized_gemm_kernel", "samples_pct": 72.5, "module": "vllm"}],
        timestamp=TS,
    )


def test_flagship_scenario_heals_end_to_end(tmp_path: Path) -> None:
    pipeline, client = _pipeline()
    _seed_healthy(client, "node-001")
    _seed_degraded_node002(client)
    _seed_healthy(client, "node-003")

    orch = ClusterSentinelOrchestrator(
        pipeline=pipeline,
        audit_root=tmp_path / "audit-repo",
        checkpoint_root=tmp_path / "checkpoints",
    )
    result = orch.run_cycle()

    assert result is not None
    # snapshot assembled from Redis with the right node health
    statuses = {n.node_id: n.status for n in result.snapshot.nodes}
    assert statuses["node-002"] in {NodeStatus.DEGRADED, NodeStatus.UNHEALTHY}

    # agent decided to requantize the offending node
    assert result.decision.action == ActionType.TRIGGER_REQUANTIZE
    assert result.decision.node_id == "node-002"

    # the heal actually executed and improved SVE2 to the target
    assert result.executed is True
    assert result.heal_outcome is not None
    assert result.heal_outcome.result.after.sve2_utilization_pct >= 79.0
    assert result.heal_outcome.result.after.ttft_p99_ms < 312.0

    # Ray fan-out dispatched a recipe per node
    assert len(result.ray_results) == 3

    # side effects landed on the streams and the audit trail
    assert client.xlen(STREAM_HEALING) >= 1
    assert client.xlen(STREAM_DECISIONS) >= 1
    audit_commits = list((tmp_path / "audit-repo" / "audit").glob("node-002/*.json"))
    assert audit_commits, "expected a GitOps audit record for the heal"


def test_healthy_cluster_takes_no_action(tmp_path: Path) -> None:
    pipeline, client = _pipeline()
    for nid in ("node-001", "node-002", "node-003"):
        _seed_healthy(client, nid)

    orch = ClusterSentinelOrchestrator(
        pipeline=pipeline,
        audit_root=tmp_path / "audit-repo",
        checkpoint_root=tmp_path / "checkpoints",
    )
    result = orch.run_cycle()

    assert result is not None
    assert result.decision.action == ActionType.NOOP
    assert result.executed is False
    assert result.heal_outcome is None
    # a noop decision is still recorded, but nothing heals
    assert client.xlen(STREAM_DECISIONS) >= 1


def test_no_telemetry_yields_no_cycle(tmp_path: Path) -> None:
    pipeline, _client = _pipeline()
    orch = ClusterSentinelOrchestrator(
        pipeline=pipeline,
        audit_root=tmp_path / "audit-repo",
        checkpoint_root=tmp_path / "checkpoints",
    )
    assert orch.run_cycle() is None
    assert orch.stats.get("skipped") == 1


def test_repeated_cycles_are_idempotent_in_health(tmp_path: Path) -> None:
    """After a heal, re-reading shows the offender recovered (no perpetual thrash)."""
    pipeline, client = _pipeline()
    _seed_healthy(client, "node-001")
    _seed_degraded_node002(client)
    _seed_healthy(client, "node-003")

    orch = ClusterSentinelOrchestrator(
        pipeline=pipeline,
        audit_root=tmp_path / "audit-repo",
        checkpoint_root=tmp_path / "checkpoints",
    )
    first = orch.run_cycle()
    assert first is not None and first.executed

    # Simulate the post-heal telemetry the pipeline would now observe.
    seed_node_telemetry(
        client,
        node_id="node-002",
        sve2_utilization_pct=79.0,
        dram_bandwidth_pct=56.0,
        cache_miss_rate_pct=14.0,
        ttft_p99_ms=131.0,
        tokens_per_sec=44.8,
        kv_eviction_rate=0.6,
        requests_per_min=340.0,
        timestamp=TS,
    )
    second = orch.run_cycle()
    assert second is not None
    assert second.decision.action == ActionType.NOOP
    assert second.executed is False


@pytest.mark.parametrize("cycles", [1, 3, 5])
def test_stats_accumulate_across_cycles(tmp_path: Path, cycles: int) -> None:
    pipeline, client = _pipeline()
    for nid in ("node-001", "node-002", "node-003"):
        _seed_healthy(client, nid)
    orch = ClusterSentinelOrchestrator(
        pipeline=pipeline,
        audit_root=tmp_path / "audit-repo",
        checkpoint_root=tmp_path / "checkpoints",
    )
    for _ in range(cycles):
        orch.run_cycle()
    assert orch.stats.get("cycles") == cycles
