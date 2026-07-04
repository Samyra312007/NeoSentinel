import json
from datetime import UTC, datetime
from pathlib import Path

from neosentinel.actions.base import ActionResult
from neosentinel.agent.snapshot import seed_node_telemetry
from neosentinel.audit.checkpoints import CheckpointStore
from neosentinel.contracts.decision import ActionType
from neosentinel.contracts.telemetry import BaselineMetrics
from neosentinel.report import ReportDataProvider, render_cluster_report_html


class TestReportProvider:
    def test_collect_empty_redis_returns_structured_report(self, fake_redis):
        provider = ReportDataProvider(fake_redis)
        report = provider.collect()
        assert report.cluster_id == "cluster-graviton4"
        assert report.snapshot is None
        assert report.decisions == []
        assert report.healing_events == []
        assert report.healthy_node_count == 0

    def test_collect_includes_snapshot_decisions_and_healing(
        self,
        telemetry_pipeline,
        fake_redis,
    ):
        seed_node_telemetry(
            fake_redis,
            node_id="node-001",
            sve2_utilization_pct=79.0,
            dram_bandwidth_pct=45.0,
            cache_miss_rate_pct=3.0,
            ttft_p99_ms=131.0,
            tokens_per_sec=842.0,
            kv_eviction_rate=0.1,
            requests_per_min=400.0,
        )
        from neosentinel.contracts.decision import SentinelDecision

        decision = SentinelDecision(
            decision_id="dec-report-001",
            cluster_id="cluster-graviton4",
            node_id="node-001",
            timestamp=datetime.now(UTC),
            action=ActionType.NOOP,
            confidence=0.99,
            reasoning="healthy",
            parameters={},
            snapshot_hash="abc123",
            quorum_required=False,
        )
        telemetry_pipeline.publish_decision(decision)
        telemetry_pipeline.publish_healing(
            decision_id=decision.decision_id,
            result=ActionResult(
                action=ActionType.NOOP,
                node_id="node-001",
                success=True,
                message="noop complete",
                before=BaselineMetrics(
                    ttft_p99_ms=131.0,
                    tokens_per_sec=842.0,
                    sve2_utilization_pct=79.0,
                    dram_bandwidth_pct=45.0,
                    cache_miss_rate_pct=3.0,
                    kv_eviction_rate=0.1,
                    requests_per_min=400.0,
                ),
                after=BaselineMetrics(
                    ttft_p99_ms=131.0,
                    tokens_per_sec=842.0,
                    sve2_utilization_pct=79.0,
                    dram_bandwidth_pct=45.0,
                    cache_miss_rate_pct=3.0,
                    kv_eviction_rate=0.1,
                    requests_per_min=400.0,
                ),
                duration_ms=10,
            ),
            checkpoint_id="chk-node-001-test",
            status="success",
        )

        provider = ReportDataProvider(fake_redis)
        report = provider.collect()
        assert report.snapshot is not None
        assert len(report.snapshot.nodes) == 1
        assert report.healthy_node_count == 1
        assert len(report.decisions) == 1
        assert report.decisions[0].decision_id == "dec-report-001"
        assert len(report.healing_events) == 1
        assert report.healing_events[0].status == "success"

    def test_collect_loads_checkpoints_from_store(self, fake_redis, tmp_path: Path):
        store = CheckpointStore(tmp_path / "checkpoints")
        store.create(
            decision_id="dec-chk",
            node_id="node-002",
            action=ActionType.TRIGGER_REQUANTIZE,
            metrics=BaselineMetrics(
                ttft_p99_ms=312.0,
                tokens_per_sec=400.0,
                sve2_utilization_pct=29.0,
                dram_bandwidth_pct=88.0,
                cache_miss_rate_pct=45.0,
                kv_eviction_rate=4.0,
                requests_per_min=200.0,
            ),
            vllm_config={"precision": "int8"},
            parameters={"target_precision": "int4"},
        )
        provider = ReportDataProvider(fake_redis, checkpoint_root=tmp_path / "checkpoints")
        report = provider.collect()
        assert len(report.checkpoints) == 1
        assert report.checkpoints[0].node_id == "node-002"

    def test_to_dict_serializable(self, fake_redis):
        provider = ReportDataProvider(fake_redis)
        payload = provider.collect().to_dict()
        encoded = json.dumps(payload)
        assert "generated_at" in encoded

    def test_render_html_includes_cluster_status(self, fake_redis):
        provider = ReportDataProvider(fake_redis)
        html = render_cluster_report_html(provider.collect())
        assert "NeoSentinel Cluster Health" in html
        assert "Graviton4 Control Plane Nominal" in html
