from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from neosentinel.contracts.decision import ActionType
from neosentinel.contracts.telemetry import BaselineMetrics


@dataclass
class ActionContext:
    node_id: str
    parameters: dict[str, Any] = field(default_factory=dict)
    before_metrics: BaselineMetrics | None = None
    vllm_config: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ActionResult:
    action: ActionType
    node_id: str
    success: bool
    message: str
    before: BaselineMetrics
    after: BaselineMetrics
    duration_ms: int
    config_delta: dict[str, Any] = field(default_factory=dict)


class ActionTool(Protocol):
    action: ActionType

    def execute(self, context: ActionContext) -> ActionResult: ...
