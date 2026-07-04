"""S5.3 tests — Quorum voting (2/3 majority required).

Exhaustively tests all vote combinations for a 3-voter quorum to verify
that the 2-of-3 majority rule is enforced correctly.
"""

from __future__ import annotations

import itertools

import pytest

from neosentinel.orchestrator.cluster import (
    QUORUM_MAJORITY,
    QuorumResult,
    Vote,
    VoteValue,
    run_quorum,
)


class TestQuorumVoting:
    def test_unanimous_approve(self) -> None:
        votes = [
            Vote(voter_id="node-001", value=VoteValue.APPROVE),
            Vote(voter_id="node-002", value=VoteValue.APPROVE),
            Vote(voter_id="node-003", value=VoteValue.APPROVE),
        ]
        result = run_quorum("dec-test-001", votes)
        assert result.passed is True
        assert result.approvals == 3

    def test_unanimous_reject(self) -> None:
        votes = [
            Vote(voter_id="node-001", value=VoteValue.REJECT),
            Vote(voter_id="node-002", value=VoteValue.REJECT),
            Vote(voter_id="node-003", value=VoteValue.REJECT),
        ]
        result = run_quorum("dec-test-002", votes)
        assert result.passed is False
        assert result.rejections == 3

    def test_two_approve_one_reject_passes(self) -> None:
        votes = [
            Vote(voter_id="node-001", value=VoteValue.APPROVE),
            Vote(voter_id="node-002", value=VoteValue.APPROVE),
            Vote(voter_id="node-003", value=VoteValue.REJECT),
        ]
        result = run_quorum("dec-test-003", votes)
        assert result.passed is True
        assert result.approvals == 2

    def test_one_approve_two_reject_fails(self) -> None:
        votes = [
            Vote(voter_id="node-001", value=VoteValue.APPROVE),
            Vote(voter_id="node-002", value=VoteValue.REJECT),
            Vote(voter_id="node-003", value=VoteValue.REJECT),
        ]
        result = run_quorum("dec-test-004", votes)
        assert result.passed is False
        assert result.approvals == 1

    def test_two_approve_one_abstain_passes(self) -> None:
        votes = [
            Vote(voter_id="node-001", value=VoteValue.APPROVE),
            Vote(voter_id="node-002", value=VoteValue.APPROVE),
            Vote(voter_id="node-003", value=VoteValue.ABSTAIN),
        ]
        result = run_quorum("dec-test-005", votes)
        assert result.passed is True

    def test_one_approve_two_abstain_fails(self) -> None:
        votes = [
            Vote(voter_id="node-001", value=VoteValue.APPROVE),
            Vote(voter_id="node-002", value=VoteValue.ABSTAIN),
            Vote(voter_id="node-003", value=VoteValue.ABSTAIN),
        ]
        result = run_quorum("dec-test-006", votes)
        assert result.passed is False

    def test_empty_votes_fails(self) -> None:
        result = run_quorum("dec-test-007", [])
        assert result.passed is False
        assert result.total == 0

    @pytest.mark.parametrize(
        "combo",
        list(
            itertools.product(
                [VoteValue.APPROVE, VoteValue.REJECT, VoteValue.ABSTAIN],
                repeat=3,
            )
        ),
    )
    def test_all_3_voter_combinations(
        self,
        combo: tuple[VoteValue, VoteValue, VoteValue],
    ) -> None:
        """Exhaustively test all 27 vote permutations."""
        votes = [Vote(voter_id=f"node-{i:03d}", value=v) for i, v in enumerate(combo, start=1)]
        result = run_quorum("dec-exhaustive", votes)
        expected_approvals = sum(1 for v in combo if v == VoteValue.APPROVE)
        assert result.approvals == expected_approvals
        assert result.passed == (expected_approvals >= QUORUM_MAJORITY)

    def test_quorum_result_properties(self) -> None:
        votes = [
            Vote(
                voter_id="node-001",
                value=VoteValue.APPROVE,
                reason="metrics look bad",
            ),
            Vote(voter_id="node-002", value=VoteValue.REJECT, reason="false alarm"),
            Vote(voter_id="node-003", value=VoteValue.APPROVE),
        ]
        result = run_quorum("dec-test-props", votes)
        assert isinstance(result, QuorumResult)
        assert result.decision_id == "dec-test-props"
        assert result.total == 3
        assert result.approvals == 2
        assert result.rejections == 1
