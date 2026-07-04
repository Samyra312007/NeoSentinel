from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from neosentinel.actions.adjust_vllm_config import AdjustVllmConfigAction
from neosentinel.actions.arm_performix_analyze import ArmPerformixAnalyzeAction
from neosentinel.actions.base import ActionContext, ActionResult
from neosentinel.actions.rollback_optimization import RollbackOptimizationAction
from neosentinel.actions.scale_worker_threads import ScaleWorkerThreadsAction
from neosentinel.actions.send_alert import SendAlertAction
from neosentinel.actions.trigger_requantize import TriggerRequantizeAction
from neosentinel.audit.checkpoints import CheckpointStore
from neosentinel.audit.gitops import GitOpsAuditor
from neosentinel.audit.rollback import RollbackMonitor
from neosentinel.contracts.decision import ActionType, SentinelDecision
from neosentinel.contracts.telemetry import BaselineMetrics, NodeSnapshot
from neosentinel.distributed.streams import TelemetryPipeline


@dataclass
class HealOutcome:
    result: ActionResult
    checkpoint_id: str
    commit_sha: str | None
    healing_id: str
    rolled_back: bool = False


@dataclass
class ActionExecutor:
    pipeline: TelemetryPipeline
    checkpoints: CheckpointStore
    gitops: GitOpsAuditor
    rollback: RollbackMonitor
    vllm_configs: dict[str, dict[str, Any]] = field(default_factory=dict)
    _tools: dict[ActionType, Any] = field(default_factory=dict, init=False, repr=False)

    def __post_init__(self) -> None:
        self._tools = {
            ActionType.ARM_PERFORMIX_ANALYZE: ArmPerformixAnalyzeAction(),
            ActionType.ADJUST_VLLM_CONFIG: AdjustVllmConfigAction(),
            ActionType.SCALE_WORKER_THREADS: ScaleWorkerThreadsAction(),
            ActionType.TRIGGER_REQUANTIZE: TriggerRequantizeAction(),
            ActionType.SEND_ALERT: SendAlertAction(),
            ActionType.ROLLBACK_OPTIMIZATION: RollbackOptimizationAction(),
        }

    def _node_metrics(self, node: NodeSnapshot) -> BaselineMetrics:
        return BaselineMetrics(
            ttft_p99_ms=node.ttft_p99_ms,
            tokens_per_sec=node.tokens_per_sec,
            sve2_utilization_pct=node.sve2_utilization_pct,
            dram_bandwidth_pct=node.dram_bandwidth_pct,
            cache_miss_rate_pct=node.cache_miss_rate_pct,
            kv_eviction_rate=node.kv_eviction_rate,
            requests_per_min=node.requests_per_min,
        )

    def execute_decision(
        self,
        decision: SentinelDecision,
        node: NodeSnapshot,
        *,
        simulate_worsening: bool = False,
    ) -> HealOutcome:
        before = self._node_metrics(node)
        checkpoint = self.checkpoints.create(
            decision_id=decision.decision_id,
            node_id=decision.node_id,
            action=decision.action,
            metrics=before,
            vllm_config=dict(self.vllm_configs.get(decision.node_id, {})),
            parameters=decision.parameters,
        )

        if decision.action == ActionType.NOOP:
            result = ActionResult(
                action=decision.action,
                node_id=decision.node_id,
                success=True,
                message="No action required",
                before=before,
                after=before,
                duration_ms=0,
            )
            healing_id = self.pipeline.publish_healing(
                decision_id=decision.decision_id,
                result=result,
                checkpoint_id=checkpoint.checkpoint_id,
                status="success",
            )
            return HealOutcome(
                result=result,
                checkpoint_id=checkpoint.checkpoint_id,
                commit_sha=None,
                healing_id=healing_id,
            )

        tool = self._tools[decision.action]
        context = ActionContext(
            node_id=decision.node_id,
            parameters=decision.parameters,
            before_metrics=before,
            vllm_config=self.vllm_configs.setdefault(decision.node_id, {}),
        )
        result = tool.execute(context)
        if result.config_delta:
            self.vllm_configs[decision.node_id].update(result.config_delta)

        commit_sha = self.gitops.commit_heal(
            decision=decision,
            before=before,
            after=result.after,
            checkpoint_id=checkpoint.checkpoint_id,
        )

        healing_id = self.pipeline.publish_healing(
            decision_id=decision.decision_id,
            result=result,
            checkpoint_id=checkpoint.checkpoint_id,
            status="success" if result.success else "failed",
        )

        rolled_back = False
        if simulate_worsening and result.success:
            worsened = result.after.model_copy(
                update={
                    "ttft_p99_ms": result.after.ttft_p99_ms * 1.3,
                    "sve2_utilization_pct": max(result.after.sve2_utilization_pct - 25.0, 5.0),
                    "tokens_per_sec": result.after.tokens_per_sec * 0.7,
                }
            )
            if self.rollback.should_rollback(result.after, worsened, elapsed_s=30.0):
                restored = self.checkpoints.restore(checkpoint.checkpoint_id)
                rollback_context = ActionContext(
                    node_id=decision.node_id,
                    parameters={
                        "restored_metrics": restored.metrics.model_dump(),
                        "restored_config": restored.vllm_config,
                    },
                    before_metrics=worsened,
                )
                rollback_result = self._tools[ActionType.ROLLBACK_OPTIMIZATION].execute(
                    rollback_context
                )
                self.vllm_configs[decision.node_id] = dict(restored.vllm_config)
                self.pipeline.publish_healing(
                    decision_id=decision.decision_id,
                    result=rollback_result,
                    checkpoint_id=checkpoint.checkpoint_id,
                    status="rolled_back",
                )
                result = rollback_result
                rolled_back = True

        return HealOutcome(
            result=result,
            checkpoint_id=checkpoint.checkpoint_id,
            commit_sha=commit_sha,
            healing_id=healing_id,
            rolled_back=rolled_back,
        )
