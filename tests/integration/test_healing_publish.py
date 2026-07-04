import json
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
        decision_id="dec-heal-001",
        cluster_id="cluster-graviton4",
        node_id="node-002",
        timestamp=datetime.now(UTC),
        action=ActionType.TRIGGER_REQUANTIZE,
        confidence=0.94,
        reasoning="SVE2 underutilization",
        parameters={"target_precision": "int4"},
    )


def _node() -> NodeSnapshot:
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


class TestHealingPublish:
    def test_healing_stream_contains_before_after_metrics(self, tmp_path: Path):
        client = fakeredis.FakeRedis(decode_responses=True)
        pipeline = TelemetryPipeline(client)
        pipeline.ensure_streams()

        executor = ActionExecutor(
            pipeline=pipeline,
            checkpoints=CheckpointStore(tmp_path / "checkpoints"),
            gitops=GitOpsAuditor(tmp_path / "audit-repo"),
            rollback=RollbackMonitor(),
        )

        outcome = executor.execute_decision(_decision(), _node())
        assert outcome.healing_id.startswith("heal-")
        assert client.xlen(STREAM_HEALING) == 1

        _entry_id, fields = pipeline.read_healing(count=1)[0]
        before = json.loads(fields["before_json"])
        after = json.loads(fields["after_json"])
        assert fields["action"] == "trigger_requantize"
        assert fields["status"] == "success"
        assert fields["checkpoint_id"] == outcome.checkpoint_id
        assert before["sve2_utilization_pct"] == 29.0
        assert after["sve2_utilization_pct"] >= 79.0
        assert int(fields["duration_ms"]) >= 0

    def test_commit_sha_recorded_on_heal(self, tmp_path: Path):
        client = fakeredis.FakeRedis(decode_responses=True)
        pipeline = TelemetryPipeline(client)
        pipeline.ensure_streams()

        executor = ActionExecutor(
            pipeline=pipeline,
            checkpoints=CheckpointStore(tmp_path / "checkpoints"),
            gitops=GitOpsAuditor(tmp_path / "audit-repo"),
            rollback=RollbackMonitor(),
        )

        outcome = executor.execute_decision(_decision(), _node())
        assert outcome.commit_sha is not None
        assert len(outcome.commit_sha) == 40
