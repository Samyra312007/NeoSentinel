from __future__ import annotations

import time
from collections.abc import Callable

from neosentinel.actions.base import ActionContext, ActionResult
from neosentinel.contracts.decision import ActionType

AlertHandler = Callable[[str, str, dict], None]


class SendAlertAction:
    action = ActionType.SEND_ALERT

    def __init__(self, *, handler: AlertHandler | None = None) -> None:
        self._handler = handler
        self.alerts: list[tuple[str, str, dict]] = []

    def execute(self, context: ActionContext) -> ActionResult:
        started = time.perf_counter()
        if context.before_metrics is None:
            raise ValueError("ActionContext.before_metrics is required")
        before = context.before_metrics
        severity = str(context.parameters.get("severity", "warning"))
        message = str(context.parameters.get("message", "NeoSentinel cluster alert"))
        payload = {
            "severity": severity,
            "message": message,
            "node_id": context.node_id,
            "metrics": before.model_dump(),
        }
        self.alerts.append((context.node_id, severity, payload))
        if self._handler:
            self._handler(context.node_id, severity, payload)

        elapsed = int((time.perf_counter() - started) * 1000)
        return ActionResult(
            action=self.action,
            node_id=context.node_id,
            success=True,
            message=f"Alert sent ({severity})",
            before=before,
            after=before,
            duration_ms=elapsed,
            config_delta=payload,
        )
