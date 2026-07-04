"""Tests for the cluster report data provider (Sahil · Week 6)."""

from datetime import UTC, datetime

import pytest

from neosentinel.contracts.decision import ActionType
from neosentinel.contracts.telemetry import (
    BaselineMetrics,
    HotspotEntry,
    NodeSnapshot,
    NodeStatus,
    TelemetrySnapshot,
)
from neosentinel.contracts.websocket import AuditEvent, HealingEvent
from neosentinel.report import (
    ClusterReport,
    build_cluster_report,
    nominal_cluster_report,
    render_report_html,
)

TS = datetime(2026, 7, 4, 12, 0, 0, tzinfo=UTC)


def _node(node_id: str, status: NodeStatus, *, ttft=120.0, sve2=80.0, hotspot: str | None = None):
    return NodeSnapshot(
        node_id=node_id,
        status=status,
        timestamp=TS,
        ttft_p99_ms=ttft,
        tokens_per_sec=45.0,
        sve2_utilization_pct=sve2,
        dram_bandwidth_pct=55.0,
        cache_miss_rate_pct=12.0,
        kv_eviction_rate=0.5,
        requests_per_min=350.0,
        hotspots=[HotspotEntry(symbol=hotspot, samples_pct=70.0)] if hotspot else [],
    )


def _healing(status: str, *, before_ttft, after_ttft, before_sve2, after_sve2) -> HealingEvent:
    def _metrics(ttft, sve2):
        return BaselineMetrics(
            ttft_p99_ms=ttft,
            tokens_per_sec=40.0,
            sve2_utilization_pct=sve2,
            dram_bandwidth_pct=55.0,
            cache_miss_rate_pct=12.0,
            kv_eviction_rate=0.5,
            requests_per_min=340.0,
        )

    return HealingEvent(
        timestamp=TS,
        healing_id="heal-001",
        node_id="node-002",
        action=ActionType.TRIGGER_REQUANTIZE,
        status=status,
        before=_metrics(before_ttft, before_sve2),
        after=_metrics(after_ttft, after_sve2),
        duration_ms=4850,
    )


def test_all_healthy_reports_nominal() -> None:
    snapshot = TelemetrySnapshot(
        cluster_id="cluster-graviton4",
        timestamp=TS,
        nodes=[_node("node-001", NodeStatus.HEALTHY), _node("node-003", NodeStatus.HEALTHY)],
    )
    report = build_cluster_report(snapshot, generated_at=TS)
    assert report.overall_status == "HEALTHY"
    assert report.headline == "Graviton4 Control Plane Nominal"
    assert report.healthy_nodes == 2
    assert report.total_nodes == 2


def test_degraded_and_unhealthy_change_verdict() -> None:
    degraded = TelemetrySnapshot(
        cluster_id="c",
        timestamp=TS,
        nodes=[_node("node-001", NodeStatus.HEALTHY), _node("node-002", NodeStatus.DEGRADED)],
    )
    assert build_cluster_report(degraded, generated_at=TS).overall_status == "DEGRADED"

    unhealthy = TelemetrySnapshot(
        cluster_id="c",
        timestamp=TS,
        nodes=[_node("node-002", NodeStatus.UNHEALTHY)],
    )
    verdict = build_cluster_report(unhealthy, generated_at=TS)
    assert verdict.overall_status == "CRITICAL"
    assert "unhealthy" in verdict.headline


def test_node_report_carries_top_hotspot() -> None:
    snapshot = TelemetrySnapshot(
        cluster_id="c",
        timestamp=TS,
        nodes=[_node("node-002", NodeStatus.DEGRADED, hotspot="unoptimized_gemm_kernel")],
    )
    report = build_cluster_report(snapshot, generated_at=TS)
    assert report.nodes[0].top_hotspot == "unoptimized_gemm_kernel"


def test_healing_summary_math() -> None:
    snapshot = TelemetrySnapshot(
        cluster_id="c", timestamp=TS, nodes=[_node("node-002", NodeStatus.HEALTHY)]
    )
    events = [
        _healing("success", before_ttft=312, after_ttft=131, before_sve2=29, after_sve2=79),
        _healing("success", before_ttft=300, after_ttft=140, before_sve2=30, after_sve2=80),
        _healing("failed", before_ttft=200, after_ttft=210, before_sve2=40, after_sve2=38),
        _healing("rolled_back", before_ttft=200, after_ttft=250, before_sve2=40, after_sve2=35),
    ]
    healing = build_cluster_report(snapshot, healing_events=events, generated_at=TS).healing
    assert healing.total == 4
    assert healing.succeeded == 2
    assert healing.failed == 1
    assert healing.rolled_back == 1
    assert healing.success_rate == 0.5
    # (181 + 160) / 2 = 170.5 ms ; (50 + 50) / 2 = 50 %
    assert healing.avg_ttft_improvement_ms == 170.5
    assert healing.avg_sve2_gain_pct == 50.0


def test_empty_healing_summary_is_zeroed() -> None:
    snapshot = TelemetrySnapshot(
        cluster_id="c", timestamp=TS, nodes=[_node("node-001", NodeStatus.HEALTHY)]
    )
    healing = build_cluster_report(snapshot, generated_at=TS).healing
    assert healing.total == 0
    assert healing.success_rate == 0.0


def test_audit_records_shorten_sha() -> None:
    snapshot = TelemetrySnapshot(
        cluster_id="c", timestamp=TS, nodes=[_node("node-002", NodeStatus.HEALTHY)]
    )
    audit = [
        AuditEvent(
            timestamp=TS,
            commit_sha="a1b2c3d4e5f60718293a4b5c6d7e8f9012345678",
            message="Auto-heal: applied trigger_requantize on node-002",
            node_id="node-002",
            action=ActionType.TRIGGER_REQUANTIZE,
            checkpoint_id="chk-node002-20260704120005",
        )
    ]
    report = build_cluster_report(snapshot, audit_events=audit, generated_at=TS)
    assert len(report.audit) == 1
    assert report.audit[0].short_sha == "a1b2c3d"


def test_report_round_trips_through_model_dump() -> None:
    report = nominal_cluster_report(generated_at=TS)
    assert ClusterReport.model_validate(report.model_dump()) == report


def test_nominal_report_has_three_healthy_nodes() -> None:
    report = nominal_cluster_report(generated_at=TS)
    assert report.total_nodes == 3
    assert report.healthy_nodes == 3
    assert report.headline == "Graviton4 Control Plane Nominal"


def test_render_html_contains_required_strings_and_escapes() -> None:
    snapshot = TelemetrySnapshot(
        cluster_id="cluster-graviton4",
        timestamp=TS,
        nodes=[_node("node-002", NodeStatus.DEGRADED, hotspot="<script>alert(1)</script>")],
    )
    html = render_report_html(build_cluster_report(snapshot, generated_at=TS))
    assert "NeoSentinel Cluster Health & Audit Report" in html
    assert "Graviton4 Control Plane Degraded" in html
    # user-derived content must be escaped, never injected raw
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html


def test_render_nominal_html_matches_cli_contract() -> None:
    """The strings the D5.4 report CLI test asserts on must be present."""
    html = render_report_html(nominal_cluster_report(generated_at=TS))
    assert "NeoSentinel Cluster Health & Audit Report" in html
    assert "Graviton4 Control Plane Nominal" in html


@pytest.mark.parametrize("cluster_id", ["cluster-graviton4", "edge-cluster-07"])
def test_cluster_id_flows_through(cluster_id: str) -> None:
    assert nominal_cluster_report(cluster_id, generated_at=TS).cluster_id == cluster_id
