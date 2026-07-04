from __future__ import annotations

from dataclasses import dataclass

from neosentinel.agent.brain import AgentBrain, MockLlamaCppBackend
from neosentinel.agent.decision_tree import evaluate_snapshot
from neosentinel.agent.synthetic import (
    SYNTHETIC_72HR_TICKS,
    HealthyTelemetryGenerator,
)
from neosentinel.contracts.decision import ActionType
from neosentinel.contracts.telemetry import TelemetrySnapshot

FALSE_POSITIVE_TARGET_PCT = 2.0


@dataclass(frozen=True)
class FalsePositiveReport:
    total_ticks: int
    false_positives: int
    false_positive_rate_pct: float

    @property
    def meets_target(self) -> bool:
        return self.false_positive_rate_pct < FALSE_POSITIVE_TARGET_PCT


def measure_decision_tree_false_positives(
    snapshots: list[TelemetrySnapshot],
) -> FalsePositiveReport:
    false_positives = 0
    for snapshot in snapshots:
        candidate = evaluate_snapshot(snapshot)
        if candidate.action != ActionType.NOOP:
            false_positives += 1
    total = len(snapshots)
    rate = (false_positives / total * 100.0) if total else 0.0
    return FalsePositiveReport(
        total_ticks=total,
        false_positives=false_positives,
        false_positive_rate_pct=rate,
    )


def measure_brain_false_positives(
    snapshots: list[TelemetrySnapshot],
    *,
    cluster_id: str = "cluster-graviton4",
) -> FalsePositiveReport:
    backend = MockLlamaCppBackend(simulate_cpu_ms=0.0)
    brain = AgentBrain(backend, cluster_id=cluster_id)
    false_positives = 0
    for snapshot in snapshots:
        decision = brain.decide(snapshot)
        if decision.action != ActionType.NOOP:
            false_positives += 1
    total = len(snapshots)
    rate = (false_positives / total * 100.0) if total else 0.0
    return FalsePositiveReport(
        total_ticks=total,
        false_positives=false_positives,
        false_positive_rate_pct=rate,
    )


def run_72hr_false_positive_audit(
    *,
    seed: int = 42,
    ticks: int = SYNTHETIC_72HR_TICKS,
    use_brain: bool = True,
) -> FalsePositiveReport:
    generator = HealthyTelemetryGenerator(seed=seed)
    snapshots = list(generator.stream_72hr(ticks=ticks))
    if use_brain:
        return measure_brain_false_positives(snapshots)
    return measure_decision_tree_false_positives(snapshots)
