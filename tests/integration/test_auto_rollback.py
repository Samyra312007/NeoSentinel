from datetime import UTC, datetime
from pathlib import Path

import fakeredis

from neosentinel.actions.executor import ActionExecutor
from neosentinel.audit.checkpoints import CheckpointStore
from neosentinel.audit.gitops import GitOpsAuditor
from neosentinel.audit.rollback import RollbackMonitor
from neosentinel.contracts.decision import ActionType, SentinelDecision
from neosentinel.contracts.streams import STREAM_HEALING
from neosentinel.contracts.telemetry import NodeSnapshot, NodeStatus
from neosentinel.distributed.streams import TelemetryPipeline


def _decision() -> SentinelDecision:
    return SentinelDecision(
        decision_id="dec-rollback-001",
        cluster_id="cluster-graviton4",
        node_id="node-002",
        timestamp=datetime.now(UTC),
        action=ActionType.TRIGGER_REQUANTIZE,
        confidence=0.94,
        reasoning="SVE2 underutilization",
        parameters={"target_precision": "int4", "enable_kleidiai": True},
        quorum_required=True,
    )


def _degraded_node() -> NodeSnapshot:
    return NodeSnapshot(
        node_id="node-002",
        status=NodeStatus.DEGRADED,
        timestamp=datetime.now(UTC),
        ttft_p99_ms=312.0,
        tokens_per_sec=18.4,
        sve2_utilization_pct=29.0,
        dram_bandwidth_pct=88.5,
        cache_miss_rate_pct=45.0,
        kv_eviction_rate=4.2,
        requests_per_min=340.0,
        hotspots=[],
    )


class TestAutoRollback:
    def test_rollback_when_metrics_worsen_within_90s(self, tmp_path: Path):
        client = fakeredis.FakeRedis(decode_responses=True)
        pipeline = TelemetryPipeline(client)
        pipeline.ensure_streams()

        executor = ActionExecutor(
            pipeline=pipeline,
            checkpoints=CheckpointStore(tmp_path / "checkpoints"),
            gitops=GitOpsAuditor(tmp_path / "audit-repo"),
            rollback=RollbackMonitor(window_s=90.0),
        )

        outcome = executor.execute_decision(
            _decision(),
            _degraded_node(),
            simulate_worsening=True,
        )

        assert outcome.rolled_back is True
        assert outcome.result.action == ActionType.ROLLBACK_OPTIMIZATION
        assert outcome.result.after.sve2_utilization_pct == 29.0

        healing_entries = pipeline.read_healing(count=5)
        statuses = [fields["status"] for _id, fields in healing_entries]
        assert "success" in statuses
        assert "rolled_back" in statuses

    def test_no_rollback_when_metrics_improve(self, tmp_path: Path):
        client = fakeredis.FakeRedis(decode_responses=True)
        pipeline = TelemetryPipeline(client)
        pipeline.ensure_streams()

        executor = ActionExecutor(
            pipeline=pipeline,
            checkpoints=CheckpointStore(tmp_path / "checkpoints"),
            gitops=GitOpsAuditor(tmp_path / "audit-repo"),
            rollback=RollbackMonitor(window_s=90.0),
        )

        outcome = executor.execute_decision(
            _decision(),
            _degraded_node(),
            simulate_worsening=False,
        )

        assert outcome.rolled_back is False
        assert outcome.result.action == ActionType.TRIGGER_REQUANTIZE
        assert outcome.result.after.sve2_utilization_pct >= 79.0
        assert client.xlen(STREAM_HEALING) == 1
