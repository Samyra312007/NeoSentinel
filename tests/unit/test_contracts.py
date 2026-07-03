from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml
from pydantic import TypeAdapter, ValidationError

from neosentinel.contracts import CONTRACT_VERSION
from neosentinel.contracts.decision import ActionType, SentinelDecision
from neosentinel.contracts.streams import (
    ALL_STREAMS,
    CONSUMER_GROUPS,
    DECISIONS_STREAM_FIELDS,
    HEALING_STREAM_FIELDS,
    PMU_STREAM_FIELDS,
    STREAM_DECISIONS,
    STREAM_FIELD_MAP,
    STREAM_HEALING,
    STREAM_PMU,
    STREAM_RETENTION_MS,
    STREAM_VLLM,
    VLLM_STREAM_FIELDS,
)
from neosentinel.contracts.telemetry import (
    BaselineMetrics,
    HotspotEntry,
    NodeSnapshot,
    NodeStatus,
    TelemetrySnapshot,
)
from neosentinel.contracts.websocket import (
    AgentThoughtEvent,
    AuditEvent,
    FlameGraphEvent,
    HealingEvent,
    MetricsEvent,
    WebSocketEventType,
)


def _baseline() -> BaselineMetrics:
    return BaselineMetrics(
        ttft_p99_ms=131.0,
        tokens_per_sec=842.0,
        sve2_utilization_pct=79.0,
        dram_bandwidth_pct=45.0,
        cache_miss_rate_pct=3.2,
        kv_eviction_rate=0.1,
        requests_per_min=1200.0,
    )


def _node(node_id: str = "node-001") -> NodeSnapshot:
    return NodeSnapshot(
        node_id=node_id,
        status=NodeStatus.HEALTHY,
        timestamp=datetime.now(UTC),
        ttft_p99_ms=131.0,
        tokens_per_sec=842.0,
        sve2_utilization_pct=79.0,
        dram_bandwidth_pct=45.0,
        cache_miss_rate_pct=3.2,
        kv_eviction_rate=0.1,
        requests_per_min=400.0,
        hotspots=[HotspotEntry(symbol="gemm_kernel", samples_pct=42.0, module="vllm")],
    )


class TestContractVersion:
    def test_version_is_semver(self):
        parts = CONTRACT_VERSION.split(".")
        assert len(parts) == 3
        assert all(p.isdigit() for p in parts)


class TestTelemetryContract:
    def test_valid_snapshot(self):
        snap = TelemetrySnapshot(
            cluster_id="demo-cluster",
            timestamp=datetime.now(UTC),
            nodes=[_node("node-001"), _node("node-002"), _node("node-003")],
            baseline=_baseline(),
        )
        assert len(snap.nodes) == 3

    def test_invalid_node_id_rejected(self):
        with pytest.raises(ValidationError):
            _node("bad-node")

    def test_hotspots_max_five(self):
        hotspots = [HotspotEntry(symbol=f"fn{i}", samples_pct=float(i)) for i in range(6)]
        with pytest.raises(ValidationError):
            NodeSnapshot(
                node_id="node-001",
                status=NodeStatus.HEALTHY,
                timestamp=datetime.now(UTC),
                ttft_p99_ms=100.0,
                tokens_per_sec=500.0,
                sve2_utilization_pct=50.0,
                dram_bandwidth_pct=30.0,
                cache_miss_rate_pct=2.0,
                kv_eviction_rate=0.0,
                requests_per_min=100.0,
                hotspots=hotspots,
            )


class TestDecisionContract:
    def test_action_type_has_seven_values(self):
        assert len(ActionType) == 7

    def test_all_action_types_present(self):
        expected = {
            "noop",
            "arm_performix_analyze",
            "adjust_vllm_config",
            "scale_worker_threads",
            "trigger_requantize",
            "send_alert",
            "rollback_optimization",
        }
        assert {a.value for a in ActionType} == expected

    def test_valid_decision(self):
        d = SentinelDecision(
            decision_id="dec-001",
            cluster_id="demo-cluster",
            node_id="node-002",
            timestamp=datetime.now(UTC),
            action=ActionType.ADJUST_VLLM_CONFIG,
            confidence=0.92,
            reasoning="SVE2 underutilization detected; adjusting batch size.",
            parameters={"max_num_seqs": 256},
        )
        assert d.action == ActionType.ADJUST_VLLM_CONFIG

    def test_confidence_bounds(self):
        with pytest.raises(ValidationError):
            SentinelDecision(
                decision_id="dec-002",
                cluster_id="demo-cluster",
                node_id="node-001",
                timestamp=datetime.now(UTC),
                action=ActionType.NOOP,
                confidence=1.5,
                reasoning="invalid",
            )


class TestStreamsContract:
    def test_four_streams_defined(self):
        assert len(ALL_STREAMS) == 4
        assert STREAM_PMU == "neosentinel:telemetry:pmu"
        assert STREAM_VLLM == "neosentinel:telemetry:vllm"
        assert STREAM_DECISIONS == "neosentinel:decisions"
        assert STREAM_HEALING == "neosentinel:healing"

    def test_consumer_group_per_stream(self):
        for stream in ALL_STREAMS:
            assert stream in CONSUMER_GROUPS
            assert CONSUMER_GROUPS[stream].startswith("neosentinel-")

    def test_retention_is_24_hours(self):
        assert STREAM_RETENTION_MS == 86_400_000

    def test_field_schemas_complete(self):
        assert len(PMU_STREAM_FIELDS) >= 5
        assert len(VLLM_STREAM_FIELDS) >= 5
        assert len(DECISIONS_STREAM_FIELDS) >= 8
        assert len(HEALING_STREAM_FIELDS) >= 9
        assert set(STREAM_FIELD_MAP.keys()) == set(ALL_STREAMS)

    def test_required_pmu_fields(self):
        required = {f.name for f in PMU_STREAM_FIELDS if f.required}
        assert "node_id" in required
        assert "sve2_utilization_pct" in required


class TestWebSocketContract:
    def test_five_event_types(self):
        assert len(WebSocketEventType) == 5
        assert WebSocketEventType.METRICS.value == "metrics"
        assert WebSocketEventType.AGENT_THOUGHT.value == "agent_thought"
        assert WebSocketEventType.HEALING.value == "healing"
        assert WebSocketEventType.AUDIT.value == "audit"
        assert WebSocketEventType.FLAME_GRAPH.value == "flame_graph"

    def test_metrics_event(self):
        evt = MetricsEvent(
            timestamp=datetime.now(UTC),
            cluster_id="demo-cluster",
            nodes=[{"node_id": "node-001", "status": "healthy"}],
        )
        assert evt.type == WebSocketEventType.METRICS

    def test_agent_thought_event(self):
        evt = AgentThoughtEvent(
            timestamp=datetime.now(UTC),
            decision_id="dec-001",
            node_id="node-002",
            chunk="Analyzing SVE2 counters...",
            done=False,
        )
        assert evt.chunk.startswith("Analyzing")

    def test_healing_event(self):
        baseline = _baseline()
        evt = HealingEvent(
            timestamp=datetime.now(UTC),
            healing_id="heal-001",
            node_id="node-002",
            action=ActionType.ADJUST_VLLM_CONFIG,
            status="success",
            before=BaselineMetrics(
                ttft_p99_ms=312.0,
                tokens_per_sec=400.0,
                sve2_utilization_pct=29.0,
                dram_bandwidth_pct=45.0,
                cache_miss_rate_pct=5.0,
                kv_eviction_rate=2.0,
                requests_per_min=800.0,
            ),
            after=baseline,
            duration_ms=45_000,
        )
        assert evt.after.sve2_utilization_pct == 79.0

    def test_audit_event(self):
        evt = AuditEvent(
            timestamp=datetime.now(UTC),
            commit_sha="abc1234",
            message="heal: adjust_vllm_config on node-002",
            node_id="node-002",
            action=ActionType.ADJUST_VLLM_CONFIG,
            checkpoint_id="ckpt-001",
        )
        assert evt.type == WebSocketEventType.AUDIT

    def test_flame_graph_event(self):
        evt = FlameGraphEvent(
            timestamp=datetime.now(UTC),
            node_id="node-001",
            hotspots=[HotspotEntry(symbol="attention", samples_pct=35.0)],
        )
        assert len(evt.hotspots) == 1


class TestOpenAPIContract:
    @pytest.fixture
    def spec(self):
        path = Path(__file__).resolve().parents[2] / "neosentinel" / "contracts" / "openapi.yaml"
        with path.open() as f:
            return yaml.safe_load(f)

    def test_openapi_version(self, spec):
        assert spec["openapi"] == "3.1.0"
        assert spec["info"]["version"] == "1.0.0"

    def test_health_endpoint(self, spec):
        assert "/health" in spec["paths"]
        assert "get" in spec["paths"]["/health"]

    def test_websocket_endpoint(self, spec):
        assert "/ws" in spec["paths"]

    def test_rest_endpoints(self, spec):
        for path in ["/api/v1/cluster", "/api/v1/decisions", "/api/v1/healing", "/api/v1/audit"]:
            assert path in spec["paths"]

    def test_action_type_enum_in_spec(self, spec):
        actions = spec["components"]["schemas"]["ActionType"]["enum"]
        assert len(actions) == 7
        assert "noop" in actions
        assert "rollback_optimization" in actions

    def test_websocket_event_discriminator(self, spec):
        ws = spec["components"]["schemas"]["WebSocketEvent"]
        assert ws["discriminator"]["propertyName"] == "type"


class TestPackageImport:
    def test_contracts_importable(self):
        import neosentinel.contracts  # noqa: F401

    def test_type_adapter_roundtrip(self):
        adapter = TypeAdapter(SentinelDecision)
        original = SentinelDecision(
            decision_id="dec-rt",
            cluster_id="c1",
            node_id="node-003",
            timestamp=datetime.now(UTC),
            action=ActionType.NOOP,
            confidence=0.5,
            reasoning="stable",
        )
        restored = adapter.validate_json(original.model_dump_json())
        assert restored.decision_id == "dec-rt"
