import json
from datetime import UTC, datetime

import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from neosentinel.contracts.decision import ActionType, SentinelDecision
from neosentinel.schemas.decision import (
    export_grammar_json_schema,
    grammar_json_schema,
    is_valid_action,
    validate_decision_json,
    validate_decision_payload,
)
from neosentinel.schemas.grammar import GrammarConstraintError, reject_impossible_action_types

VALID_ACTIONS = [action.value for action in ActionType]
_ID_ALPHABET = "abcdefghijklmnopqrstuvwxyz0123456789-"


@st.composite
def valid_sentinel_decision_payloads(draw: st.DrawFn) -> dict:
    action = draw(st.sampled_from(VALID_ACTIONS))
    node_num = draw(st.integers(min_value=1, max_value=3))
    confidence = draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False))
    return {
        "decision_id": draw(st.text(min_size=4, max_size=32, alphabet=_ID_ALPHABET)),
        "cluster_id": draw(
            st.text(min_size=3, max_size=24, alphabet="abcdefghijklmnopqrstuvwxyz-"),
        ),
        "node_id": f"node-{node_num:03d}",
        "timestamp": datetime.now(UTC).isoformat(),
        "action": action,
        "confidence": confidence,
        "reasoning": draw(st.text(min_size=1, max_size=120)),
        "parameters": draw(
            st.dictionaries(
                keys=st.text(min_size=1, max_size=16, alphabet="abcdefghijklmnopqrstuvwxyz_"),
                values=st.one_of(
                    st.integers(),
                    st.floats(allow_nan=False),
                    st.booleans(),
                    st.text(max_size=20),
                ),
                max_size=4,
            )
        ),
        "snapshot_hash": draw(
            st.text(min_size=8, max_size=16, alphabet="abcdef0123456789"),
        ),
        "quorum_required": draw(st.booleans()),
    }


@st.composite
def invalid_node_id_payloads(draw: st.DrawFn) -> dict:
    payload = draw(valid_sentinel_decision_payloads())
    payload["node_id"] = draw(
        st.one_of(
            st.text(min_size=1, max_size=12),
            st.just("node-1"),
            st.just("NODE-001"),
            st.just(""),
        )
    )
    assume(payload["node_id"] not in {f"node-{i:03d}" for i in range(1, 4)})
    return payload


@st.composite
def invalid_action_payloads(draw: st.DrawFn) -> dict:
    payload = draw(valid_sentinel_decision_payloads())
    payload["action"] = draw(
        st.text(min_size=1, max_size=24).filter(lambda v: not is_valid_action(v))
    )
    return payload


class TestDecisionSchemaProperties:
    @given(payload=valid_sentinel_decision_payloads())
    @settings(max_examples=500, deadline=None)
    def test_valid_payload_roundtrips_through_model_dump(self, payload: dict):
        decision = validate_decision_payload(payload)
        restored = SentinelDecision.model_validate(decision.model_dump())
        assert restored.action == decision.action
        assert restored.node_id == decision.node_id
        assert restored.confidence == decision.confidence

    @given(payload=valid_sentinel_decision_payloads())
    @settings(max_examples=500, deadline=None)
    def test_valid_payload_json_roundtrip(self, payload: dict):
        encoded = json.dumps(payload)
        decision = validate_decision_json(encoded)
        assert decision.action.value == payload["action"]
        assert 0.0 <= decision.confidence <= 1.0

    @given(payload=invalid_node_id_payloads())
    @settings(max_examples=200, deadline=None)
    def test_invalid_node_id_rejected(self, payload: dict):
        with pytest.raises(Exception):
            validate_decision_payload(payload)

    @given(payload=invalid_action_payloads())
    @settings(max_examples=200, deadline=None)
    def test_invalid_action_string_rejected_by_grammar(self, payload: dict):
        with pytest.raises(GrammarConstraintError):
            reject_impossible_action_types(payload["action"])

    @given(payload=valid_sentinel_decision_payloads())
    @settings(max_examples=200, deadline=None)
    def test_grammar_schema_export_is_stable_json(self, payload: dict):
        _ = validate_decision_payload(payload)
        exported = export_grammar_json_schema()
        parsed = json.loads(exported)
        assert parsed["title"] == "SentinelDecisionGrammar"
        assert set(parsed["properties"]["action"]["enum"]) == set(VALID_ACTIONS)

    def test_grammar_json_schema_contains_all_action_types(self):
        schema = grammar_json_schema()
        assert set(schema["properties"]["action"]["enum"]) == set(VALID_ACTIONS)

    @given(confidence=st.floats(allow_nan=True))
    @settings(max_examples=100, deadline=None)
    def test_confidence_out_of_range_rejected(self, confidence: float):
        assume(confidence < 0.0 or confidence > 1.0 or confidence != confidence)
        payload = {
            "decision_id": "dec-test",
            "cluster_id": "cluster-graviton4",
            "node_id": "node-001",
            "timestamp": datetime.now(UTC).isoformat(),
            "action": ActionType.NOOP.value,
            "confidence": confidence,
            "reasoning": "test",
            "parameters": {},
            "snapshot_hash": "abc12345",
            "quorum_required": False,
        }
        with pytest.raises(Exception):
            validate_decision_payload(payload)
