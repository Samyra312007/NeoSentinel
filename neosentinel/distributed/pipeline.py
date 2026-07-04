from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass

from neosentinel.distributed.streams import TelemetryPipeline
from neosentinel.telemetry.mock_performix import MockPerformix
from neosentinel.telemetry.performix import PerformixDaemon, PmuFrame
from neosentinel.telemetry.vllm_scraper import VllmMetricsFrame, VllmMetricsScraper

PmuSource = PerformixDaemon | MockPerformix


@dataclass
class PipelineStats:
    pmu_published: int = 0
    vllm_published: int = 0
    last_pmu_id: str | None = None
    last_vllm_id: str | None = None


class TelemetryIngestionPipeline:
    def __init__(
        self,
        pipeline: TelemetryPipeline,
        pmu_source: PmuSource,
        vllm_scraper: VllmMetricsScraper,
        *,
        pmu_interval_s: float = 1.0,
        vllm_interval_s: float = 5.0,
        on_pmu: Callable[[PmuFrame, str], None] | None = None,
        on_vllm: Callable[[VllmMetricsFrame, str], None] | None = None,
    ) -> None:
        self._pipeline = pipeline
        self._pmu_source = pmu_source
        self._vllm_scraper = vllm_scraper
        self._pmu_interval_s = pmu_interval_s
        self._vllm_interval_s = vllm_interval_s
        self._on_pmu = on_pmu
        self._on_vllm = on_vllm
        self._last_vllm_at = -self._vllm_interval_s
        self.stats = PipelineStats()

    def _collect_pmu(self) -> PmuFrame:
        if isinstance(self._pmu_source, MockPerformix):
            return self._pmu_source.generate_frame()
        return self._pmu_source.collect_once()

    def publish_pmu_once(self) -> str:
        frame = self._collect_pmu()
        message_id = self._pipeline.publish_pmu(frame)
        self.stats.pmu_published += 1
        self.stats.last_pmu_id = message_id
        if self._on_pmu:
            self._on_pmu(frame, message_id)
        return message_id

    def publish_vllm_once(self) -> str:
        frame = self._vllm_scraper.scrape_once()
        message_id = self._pipeline.publish_vllm(frame)
        self.stats.vllm_published += 1
        self.stats.last_vllm_id = message_id
        if self._on_vllm:
            self._on_vllm(frame, message_id)
        return message_id

    def tick(self, *, now: float | None = None) -> tuple[str | None, str | None]:
        current = now if now is not None else time.monotonic()
        pmu_id = self.publish_pmu_once()
        vllm_id = None
        if current - self._last_vllm_at >= self._vllm_interval_s:
            vllm_id = self.publish_vllm_once()
            self._last_vllm_at = current
        return pmu_id, vllm_id

    def run_for(
        self,
        duration_s: float,
        *,
        clock: Callable[[], float] | None = None,
        sleeper: Callable[[float], None] | None = None,
    ) -> PipelineStats:
        monotonic = clock or time.monotonic
        sleep = sleeper or time.sleep
        deadline = monotonic() + duration_s
        self._last_vllm_at = monotonic() - self._vllm_interval_s
        while monotonic() < deadline:
            self.tick(now=monotonic())
            sleep(self._pmu_interval_s)
        return self.stats
