from __future__ import annotations

from dataclasses import dataclass
from itertools import product

from neosentinel.agent.decision_tree import SVE2_LOW_THRESHOLD, TTFT_HIGH_THRESHOLD, evaluate_node
from neosentinel.contracts.decision import ActionType
from neosentinel.contracts.telemetry import NodeSnapshot, TelemetrySnapshot

CLUSTER_SIZE = 3
QUORUM_THRESHOLD = 2


@dataclass(frozen=True)
class NodeVote:
    voter_id: str
    agrees: bool
    action: ActionType
    confidence: float
    reason: str


@dataclass(frozen=True)
class QuorumResult:
    votes: tuple[NodeVote, ...]
    agree_count: int
    quorum_met: bool
    required: int = QUORUM_THRESHOLD


def quorum_met(agree_count: int, *, required: int = QUORUM_THRESHOLD) -> bool:
    return agree_count >= required


def evaluate_votes(votes: list[NodeVote] | tuple[NodeVote, ...]) -> QuorumResult:
    agree_count = sum(1 for vote in votes if vote.agrees)
    return QuorumResult(
        votes=tuple(votes),
        agree_count=agree_count,
        quorum_met=quorum_met(agree_count),
    )


def _node_supports_heal(
    voter: NodeSnapshot,
    target: NodeSnapshot,
    proposed_action: ActionType,
) -> bool:
    if voter.node_id == target.node_id:
        return True
    if proposed_action == ActionType.NOOP:
        return True
    voter_candidate = evaluate_node(voter)
    if voter_candidate.action == proposed_action:
        return True
    if (
        target.sve2_utilization_pct < SVE2_LOW_THRESHOLD
        and target.ttft_p99_ms > TTFT_HIGH_THRESHOLD
        and voter.sve2_utilization_pct >= SVE2_LOW_THRESHOLD
    ):
        return True
    return voter.status.value == "healthy" and target.status.value != "healthy"


def collect_votes(
    snapshot: TelemetrySnapshot,
    *,
    target_node_id: str,
    proposed_action: ActionType,
) -> QuorumResult:
    target = next(node for node in snapshot.nodes if node.node_id == target_node_id)
    votes: list[NodeVote] = []
    for voter in snapshot.nodes:
        agrees = _node_supports_heal(voter, target, proposed_action)
        candidate = evaluate_node(voter)
        votes.append(
            NodeVote(
                voter_id=voter.node_id,
                agrees=agrees,
                action=candidate.action,
                confidence=candidate.confidence,
                reason=f"{'support' if agrees else 'reject'} heal on {target_node_id}",
            )
        )
    return evaluate_votes(votes)


def all_vote_combinations() -> list[tuple[bool, bool, bool]]:
    return list(product([False, True], repeat=CLUSTER_SIZE))
