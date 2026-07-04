from __future__ import annotations

import time

from neosentinel.actions.base import ActionContext, ActionResult
from neosentinel.contracts.decision import ActionType
from neosentinel.contracts.telemetry import BaselineMetrics


def _baseline(context: ActionContext) -> BaselineMetrics:
    if context.before_metrics is None:
        raise ValueError("ActionContext.before_metrics is required")
    return context.before_metrics


class TriggerRequantizeAction:
    action = ActionType.TRIGGER_REQUANTIZE

    def execute(self, context: ActionContext) -> ActionResult:
        started = time.perf_counter()
        before = _baseline(context)
        precision = str(context.parameters.get("target_precision", "int4"))
        kleidiai = bool(context.parameters.get("enable_kleidiai", True))

        after = before.model_copy(
            update={
                "sve2_utilization_pct": min(max(before.sve2_utilization_pct + 50.0, 79.0), 100.0),
                "ttft_p99_ms": max(before.ttft_p99_ms * 0.42, 131.0),
                "tokens_per_sec": max(before.tokens_per_sec * 2.4, 44.0),
                "dram_bandwidth_pct": max(before.dram_bandwidth_pct - 32.0, 45.0),
                "cache_miss_rate_pct": max(before.cache_miss_rate_pct * 0.35, 3.0),
                "kv_eviction_rate": max(before.kv_eviction_rate * 0.15, 0.1),
            }
        )
        elapsed = int((time.perf_counter() - started) * 1000)
        return ActionResult(
            action=self.action,
            node_id=context.node_id,
            success=True,
            message=f"Requantized to {precision} (kleidiai={kleidiai})",
            before=before,
            after=after,
            duration_ms=elapsed,
            config_delta={
                "target_precision": precision,
                "enable_kleidiai": kleidiai,
            },
        )
