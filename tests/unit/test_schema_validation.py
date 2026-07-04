from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from neosentinel.contracts.decision import ActionType
from neosentinel.schemas.decision import (
    export_grammar_json_schema,
    grammar_json_schema,
    is_valid_action,
    validate_decision_json,
    validate_decision_payload,
)
from neosentinel.schemas.grammar import (
    GrammarConstraintError,
    decode_grammar_constrained,
    reject_impossible_action_types,
)


def _valid_payload(**overrides: object) -> dict:
    base = {
        "decision_id": "dec-schema-001",
        "cluster_id": "cluster-graviton4",
        "node_id": "node-002",
        "timestamp": datetime.now(UTC).isoformat(),
        "action": ActionType.TRIGGER_REQUANTIZE.value,
        "confidence": 0.94,
        "reasoning": "SVE2 underutilization with elevated TTFT.",
        "parameters": {"target_precision": "int4"},
        "snapshot_hash": "abc123",
        "quorum_required": True,
    }
    base.update(overrides)
    return base


class TestGrammarSchemaExport:
    def test_schema_contains_all_action_enums(self):
        schema = grammar_json_schema()
        assert set(schema["properties"]["action"]["enum"]) == {a.value for a in ActionType}

    def test_export_is_valid_json_string(self):
        exported = export_grammar_json_schema()
        assert '"SentinelDecisionGrammar"' in exported
        assert "trigger_requantize" in exported


class TestValidDecisionPayloads:
    @pytest.mark.parametrize("action", list(ActionType))
    def test_each_action_type_valid(self, action: ActionType):
        decision = validate_decision_payload(_valid_payload(action=action.value))
        assert decision.action == action

    def test_roundtrip_json(self):
        raw = validate_decision_json(
            '{"decision_id":"dec-1","cluster_id":"c","node_id":"node-001",'
            '"timestamp":"2026-07-04T12:00:00+00:00","action":"noop",'
            '"confidence":0.5,"reasoning":"ok"}'
        )
        assert raw.action == ActionType.NOOP


class TestInvalidDecisionPayloads:
    def test_invalid_node_id(self):
        with pytest.raises(ValidationError):
            validate_decision_payload(_valid_payload(node_id="bad-node"))

    def test_confidence_above_one(self):
        with pytest.raises(ValidationError):
            validate_decision_payload(_valid_payload(confidence=1.2))

    def test_confidence_below_zero(self):
        with pytest.raises(ValidationError):
            validate_decision_payload(_valid_payload(confidence=-0.1))

    def test_invalid_action_enum(self):
        with pytest.raises(ValidationError):
            validate_decision_payload(_valid_payload(action="restart_worker"))

    def test_missing_required_field(self):
        payload = _valid_payload()
        del payload["reasoning"]
        with pytest.raises(ValidationError):
            validate_decision_payload(payload)

    def test_invalid_json_text(self):
        with pytest.raises(ValueError, match="Invalid decision JSON"):
            validate_decision_json("{not-json")

    def test_non_object_json(self):
        with pytest.raises(ValidationError):
            validate_decision_json("[1,2,3]")

    def test_impossible_action_rejected(self):
        with pytest.raises(GrammarConstraintError):
            reject_impossible_action_types("restart_worker")

    def test_grammar_decode_rejects_bad_action(self):
        payload = _valid_payload(action="isolate_node")
        with pytest.raises(GrammarConstraintError):
            decode_grammar_constrained(
                '{"decision_id":"d","cluster_id":"c","node_id":"node-001",'
                '"timestamp":"2026-07-04T12:00:00+00:00","action":"isolate_node",'
                '"confidence":0.5,"reasoning":"x"}'
            )
        _ = payload


class TestIsValidAction:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ("noop", True),
            ("trigger_requantize", True),
            ("restart_worker", False),
            ("", False),
        ],
    )
    def test_action_membership(self, value: str, expected: bool):
        assert is_valid_action(value) is expected
