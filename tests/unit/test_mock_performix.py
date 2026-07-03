import json

from neosentinel.telemetry.mock_performix import MockPerformix


class TestMockPerformix:
    def test_generate_frame_is_contract_valid(self):
        mock = MockPerformix("node-001", seed=42)
        frame = mock.generate_frame()
        frame.validate_stream_fields()
        assert frame.node_id == "node-001"
        assert 0.0 <= frame.sve2_utilization_pct <= 100.0
        assert 0.0 <= frame.dram_bandwidth_pct <= 100.0
        assert len(frame.hotspots) == 5

    def test_stream_produces_requested_count(self):
        mock = MockPerformix("node-002", seed=1)
        frames = list(mock.stream(10))
        assert len(frames) == 10
        assert all(f.node_id == "node-002" for f in frames)

    def test_to_apx_text_is_parseable(self):
        from neosentinel.telemetry.performix import parse_apx_output

        mock = MockPerformix("node-003", seed=99)
        text = mock.to_apx_text()
        frame = parse_apx_output(text)
        assert frame.node_id == "node-003"
        assert len(frame.hotspots) == 5

    def test_hotspots_json_serializable(self):
        mock = MockPerformix("node-001", seed=7)
        fields = mock.generate_frame().to_stream_fields()
        hotspots = json.loads(fields["hotspots_json"])
        assert len(hotspots) == 5
        assert "symbol" in hotspots[0]
