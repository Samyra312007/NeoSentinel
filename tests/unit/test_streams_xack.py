from neosentinel.contracts.streams import CONSUMER_GROUPS, STREAM_PMU
from neosentinel.telemetry.mock_performix import MockPerformix


class TestStreamsXack:
    def test_publish_and_consume_with_ack(self, telemetry_pipeline):
        group = CONSUMER_GROUPS[STREAM_PMU]
        consumer = "test-consumer-1"
        frame = MockPerformix("node-001", seed=1).generate_frame()
        message_id = telemetry_pipeline.publish_pmu(frame)

        messages = telemetry_pipeline.read_group(
            STREAM_PMU,
            group,
            consumer,
            count=1,
            block_ms=100,
        )
        assert len(messages) == 1
        entry_id, fields = messages[0]
        assert entry_id == message_id
        assert fields["node_id"] == "node-001"
        assert telemetry_pipeline.pending_count(STREAM_PMU, group) == 1

        acked = telemetry_pipeline.ack(STREAM_PMU, group, entry_id)
        assert acked == 1
        assert telemetry_pipeline.pending_count(STREAM_PMU, group) == 0

    def test_unacked_messages_stay_pending(self, telemetry_pipeline):
        group = CONSUMER_GROUPS[STREAM_PMU]
        consumer = "test-consumer-2"
        frame = MockPerformix("node-002", seed=2).generate_frame()
        telemetry_pipeline.publish_pmu(frame)

        messages = telemetry_pipeline.read_group(
            STREAM_PMU,
            group,
            consumer,
            count=1,
            block_ms=100,
        )
        assert len(messages) == 1
        assert telemetry_pipeline.pending_count(STREAM_PMU, group) == 1

        redelivered = telemetry_pipeline.read_pending(
            STREAM_PMU,
            group,
            consumer,
            count=1,
        )
        assert len(redelivered) == 1

    def test_at_least_once_after_ack_new_consumer_gets_next(self, telemetry_pipeline):
        group = CONSUMER_GROUPS[STREAM_PMU]
        frame_a = MockPerformix("node-001", seed=3).generate_frame()
        frame_b = MockPerformix("node-001", seed=4).generate_frame()
        id_a = telemetry_pipeline.publish_pmu(frame_a)
        id_b = telemetry_pipeline.publish_pmu(frame_b)

        first = telemetry_pipeline.read_group(STREAM_PMU, group, "worker-a", count=1, block_ms=100)
        assert first[0][0] == id_a
        telemetry_pipeline.ack(STREAM_PMU, group, id_a)

        second = telemetry_pipeline.read_group(STREAM_PMU, group, "worker-b", count=1, block_ms=100)
        assert second[0][0] == id_b
