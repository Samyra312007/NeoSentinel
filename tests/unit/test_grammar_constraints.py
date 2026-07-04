import json
from datetime import UTC, datetime

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from neosentinel.contracts.decision import ActionType, SentinelDecision
from neosentinel.schemas.decision import grammar_json_schema, validate_decision_payload
from neosentinel.schemas.grammar import (
    GrammarConstraintError,
    decode_grammar_constrained,
    reject_impossible_action_types,
)

INVALID_ACTIONS = [
    "restart_worker",
    "rebalance_kv_load",
    "migrate_workload",
    "isolate_node",
    "delete_cluster",
    "",
    "TRIGGER_REQUANTIZE",
    "noop_extra",
]

VALID_ACTIONS = [action.value for action in ActionType]
_ID_ALPHABET = "abcdefghijklmnopqrstuvwxyz0123456789-"


@st.composite
def sentinel_decision_payloads(draw: st.DrawFn) -> dict:
    action = draw(st.sampled_from(VALID_ACTIONS))
    node_num = draw(st.integers(min_value=1, max_value=3))
    confidence = draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False))
    return {
        "decision_id": draw(
            st.text(min_size=4, max_size=32, alphabet=_ID_ALPHABET),
        ),
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


class TestGrammarConstraints:
    @given(payload=sentinel_decision_payloads())
    @settings(max_examples=1000, deadline=None)
    def test_generated_decisions_have_zero_schema_violations(self, payload: dict):
        decision = validate_decision_payload(payload)
        assert isinstance(decision, SentinelDecision)
        assert decision.action.value in VALID_ACTIONS

    @given(payload=sentinel_decision_payloads())
    @settings(max_examples=200, deadline=None)
    def test_grammar_json_roundtrip(self, payload: dict):
        encoded = json.dumps(payload)
        decoded = decode_grammar_constrained(encoded)
        assert decoded.action.value == payload["action"]

    @pytest.mark.parametrize("bad_action", INVALID_ACTIONS)
    def test_impossible_actions_rejected(self, bad_action: str):
        with pytest.raises(GrammarConstraintError):
            reject_impossible_action_types(bad_action)

    def test_grammar_schema_enum_matches_action_type(self):
        schema = grammar_json_schema()
        assert set(schema["properties"]["action"]["enum"]) == set(VALID_ACTIONS)
