from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol

from neosentinel.agent.decision_tree import (
    DecisionCandidate,
    evaluate_snapshot,
    new_decision_id,
)
from neosentinel.contracts.decision import ActionType, SentinelDecision
from neosentinel.contracts.telemetry import TelemetrySnapshot
from neosentinel.schemas.grammar import decode_grammar_constrained

MODEL_NAME = "meta-llama/Llama-3.2-3B-Instruct"
MODEL_QUANT = "INT4"
CPU_BUDGET_PCT = 5.0


class LlamaCppBackend(Protocol):
    def complete(
        self,
        prompt: str,
        *,
        grammar_schema: dict[str, Any],
        max_tokens: int = 256,
    ) -> str: ...


@dataclass
class BrainStats:
    decisions_made: int = 0
    grammar_rejections: int = 0
    total_cpu_time_ms: float = 0.0
    last_decision_id: str | None = None


class MockLlamaCppBackend:
    def __init__(
        self,
        *,
        responder: Callable[[str, DecisionCandidate], dict[str, Any]] | None = None,
        simulate_cpu_ms: float = 12.0,
    ) -> None:
        self._responder = responder
        self.simulate_cpu_ms = simulate_cpu_ms
        self.calls: list[str] = []
        self._last_candidate = DecisionCandidate(
            node_id="node-001",
            action=ActionType.NOOP,
            confidence=0.5,
            reasoning="init",
            parameters={},
        )

    def complete(
        self,
        prompt: str,
        *,
        grammar_schema: dict[str, Any],
        max_tokens: int = 256,
    ) -> str:
        _ = grammar_schema, max_tokens
        self.calls.append(prompt)
        time.sleep(self.simulate_cpu_ms / 1000.0)
        if self._responder is not None:
            payload = self._responder(prompt, self._last_candidate)
        else:
            candidate = self._last_candidate
            payload = {
                "decision_id": candidate.node_id,
                "cluster_id": "cluster-graviton4",
                "node_id": candidate.node_id,
                "timestamp": datetime.now(UTC).isoformat(),
                "action": candidate.action.value,
                "confidence": candidate.confidence,
                "reasoning": candidate.reasoning,
                "parameters": candidate.parameters,
                "snapshot_hash": "",
                "quorum_required": candidate.quorum_required,
            }
        return json.dumps(payload)

    def set_candidate(self, candidate: DecisionCandidate) -> None:
        self._last_candidate = candidate


def _snapshot_hash(snapshot: TelemetrySnapshot) -> str:
    digest = hashlib.sha256(
        snapshot.model_dump_json().encode(),
    ).hexdigest()
    return digest[:16]


def _build_prompt(snapshot: TelemetrySnapshot, candidate: DecisionCandidate) -> str:
    node_summaries = []
    for node in snapshot.nodes:
        node_summaries.append(
            f"{node.node_id}: sve2={node.sve2_utilization_pct:.1f}% "
            f"ttft={node.ttft_p99_ms:.0f}ms dram={node.dram_bandwidth_pct:.1f}% "
            f"kv_evict={node.kv_eviction_rate:.1f}"
        )
    return (
        "You are NeoSentinel, an autonomous Graviton4 cluster healing agent.\n"
        f"Cluster: {snapshot.cluster_id}\n"
        f"Nodes:\n- " + "\n- ".join(node_summaries) + "\n"
        f"Proposed action: {candidate.action.value} on {candidate.node_id}\n"
        f"Reason: {candidate.reasoning}\n"
        "Respond with a single JSON SentinelDecision object."
    )


class AgentBrain:
    def __init__(
        self,
        backend: LlamaCppBackend,
        *,
        cluster_id: str = "cluster-graviton4",
        cpu_budget_pct: float = CPU_BUDGET_PCT,
    ) -> None:
        self._backend = backend
        self.cluster_id = cluster_id
        self.cpu_budget_pct = cpu_budget_pct
        self.stats = BrainStats()

    def decide(self, snapshot: TelemetrySnapshot) -> SentinelDecision:
        started = time.perf_counter()
        candidate = evaluate_snapshot(snapshot)
        if isinstance(self._backend, MockLlamaCppBackend):
            self._backend.set_candidate(candidate)

        from neosentinel.schemas.decision import grammar_json_schema

        schema = grammar_json_schema()
        prompt = _build_prompt(snapshot, candidate)
        raw = self._backend.complete(prompt, grammar_schema=schema)

        try:
            decision = decode_grammar_constrained(raw)
        except Exception:
            self.stats.grammar_rejections += 1
            decision = self._fallback_decision(snapshot, candidate)

        elapsed_ms = (time.perf_counter() - started) * 1000.0
        self.stats.total_cpu_time_ms += elapsed_ms
        self.stats.decisions_made += 1

        finalized = decision.model_copy(
            update={
                "decision_id": new_decision_id(),
                "cluster_id": self.cluster_id,
                "timestamp": datetime.now(UTC),
                "snapshot_hash": _snapshot_hash(snapshot),
            }
        )
        self.stats.last_decision_id = finalized.decision_id
        return finalized

    def _fallback_decision(
        self,
        snapshot: TelemetrySnapshot,
        candidate: DecisionCandidate,
    ) -> SentinelDecision:
        return SentinelDecision(
            decision_id=new_decision_id(),
            cluster_id=self.cluster_id,
            node_id=candidate.node_id,
            timestamp=datetime.now(UTC),
            action=candidate.action,
            confidence=candidate.confidence,
            reasoning=candidate.reasoning,
            parameters=dict(candidate.parameters),
            snapshot_hash=_snapshot_hash(snapshot),
            quorum_required=candidate.quorum_required,
        )

    @property
    def avg_cpu_pct(self) -> float:
        if self.stats.decisions_made == 0:
            return 0.0
        avg_ms = self.stats.total_cpu_time_ms / self.stats.decisions_made
        return min(avg_ms / 300.0 * 100.0, 100.0)
