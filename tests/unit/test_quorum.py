from datetime import UTC, datetime

import pytest

from neosentinel.contracts.decision import ActionType
from neosentinel.contracts.telemetry import NodeSnapshot, NodeStatus, TelemetrySnapshot
from neosentinel.orchestrator.quorum import (
    QUORUM_THRESHOLD,
    NodeVote,
    all_vote_combinations,
    collect_votes,
    evaluate_votes,
    quorum_met,
)


def _votes(agreements: tuple[bool, bool, bool]) -> list[NodeVote]:
    return [
        NodeVote(
            voter_id=f"node-{index:03d}",
            agrees=agree,
            action=ActionType.TRIGGER_REQUANTIZE,
            confidence=0.9,
            reason="test",
        )
        for index, agree in enumerate(agreements, start=1)
    ]


class TestQuorum:
    def test_quorum_threshold_is_two_of_three(self):
        assert QUORUM_THRESHOLD == 2

    @pytest.mark.parametrize(
        ("agreements", "expected"),
        [
            ((True, True, True), True),
            ((True, True, False), True),
            ((True, False, True), True),
            ((False, True, True), True),
            ((True, False, False), False),
            ((False, True, False), False),
            ((False, False, True), False),
            ((False, False, False), False),
        ],
    )
    def test_all_vote_combinations(self, agreements: tuple[bool, bool, bool], expected: bool):
        result = evaluate_votes(_votes(agreements))
        assert result.quorum_met is expected
        assert result.agree_count == sum(agreements)

    def test_all_combinations_enumerated(self):
        combos = all_vote_combinations()
        assert len(combos) == 8

    def test_quorum_met_helper(self):
        assert quorum_met(2) is True
        assert quorum_met(1) is False
        assert quorum_met(3) is True

    def test_collect_votes_for_sve2_heal(self):
        snapshot = TelemetrySnapshot(
            cluster_id="cluster-graviton4",
            timestamp=datetime.now(UTC),
            nodes=[
                NodeSnapshot(
                    node_id="node-001",
                    status=NodeStatus.HEALTHY,
                    timestamp=datetime.now(UTC),
                    ttft_p99_ms=120.0,
                    tokens_per_sec=45.0,
                    sve2_utilization_pct=82.0,
                    dram_bandwidth_pct=55.0,
                    cache_miss_rate_pct=12.0,
                    kv_eviction_rate=0.5,
                    requests_per_min=350.0,
                ),
                NodeSnapshot(
                    node_id="node-002",
                    status=NodeStatus.DEGRADED,
                    timestamp=datetime.now(UTC),
                    ttft_p99_ms=312.0,
                    tokens_per_sec=18.4,
                    sve2_utilization_pct=29.0,
                    dram_bandwidth_pct=88.5,
                    cache_miss_rate_pct=45.0,
                    kv_eviction_rate=4.2,
                    requests_per_min=340.0,
                ),
                NodeSnapshot(
                    node_id="node-003",
                    status=NodeStatus.HEALTHY,
                    timestamp=datetime.now(UTC),
                    ttft_p99_ms=118.0,
                    tokens_per_sec=46.0,
                    sve2_utilization_pct=80.5,
                    dram_bandwidth_pct=54.0,
                    cache_miss_rate_pct=11.8,
                    kv_eviction_rate=0.4,
                    requests_per_min=355.0,
                ),
            ],
        )
        result = collect_votes(
            snapshot,
            target_node_id="node-002",
            proposed_action=ActionType.TRIGGER_REQUANTIZE,
        )
        assert result.agree_count >= QUORUM_THRESHOLD
        assert result.quorum_met is True
