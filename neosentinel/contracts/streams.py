from dataclasses import dataclass
from typing import Literal

STREAM_PMU = "neosentinel:telemetry:pmu"
STREAM_VLLM = "neosentinel:telemetry:vllm"
STREAM_DECISIONS = "neosentinel:decisions"
STREAM_HEALING = "neosentinel:healing"

STREAM_RETENTION_MS = 86_400_000

CONSUMER_GROUPS = {
    STREAM_PMU: "neosentinel-pmu-consumers",
    STREAM_VLLM: "neosentinel-vllm-consumers",
    STREAM_DECISIONS: "neosentinel-decision-consumers",
    STREAM_HEALING: "neosentinel-healing-consumers",
}


@dataclass(frozen=True)
class StreamFieldSchema:
    name: str
    redis_type: Literal["string", "float", "int"]
    required: bool = True
    description: str = ""


PMU_STREAM_FIELDS: tuple[StreamFieldSchema, ...] = (
    StreamFieldSchema("node_id", "string", description="Node identifier, e.g. node-001"),
    StreamFieldSchema("timestamp", "string", description="ISO-8601 UTC timestamp"),
    StreamFieldSchema("sve2_utilization_pct", "float"),
    StreamFieldSchema("dram_bandwidth_pct", "float"),
    StreamFieldSchema("cache_miss_rate_pct", "float"),
    StreamFieldSchema("hotspots_json", "string", description="JSON array of top-5 hotspots"),
)

VLLM_STREAM_FIELDS: tuple[StreamFieldSchema, ...] = (
    StreamFieldSchema("node_id", "string"),
    StreamFieldSchema("timestamp", "string"),
    StreamFieldSchema("ttft_p99_ms", "float"),
    StreamFieldSchema("tokens_per_sec", "float"),
    StreamFieldSchema("kv_eviction_rate", "float"),
    StreamFieldSchema("requests_per_min", "float"),
)

DECISIONS_STREAM_FIELDS: tuple[StreamFieldSchema, ...] = (
    StreamFieldSchema("decision_id", "string"),
    StreamFieldSchema("cluster_id", "string"),
    StreamFieldSchema("node_id", "string"),
    StreamFieldSchema("timestamp", "string"),
    StreamFieldSchema("action", "string", description="ActionType enum value"),
    StreamFieldSchema("confidence", "float"),
    StreamFieldSchema("reasoning", "string"),
    StreamFieldSchema("parameters_json", "string", required=False),
    StreamFieldSchema("snapshot_hash", "string", required=False),
    StreamFieldSchema("quorum_required", "string", description="true or false"),
)

HEALING_STREAM_FIELDS: tuple[StreamFieldSchema, ...] = (
    StreamFieldSchema("healing_id", "string"),
    StreamFieldSchema("decision_id", "string"),
    StreamFieldSchema("node_id", "string"),
    StreamFieldSchema("timestamp", "string"),
    StreamFieldSchema("action", "string"),
    StreamFieldSchema("status", "string", description="success, failed, or rolled_back"),
    StreamFieldSchema("before_json", "string", description="BaselineMetrics JSON before heal"),
    StreamFieldSchema("after_json", "string", description="BaselineMetrics JSON after heal"),
    StreamFieldSchema("duration_ms", "int"),
    StreamFieldSchema("checkpoint_id", "string", required=False),
)

STREAM_FIELD_MAP: dict[str, tuple[StreamFieldSchema, ...]] = {
    STREAM_PMU: PMU_STREAM_FIELDS,
    STREAM_VLLM: VLLM_STREAM_FIELDS,
    STREAM_DECISIONS: DECISIONS_STREAM_FIELDS,
    STREAM_HEALING: HEALING_STREAM_FIELDS,
}

ALL_STREAMS = (STREAM_PMU, STREAM_VLLM, STREAM_DECISIONS, STREAM_HEALING)
