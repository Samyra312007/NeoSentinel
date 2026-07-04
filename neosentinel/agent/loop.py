from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass

from neosentinel.agent.brain import AgentBrain
from neosentinel.agent.snapshot import build_snapshot_from_redis
from neosentinel.contracts.decision import SentinelDecision
from neosentinel.distributed.streams import TelemetryPipeline

DEFAULT_INTERVAL_S = 30.0


@dataclass
class LoopStats:
    ticks: int = 0
    decisions_published: int = 0
    skipped_ticks: int = 0
    last_decision_id: str | None = None


class DecisionLoop:
    def __init__(
        self,
        pipeline: TelemetryPipeline,
        brain: AgentBrain,
        *,
        interval_s: float = DEFAULT_INTERVAL_S,
        cluster_id: str = "cluster-graviton4",
    ) -> None:
        self._pipeline = pipeline
        self._brain = brain
        self.interval_s = interval_s
        self.cluster_id = cluster_id
        self.stats = LoopStats()

    def tick(self) -> SentinelDecision | None:
        self.stats.ticks += 1
        snapshot = build_snapshot_from_redis(
            self._pipeline._client,
            cluster_id=self.cluster_id,
        )
        if snapshot is None:
            self.stats.skipped_ticks += 1
            return None

        decision = self._brain.decide(snapshot)
        message_id = self._pipeline.publish_decision(decision)
        self.stats.decisions_published += 1
        self.stats.last_decision_id = decision.decision_id
        _ = message_id
        return decision

    def run_for(
        self,
        duration_s: float,
        *,
        clock: Callable[[], float] | None = None,
        sleeper: Callable[[float], None] | None = None,
    ) -> LoopStats:
        monotonic = clock or time.monotonic
        sleep = sleeper or time.sleep
        deadline = monotonic() + duration_s
        while monotonic() < deadline:
            self.tick()
            sleep(self.interval_s)
        return self.stats
