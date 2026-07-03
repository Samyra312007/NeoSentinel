from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class NodeStatus(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class HotspotEntry(BaseModel):
    symbol: str
    samples_pct: float = Field(ge=0.0, le=100.0)
    module: str = ""


class BaselineMetrics(BaseModel):
    ttft_p99_ms: float = Field(ge=0.0)
    tokens_per_sec: float = Field(ge=0.0)
    sve2_utilization_pct: float = Field(ge=0.0, le=100.0)
    dram_bandwidth_pct: float = Field(ge=0.0, le=100.0)
    cache_miss_rate_pct: float = Field(ge=0.0, le=100.0)
    kv_eviction_rate: float = Field(ge=0.0)
    requests_per_min: float = Field(ge=0.0)


class NodeSnapshot(BaseModel):
    node_id: str = Field(pattern=r"^node-\d{3}$")
    status: NodeStatus
    timestamp: datetime
    ttft_p99_ms: float = Field(ge=0.0)
    tokens_per_sec: float = Field(ge=0.0)
    sve2_utilization_pct: float = Field(ge=0.0, le=100.0)
    dram_bandwidth_pct: float = Field(ge=0.0, le=100.0)
    cache_miss_rate_pct: float = Field(ge=0.0, le=100.0)
    kv_eviction_rate: float = Field(ge=0.0)
    requests_per_min: float = Field(ge=0.0)
    hotspots: list[HotspotEntry] = Field(default_factory=list, max_length=5)


class TelemetrySnapshot(BaseModel):
    cluster_id: str
    timestamp: datetime
    nodes: list[NodeSnapshot] = Field(min_length=1, max_length=3)
    baseline: BaselineMetrics | None = None
