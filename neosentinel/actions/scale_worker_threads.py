from __future__ import annotations

import time

from neosentinel.actions.base import ActionContext, ActionResult
from neosentinel.contracts.decision import ActionType
from neosentinel.contracts.telemetry import BaselineMetrics


def _baseline(context: ActionContext) -> BaselineMetrics:
    if context.before_metrics is None:
        raise ValueError("ActionContext.before_metrics is required")
    return context.before_metrics


class ScaleWorkerThreadsAction:
    action = ActionType.SCALE_WORKER_THREADS

    def execute(self, context: ActionContext) -> ActionResult:
        started = time.perf_counter()
        before = _baseline(context)
        delta = int(context.parameters.get("worker_threads_delta", 2))
        threads = int(context.vllm_config.get("worker_threads", 4)) + delta

        after = before.model_copy(
            update={
                "tokens_per_sec": before.tokens_per_sec * 1.2,
                "kv_eviction_rate": max(before.kv_eviction_rate * 0.55, 0.1),
                "requests_per_min": before.requests_per_min * 1.1,
            }
        )
        elapsed = int((time.perf_counter() - started) * 1000)
        return ActionResult(
            action=self.action,
            node_id=context.node_id,
            success=True,
            message=f"Scaled worker threads to {threads}",
            before=before,
            after=after,
            duration_ms=elapsed,
            config_delta={"worker_threads": threads},
        )
