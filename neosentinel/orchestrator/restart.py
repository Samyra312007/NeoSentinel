from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

ROLLING_RESTART_ORDER: tuple[str, ...] = ("node-002", "node-003", "node-001")


class RestartPhase(StrEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"
    SKIPPED = "skipped"


@dataclass
class RestartStep:
    node_id: str
    order: int
    phase: RestartPhase


@dataclass
class RollingRestartPlan:
    steps: list[RestartStep]
    completed: list[str]

    @property
    def order(self) -> tuple[str, ...]:
        return tuple(step.node_id for step in self.steps)

    def next_node(self) -> str | None:
        for step in self.steps:
            if step.phase == RestartPhase.PENDING:
                return step.node_id
        return None

    def mark_complete(self, node_id: str) -> None:
        self.completed.append(node_id)
        for step in self.steps:
            if step.node_id == node_id:
                step.phase = RestartPhase.COMPLETE

    def advance(self) -> RestartStep | None:
        for step in self.steps:
            if step.phase == RestartPhase.PENDING:
                step.phase = RestartPhase.IN_PROGRESS
                return step
        return None

    @property
    def is_complete(self) -> bool:
        return all(step.phase == RestartPhase.COMPLETE for step in self.steps)


def plan_rolling_restart(
    *,
    node_ids: tuple[str, ...] = ROLLING_RESTART_ORDER,
) -> RollingRestartPlan:
    steps = [
        RestartStep(node_id=node_id, order=index + 1, phase=RestartPhase.PENDING)
        for index, node_id in enumerate(node_ids)
    ]
    return RollingRestartPlan(steps=steps, completed=[])


def execute_rolling_restart(
    plan: RollingRestartPlan,
    *,
    restart_fn,
) -> list[str]:
    restarted: list[str] = []
    while not plan.is_complete:
        step = plan.advance()
        if step is None:
            break
        restart_fn(step.node_id)
        plan.mark_complete(step.node_id)
        restarted.append(step.node_id)
    return restarted
