from __future__ import annotations

import time

from neosentinel.actions.base import ActionContext, ActionResult
from neosentinel.contracts.decision import ActionType
from neosentinel.contracts.telemetry import BaselineMetrics


class RollbackOptimizationAction:
    action = ActionType.ROLLBACK_OPTIMIZATION

    def execute(self, context: ActionContext) -> ActionResult:
        started = time.perf_counter()
        if context.before_metrics is None:
            raise ValueError("ActionContext.before_metrics is required")
        before = context.before_metrics
        restored = context.parameters.get("restored_metrics")
        if restored is None:
            return ActionResult(
                action=self.action,
                node_id=context.node_id,
                success=False,
                message="No checkpoint metrics provided for rollback",
                before=before,
                after=before,
                duration_ms=int((time.perf_counter() - started) * 1000),
            )

        after = BaselineMetrics.model_validate(restored)
        elapsed = int((time.perf_counter() - started) * 1000)
        return ActionResult(
            action=self.action,
            node_id=context.node_id,
            success=True,
            message="Optimization rolled back to checkpoint",
            before=before,
            after=after,
            duration_ms=elapsed,
            config_delta=dict(context.parameters.get("restored_config", {})),
        )
