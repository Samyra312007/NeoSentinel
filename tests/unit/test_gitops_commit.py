import json
from datetime import UTC, datetime
from pathlib import Path

from neosentinel.audit.gitops import GitOpsAuditor
from neosentinel.contracts.decision import ActionType, SentinelDecision
from neosentinel.contracts.telemetry import BaselineMetrics


def _decision() -> SentinelDecision:
    return SentinelDecision(
        decision_id="dec-gitops-001",
        cluster_id="cluster-graviton4",
        node_id="node-002",
        timestamp=datetime.now(UTC),
        action=ActionType.TRIGGER_REQUANTIZE,
        confidence=0.94,
        reasoning="SVE2 underutilization detected",
        parameters={"target_precision": "int4"},
    )


def _before() -> BaselineMetrics:
    return BaselineMetrics(
        ttft_p99_ms=312.0,
        tokens_per_sec=18.4,
        sve2_utilization_pct=29.0,
        dram_bandwidth_pct=88.5,
        cache_miss_rate_pct=45.0,
        kv_eviction_rate=4.2,
        requests_per_min=340.0,
    )


def _after() -> BaselineMetrics:
    return BaselineMetrics(
        ttft_p99_ms=131.0,
        tokens_per_sec=44.8,
        sve2_utilization_pct=79.0,
        dram_bandwidth_pct=56.0,
        cache_miss_rate_pct=14.0,
        kv_eviction_rate=0.6,
        requests_per_min=340.0,
    )


class TestGitOpsCommit:
    def test_commit_writes_audit_json(self, tmp_path: Path):
        auditor = GitOpsAuditor(tmp_path / "audit-repo")
        sha = auditor.commit_heal(
            decision=_decision(),
            before=_before(),
            after=_after(),
            checkpoint_id="chk-node-002-test",
        )
        assert len(sha) == 40
        audit_files = list((tmp_path / "audit-repo" / "audit" / "node-002").glob("*.json"))
        assert len(audit_files) == 1
        record = json.loads(audit_files[0].read_text(encoding="utf-8"))
        assert record["action"] == "trigger_requantize"
        assert record["before"]["sve2_utilization_pct"] == 29.0
        assert record["after"]["sve2_utilization_pct"] == 79.0
        assert auditor.repo.head.commit.hexsha == sha
