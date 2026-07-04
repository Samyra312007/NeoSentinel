from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from neosentinel.contracts.decision import ActionType
from neosentinel.contracts.telemetry import BaselineMetrics


@dataclass(frozen=True)
class Checkpoint:
    checkpoint_id: str
    decision_id: str
    node_id: str
    action: ActionType
    created_at: datetime
    metrics: BaselineMetrics
    vllm_config: dict[str, Any]
    parameters: dict[str, Any]


class CheckpointStore:
    def __init__(self, root: Path | None = None) -> None:
        self._root = root or Path(".neosentinel/checkpoints")
        self._root.mkdir(parents=True, exist_ok=True)
        self._memory: dict[str, Checkpoint] = {}

    def _checkpoint_path(self, checkpoint_id: str) -> Path:
        return self._root / f"{checkpoint_id}.json"

    @staticmethod
    def _new_id(node_id: str) -> str:
        ts = datetime.now(UTC).strftime("%Y%m%d%H%M%S%f")
        return f"chk-{node_id}-{ts}"

    def create(
        self,
        *,
        decision_id: str,
        node_id: str,
        action: ActionType,
        metrics: BaselineMetrics,
        vllm_config: dict[str, Any],
        parameters: dict[str, Any],
    ) -> Checkpoint:
        checkpoint = Checkpoint(
            checkpoint_id=self._new_id(node_id),
            decision_id=decision_id,
            node_id=node_id,
            action=action,
            created_at=datetime.now(UTC),
            metrics=metrics,
            vllm_config=vllm_config,
            parameters=parameters,
        )
        self._memory[checkpoint.checkpoint_id] = checkpoint
        payload = {
            "checkpoint_id": checkpoint.checkpoint_id,
            "decision_id": checkpoint.decision_id,
            "node_id": checkpoint.node_id,
            "action": checkpoint.action.value,
            "created_at": checkpoint.created_at.isoformat(),
            "metrics": checkpoint.metrics.model_dump(),
            "vllm_config": checkpoint.vllm_config,
            "parameters": checkpoint.parameters,
        }
        self._checkpoint_path(checkpoint.checkpoint_id).write_text(
            json.dumps(payload, indent=2),
            encoding="utf-8",
        )
        return checkpoint

    def get(self, checkpoint_id: str) -> Checkpoint:
        if checkpoint_id in self._memory:
            return self._memory[checkpoint_id]
        path = self._checkpoint_path(checkpoint_id)
        if not path.exists():
            raise KeyError(f"Checkpoint not found: {checkpoint_id}")
        payload = json.loads(path.read_text(encoding="utf-8"))
        checkpoint = Checkpoint(
            checkpoint_id=payload["checkpoint_id"],
            decision_id=payload["decision_id"],
            node_id=payload["node_id"],
            action=ActionType(payload["action"]),
            created_at=datetime.fromisoformat(payload["created_at"]),
            metrics=BaselineMetrics.model_validate(payload["metrics"]),
            vllm_config=payload["vllm_config"],
            parameters=payload["parameters"],
        )
        self._memory[checkpoint_id] = checkpoint
        return checkpoint

    def restore(self, checkpoint_id: str) -> Checkpoint:
        return self.get(checkpoint_id)
