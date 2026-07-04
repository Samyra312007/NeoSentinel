from __future__ import annotations

import json
from typing import Any

from pydantic import ValidationError

from neosentinel.contracts.decision import ActionType, SentinelDecision

GRAMMAR_SCHEMA_VERSION = "1.0.0"


def grammar_json_schema() -> dict[str, Any]:
    schema = SentinelDecision.model_json_schema()
    action_schema = schema.setdefault("properties", {}).setdefault("action", {})
    action_schema["enum"] = [action.value for action in ActionType]
    action_schema["type"] = "string"
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["title"] = "SentinelDecisionGrammar"
    schema["description"] = "Grammar-constrained agent decision output for llama.cpp"
    return schema


def export_grammar_json_schema() -> str:
    return json.dumps(grammar_json_schema(), indent=2, sort_keys=True)


def validate_decision_payload(payload: dict[str, Any]) -> SentinelDecision:
    return SentinelDecision.model_validate(payload)


def validate_decision_json(text: str) -> SentinelDecision:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid decision JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValidationError.from_exception_data(
            "SentinelDecision",
            [
                {
                    "type": "dict_type",
                    "loc": (),
                    "msg": "Decision payload must be a JSON object",
                    "input": payload,
                }
            ],
        )
    return validate_decision_payload(payload)


def is_valid_action(value: str) -> bool:
    try:
        ActionType(value)
    except ValueError:
        return False
    return True
