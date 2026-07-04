from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from neosentinel.actions.executor import ActionExecutor, HealOutcome
from neosentinel.agent.brain import AgentBrain, MockLlamaCppBackend
from neosentinel.agent.decision_tree import new_decision_id
from neosentinel.agent.snapshot import NODE_IDS, build_snapshot_from_redis
from neosentinel.audit.checkpoints import CheckpointStore
from neosentinel.audit.gitops import GitOpsAuditor
from neosentinel.audit.rollback import RollbackMonitor
from neosentinel.contracts.decision import ActionType, SentinelDecision
from neosentinel.contracts.telemetry import TelemetrySnapshot
from neosentinel.distributed.ray_tasks import LocalRayTaskDispatcher, RayTaskDispatcher
from neosentinel.distributed.streams import TelemetryPipeline
from neosentinel.orchestrator.correlation import CorrelationFinding, primary_finding
from neosentinel.orchestrator.quorum import QuorumResult, collect_votes
from neosentinel.orchestrator.restart import (
    ROLLING_RESTART_ORDER,
    execute_rolling_restart,
    plan_rolling_restart,
)


@dataclass
class OrchestratorCycleResult:
    snapshot: TelemetrySnapshot
    finding: CorrelationFinding
    decision: SentinelDecision
    quorum: QuorumResult | None
    ray_results: list[Any]
    heal_outcome: HealOutcome | None
    restart_order: tuple[str, ...]
    restarted_nodes: list[str]
    executed: bool


@dataclass
class ClusterSentinelOrchestrator:
    pipeline: TelemetryPipeline
    ray: RayTaskDispatcher = field(default_factory=LocalRayTaskDispatcher)
    executor: ActionExecutor | None = None
    brain: AgentBrain | None = None
    cluster_id: str = "cluster-graviton4"
    audit_root: Path | None = None
    checkpoint_root: Path | None = None
    stats: dict[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.executor is None:
            audit_path = self.audit_root or Path(".neosentinel/audit-repo")
            checkpoint_path = self.checkpoint_root or Path(".neosentinel/checkpoints")
            self.executor = ActionExecutor(
                pipeline=self.pipeline,
                checkpoints=CheckpointStore(checkpoint_path),
                gitops=GitOpsAuditor(audit_path),
                rollback=RollbackMonitor(),
            )
        if self.brain is None:
            self.brain = AgentBrain(
                MockLlamaCppBackend(simulate_cpu_ms=0.0),
                cluster_id=self.cluster_id,
            )

    def read_cluster_snapshot(self) -> TelemetrySnapshot | None:
        return build_snapshot_from_redis(
            self.pipeline._client,
            cluster_id=self.cluster_id,
            node_ids=NODE_IDS,
        )

    def correlate(self, snapshot: TelemetrySnapshot) -> CorrelationFinding:
        return primary_finding(snapshot)

    def run_cycle(
        self,
        *,
        force_execute: bool = False,
    ) -> OrchestratorCycleResult | None:
        snapshot = self.read_cluster_snapshot()
        if snapshot is None:
            self.stats["skipped"] = self.stats.get("skipped", 0) + 1
            return None

        finding = self.correlate(snapshot)
        decision = self.brain.decide(snapshot)

        quorum: QuorumResult | None = None
        if decision.quorum_required:
            quorum = collect_votes(
                snapshot,
                target_node_id=decision.node_id,
                proposed_action=decision.action,
            )

        ray_results = self.ray.dispatch_performix_recipes(
            NODE_IDS,
            recipe=str(decision.parameters.get("recipe", "code_hotspots")),
        )

        restart_plan = plan_rolling_restart()
        restarted_nodes: list[str] = []
        heal_outcome: HealOutcome | None = None
        executed = False

        should_execute = False
        if decision.action != ActionType.NOOP:
            if quorum is not None:
                should_execute = quorum.quorum_met
            else:
                should_execute = True
        if force_execute and decision.action != ActionType.NOOP:
            should_execute = True

        if should_execute and decision.action != ActionType.NOOP:
            target = next(node for node in snapshot.nodes if node.node_id == decision.node_id)
            config_delta = decision.parameters or {}
            if config_delta:
                self.ray.apply_remote_config(decision.node_id, dict(config_delta))

            if finding.cluster_wide or decision.quorum_required:
                restarted_nodes = execute_rolling_restart(
                    restart_plan,
                    restart_fn=lambda node_id: self.ray.apply_remote_config(
                        node_id,
                        {"rolling_restart": True},
                    ),
                )

            heal_outcome = self.executor.execute_decision(decision, target)
            executed = True
            self.stats["heals"] = self.stats.get("heals", 0) + 1
        elif decision.action != ActionType.NOOP:
            self.stats["blocked"] = self.stats.get("blocked", 0) + 1

        self.pipeline.publish_decision(decision)
        self.stats["cycles"] = self.stats.get("cycles", 0) + 1
        return OrchestratorCycleResult(
            snapshot=snapshot,
            finding=finding,
            decision=decision,
            quorum=quorum,
            ray_results=ray_results,
            heal_outcome=heal_outcome,
            restart_order=ROLLING_RESTART_ORDER,
            restarted_nodes=restarted_nodes,
            executed=executed,
        )

    def build_decision_from_finding(
        self,
        snapshot: TelemetrySnapshot,
        finding: CorrelationFinding,
    ) -> SentinelDecision:
        return SentinelDecision(
            decision_id=new_decision_id(),
            cluster_id=self.cluster_id,
            node_id=finding.target_node,
            timestamp=datetime.now(UTC),
            action=finding.recommended_action,
            confidence=0.9,
            reasoning=f"Cross-node correlation: {finding.pattern}",
            parameters={},
            quorum_required=finding.cluster_wide,
        )
