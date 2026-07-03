from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class ActionType(StrEnum):
    NOOP = "noop"
    ARM_PERFORMIX_ANALYZE = "arm_performix_analyze"
    ADJUST_VLLM_CONFIG = "adjust_vllm_config"
    SCALE_WORKER_THREADS = "scale_worker_threads"
    TRIGGER_REQUANTIZE = "trigger_requantize"
    SEND_ALERT = "send_alert"
    ROLLBACK_OPTIMIZATION = "rollback_optimization"


class SentinelDecision(BaseModel):
    decision_id: str
    cluster_id: str
    node_id: str = Field(pattern=r"^node-\d{3}$")
    timestamp: datetime
    action: ActionType
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    snapshot_hash: str = ""
    quorum_required: bool = False
