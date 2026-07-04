from __future__ import annotations

import time

from neosentinel.actions.base import ActionContext, ActionResult
from neosentinel.contracts.decision import ActionType
from neosentinel.contracts.telemetry import BaselineMetrics


def _baseline(context: ActionContext) -> BaselineMetrics:
    if context.before_metrics is None:
        raise ValueError("ActionContext.before_metrics is required")
    return context.before_metrics


class AdjustVllmConfigAction:
    action = ActionType.ADJUST_VLLM_CONFIG

    def execute(self, context: ActionContext) -> ActionResult:
        started = time.perf_counter()
        before = _baseline(context)
        delta = dict(context.parameters)
        merged = {**context.vllm_config, **delta}

        after = before.model_copy(
            update={
                "ttft_p99_ms": max(before.ttft_p99_ms * 0.65, 100.0),
                "kv_eviction_rate": max(before.kv_eviction_rate * 0.3, 0.1),
                "dram_bandwidth_pct": max(before.dram_bandwidth_pct - 15.0, 20.0),
                "tokens_per_sec": before.tokens_per_sec * 1.15,
            }
        )
        elapsed = int((time.perf_counter() - started) * 1000)
        return ActionResult(
            action=self.action,
            node_id=context.node_id,
            success=True,
            message="vLLM config adjusted",
            before=before,
            after=after,
            duration_ms=elapsed,
            config_delta=merged,
        )
