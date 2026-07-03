from neosentinel.telemetry.performix import PerformixDaemon, parse_apx_output

SAMPLE_APX_OUTPUT = """\
=== PMU Snapshot @ 2026-07-03T12:00:00Z ===
node_id: node-002
sve2_utilization_pct: 79.2
dram_bandwidth_pct: 45.1
cache_miss_rate_pct: 3.2

=== Hotspots (top 5) ===
  42.0%  gemm_kernel  [vllm]
  18.5%  attention_fwd  [vllm]
  12.3%  kv_cache_update  [vllm]
  8.1%  rope_apply  [vllm]
  5.4%  sampler  [vllm]
"""


class TestPerformixParser:
    def test_parse_sample_apx_output(self):
        frame = parse_apx_output(SAMPLE_APX_OUTPUT)
        assert frame.node_id == "node-002"
        assert frame.sve2_utilization_pct == 79.2
        assert frame.dram_bandwidth_pct == 45.1
        assert frame.cache_miss_rate_pct == 3.2
        assert len(frame.hotspots) == 5
        assert frame.hotspots[0].symbol == "gemm_kernel"
        assert frame.hotspots[0].samples_pct == 42.0
        assert frame.hotspots[0].module == "vllm"

    def test_stream_fields_match_pmu_contract(self):
        frame = parse_apx_output(SAMPLE_APX_OUTPUT)
        fields = frame.to_stream_fields()
        assert fields["node_id"] == "node-002"
        assert "hotspots_json" in fields
        frame.validate_stream_fields()

    def test_daemon_collect_once_with_mock_runner(self):
        daemon = PerformixDaemon(
            node_id="node-001",
            runner=lambda _cmd: SAMPLE_APX_OUTPUT,
        )
        frame = daemon.collect_once()
        assert frame.sve2_utilization_pct == 79.2

    def test_daemon_stream_respects_max_frames(self):
        daemon = PerformixDaemon(
            node_id="node-001",
            interval_hz=1000.0,
            runner=lambda _cmd: SAMPLE_APX_OUTPUT,
        )
        frames = list(daemon.stream(max_frames=3))
        assert len(frames) == 3
