"""Property-based tests for the SentinelDecision schema (Sahil · Week 6).

The plan calls for "Hypothesis property tests for decision schema" — the spec's
target being *1000 generated decisions, 0 schema violations*. The frozen
contract in ``neosentinel/contracts/decision.py`` is the source of truth for the
decision shape, so these properties exercise it directly:

* every well-formed decision constructs and survives a JSON round-trip, and
* every constraint (node-id pattern, confidence bounds, action enum) actually
  rejects out-of-domain input.
"""

import re

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from neosentinel.contracts.decision import ActionType, SentinelDecision

NODE_ID_RE = re.compile(r"^node-\d{3}$")

# JSON-safe printable text keeps the round-trip deterministic (no lone surrogates).
_text = st.text(st.characters(min_codepoint=32, max_codepoint=126), max_size=120)
_node_ids = st.integers(min_value=0, max_value=999).map(lambda n: f"node-{n:03d}")
_params = st.dictionaries(
    keys=st.text(st.characters(min_codepoint=32, max_codepoint=126), min_size=1, max_size=24),
    values=st.one_of(
        st.booleans(),
        st.integers(min_value=-1_000_000, max_value=1_000_000),
        st.floats(allow_nan=False, allow_infinity=False, width=32),
        _text,
    ),
    max_size=6,
)


def _valid_decisions() -> st.SearchStrategy[SentinelDecision]:
    """A strategy that only ever yields contract-valid decisions."""
    return st.builds(
        SentinelDecision,
        decision_id=_text,
        cluster_id=_text,
        node_id=_node_ids,
        timestamp=st.datetimes(),
        action=st.sampled_from(list(ActionType)),
        confidence=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
        reasoning=_text,
        parameters=_params,
        snapshot_hash=_text,
        quorum_required=st.booleans(),
    )


@settings(max_examples=1000)
@given(decision=_valid_decisions())
def test_generated_decisions_never_violate_schema(decision: SentinelDecision) -> None:
    """1000 generated decisions, 0 schema violations (re-validation is a no-op)."""
    assert SentinelDecision.model_validate(decision.model_dump()) == decision
    assert NODE_ID_RE.match(decision.node_id)
    assert 0.0 <= decision.confidence <= 1.0


@settings(max_examples=500)
@given(decision=_valid_decisions())
def test_json_round_trip_is_lossless(decision: SentinelDecision) -> None:
    """Serialising to JSON and back reconstructs an identical decision."""
    assert SentinelDecision.model_validate_json(decision.model_dump_json()) == decision


@given(bad=st.floats(allow_nan=False, allow_infinity=False).filter(lambda x: x < 0.0 or x > 1.0))
def test_confidence_out_of_range_is_rejected(bad: float) -> None:
    with pytest.raises(ValidationError):
        SentinelDecision(
            decision_id="d",
            cluster_id="c",
            node_id="node-001",
            timestamp="2026-07-04T12:00:00Z",
            action=ActionType.NOOP,
            confidence=bad,
            reasoning="r",
        )


@given(bad_node=_text.filter(lambda s: NODE_ID_RE.match(s) is None))
def test_node_id_pattern_is_enforced(bad_node: str) -> None:
    with pytest.raises(ValidationError):
        SentinelDecision(
            decision_id="d",
            cluster_id="c",
            node_id=bad_node,
            timestamp="2026-07-04T12:00:00Z",
            action=ActionType.NOOP,
            confidence=0.5,
            reasoning="r",
        )


@pytest.mark.parametrize("confidence", [0.0, 1.0])
def test_confidence_boundaries_are_inclusive(confidence: float) -> None:
    decision = SentinelDecision(
        decision_id="d",
        cluster_id="c",
        node_id="node-042",
        timestamp="2026-07-04T12:00:00Z",
        action=ActionType.SEND_ALERT,
        confidence=confidence,
        reasoning="boundary",
    )
    assert decision.confidence == confidence


@pytest.mark.parametrize("action", list(ActionType))
def test_every_action_type_is_constructible(action: ActionType) -> None:
    decision = SentinelDecision(
        decision_id="d",
        cluster_id="c",
        node_id="node-003",
        timestamp="2026-07-04T12:00:00Z",
        action=action,
        confidence=0.9,
        reasoning="enumerate",
    )
    assert decision.action is action


def test_action_type_has_seven_values() -> None:
    """The contract fixes exactly seven action types (spec: 7 enum values)."""
    assert len(list(ActionType)) == 7
