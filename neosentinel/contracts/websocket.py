from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field

from neosentinel.contracts.decision import ActionType
from neosentinel.contracts.telemetry import BaselineMetrics, HotspotEntry, NodeStatus


class WebSocketEventType(StrEnum):
    METRICS = "metrics"
    AGENT_THOUGHT = "agent_thought"
    HEALING = "healing"
    AUDIT = "audit"
    FLAME_GRAPH = "flame_graph"


class MetricsEvent(BaseModel):
    type: Literal[WebSocketEventType.METRICS] = WebSocketEventType.METRICS
    timestamp: datetime
    cluster_id: str
    nodes: list[dict]


class AgentThoughtEvent(BaseModel):
    type: Literal[WebSocketEventType.AGENT_THOUGHT] = WebSocketEventType.AGENT_THOUGHT
    timestamp: datetime
    decision_id: str
    node_id: str
    chunk: str
    done: bool = False


class HealingEvent(BaseModel):
    type: Literal[WebSocketEventType.HEALING] = WebSocketEventType.HEALING
    timestamp: datetime
    healing_id: str
    node_id: str
    action: ActionType
    status: Literal["success", "failed", "rolled_back"]
    before: BaselineMetrics
    after: BaselineMetrics
    duration_ms: int


class AuditEvent(BaseModel):
    type: Literal[WebSocketEventType.AUDIT] = WebSocketEventType.AUDIT
    timestamp: datetime
    commit_sha: str
    message: str
    node_id: str
    action: ActionType
    checkpoint_id: str


class FlameGraphEvent(BaseModel):
    type: Literal[WebSocketEventType.FLAME_GRAPH] = WebSocketEventType.FLAME_GRAPH
    timestamp: datetime
    node_id: str
    hotspots: list[HotspotEntry] = Field(max_length=5)


WebSocketEvent = Annotated[
    Union[MetricsEvent, AgentThoughtEvent, HealingEvent, AuditEvent, FlameGraphEvent],
    Field(discriminator="type"),
]

WS_NODE_STATUS_VALUES = frozenset(s.value for s in NodeStatus)
