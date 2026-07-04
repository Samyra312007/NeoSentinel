from __future__ import annotations

import json
from typing import Any

from pydantic import ValidationError

from neosentinel.contracts.decision import ActionType, SentinelDecision
from neosentinel.schemas.decision import grammar_json_schema


class GrammarConstraintError(ValueError):
    pass


def enforce_action_enum(
    payload: dict[str, Any],
    schema: dict[str, Any] | None = None,
) -> dict[str, Any]:
    resolved_schema = schema or grammar_json_schema()
    allowed = set(resolved_schema["properties"]["action"]["enum"])
    action = payload.get("action")
    if action not in allowed:
        raise GrammarConstraintError(
            f"Action '{action}' is not in grammar enum: {sorted(allowed)}"
        )
    return payload


def decode_grammar_constrained(text: str) -> SentinelDecision:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise GrammarConstraintError(f"Invalid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise GrammarConstraintError("Decision payload must be a JSON object")
    enforce_action_enum(payload)
    try:
        return SentinelDecision.model_validate(payload)
    except ValidationError as exc:
        raise GrammarConstraintError(str(exc)) from exc


def reject_impossible_action_types(raw_action: str) -> None:
    if not raw_action:
        raise GrammarConstraintError("Action must not be empty")
    try:
        ActionType(raw_action)
    except ValueError as exc:
        raise GrammarConstraintError(f"Impossible action type: {raw_action}") from exc
