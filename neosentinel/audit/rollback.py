from __future__ import annotations

from neosentinel.contracts.telemetry import BaselineMetrics

ROLLBACK_WINDOW_S = 90.0


class RollbackMonitor:
    def __init__(self, *, window_s: float = ROLLBACK_WINDOW_S) -> None:
        self.window_s = window_s

    def should_rollback(
        self,
        healed: BaselineMetrics,
        current: BaselineMetrics,
        *,
        elapsed_s: float,
    ) -> bool:
        if elapsed_s > self.window_s:
            return False
        ttft_worse = current.ttft_p99_ms > healed.ttft_p99_ms * 1.1
        sve2_worse = current.sve2_utilization_pct < healed.sve2_utilization_pct - 10.0
        tokens_worse = current.tokens_per_sec < healed.tokens_per_sec * 0.85
        return ttft_worse or sve2_worse or tokens_worse
