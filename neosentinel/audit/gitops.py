from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from git import Repo

from neosentinel.contracts.decision import SentinelDecision
from neosentinel.contracts.telemetry import BaselineMetrics


class GitOpsAuditor:
    def __init__(self, repo_path: Path) -> None:
        self.repo_path = repo_path
        self.repo_path.mkdir(parents=True, exist_ok=True)
        if not (self.repo_path / ".git").exists():
            self.repo = Repo.init(self.repo_path)
            readme = self.repo_path / "README.md"
            if not readme.exists():
                readme.write_text("# NeoSentinel GitOps Audit\n", encoding="utf-8")
            self.repo.index.add(["README.md"])
            self.repo.index.commit("Initial NeoSentinel audit repository")
        else:
            self.repo = Repo(self.repo_path)

    def commit_heal(
        self,
        *,
        decision: SentinelDecision,
        before: BaselineMetrics,
        after: BaselineMetrics,
        checkpoint_id: str,
    ) -> str:
        audit_dir = self.repo_path / "audit" / decision.node_id
        audit_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        record_path = audit_dir / f"{stamp}-{decision.action.value}.json"
        record = {
            "decision_id": decision.decision_id,
            "node_id": decision.node_id,
            "action": decision.action.value,
            "checkpoint_id": checkpoint_id,
            "timestamp": datetime.now(UTC).isoformat(),
            "before": before.model_dump(),
            "after": after.model_dump(),
            "reasoning": decision.reasoning,
        }
        record_path.write_text(json.dumps(record, indent=2), encoding="utf-8")

        rel_path = str(record_path.relative_to(self.repo_path))
        self.repo.index.add([rel_path])
        commit = self.repo.index.commit(
            f"Auto-heal: applied {decision.action.value} on {decision.node_id} "
            f"(SVE2 {before.sve2_utilization_pct:.0f}% -> {after.sve2_utilization_pct:.0f}%)"
        )
        return commit.hexsha
