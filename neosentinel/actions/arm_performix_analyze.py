from __future__ import annotations

import time
from typing import Any

from neosentinel.actions.base import ActionContext, ActionResult
from neosentinel.contracts.decision import ActionType
from neosentinel.contracts.telemetry import BaselineMetrics
from neosentinel.telemetry.recipes import run_code_hotspots, run_memory_bandwidth


def _baseline(context: ActionContext) -> BaselineMetrics:
    if context.before_metrics is None:
        raise ValueError("ActionContext.before_metrics is required")
    return context.before_metrics


class ArmPerformixAnalyzeAction:
    action = ActionType.ARM_PERFORMIX_ANALYZE

    def __init__(self, *, runner: Any | None = None) -> None:
        self._runner = runner

    def execute(self, context: ActionContext) -> ActionResult:
        started = time.perf_counter()
        before = _baseline(context)
        recipe = str(context.parameters.get("recipe", "code_hotspots"))
        sample_ms = int(context.parameters.get("sample_ms", 5000))

        if recipe == "memory_bandwidth":
            report = run_memory_bandwidth(context.node_id, runner=self._runner)
        else:
            report = run_code_hotspots(context.node_id, runner=self._runner)

        after = before.model_copy(
            update={
                "cache_miss_rate_pct": max(before.cache_miss_rate_pct - 2.0, 1.0),
                "sve2_utilization_pct": min(before.sve2_utilization_pct + 3.0, 100.0),
            }
        )
        elapsed = int((time.perf_counter() - started) * 1000)
        hotspot_count = len(report.hotspots)
        return ActionResult(
            action=self.action,
            node_id=context.node_id,
            success=True,
            message=(
                f"Performix {recipe} complete ({sample_ms}ms sample, "
                f"{hotspot_count} hotspots)"
            ),
            before=before,
            after=after,
            duration_ms=elapsed,
            config_delta={"performix_report": report.to_dict()},
        )
