from __future__ import annotations

import random
from collections.abc import Iterator
from datetime import UTC, datetime

from neosentinel.contracts.telemetry import HotspotEntry
from neosentinel.telemetry.performix import PmuFrame

_DEFAULT_HOTSPOTS = (
    ("gemm_kernel", "vllm", 42.0),
    ("attention_fwd", "vllm", 18.5),
    ("kv_cache_update", "vllm", 12.3),
    ("rope_apply", "vllm", 8.1),
    ("sampler", "vllm", 5.4),
)


class MockPerformix:
    def __init__(
        self,
        node_id: str,
        *,
        sve2_base: float = 79.0,
        dram_base: float = 45.0,
        cache_miss_base: float = 3.2,
        seed: int | None = None,
    ) -> None:
        self.node_id = node_id
        self.sve2_base = sve2_base
        self.dram_base = dram_base
        self.cache_miss_base = cache_miss_base
        self._rng = random.Random(seed)

    def _jitter(self, base: float, spread: float) -> float:
        return round(base + self._rng.uniform(-spread, spread), 2)

    def generate_frame(self) -> PmuFrame:
        hotspots = tuple(
            HotspotEntry(
                symbol=symbol,
                samples_pct=round(pct + self._rng.uniform(-2.0, 2.0), 1),
                module=module,
            )
            for symbol, module, pct in _DEFAULT_HOTSPOTS
        )
        frame = PmuFrame(
            node_id=self.node_id,
            timestamp=datetime.now(UTC),
            sve2_utilization_pct=self._jitter(self.sve2_base, 5.0),
            dram_bandwidth_pct=self._jitter(self.dram_base, 8.0),
            cache_miss_rate_pct=self._jitter(self.cache_miss_base, 1.0),
            hotspots=hotspots,
        )
        frame.validate_stream_fields()
        return frame

    def stream(self, count: int) -> Iterator[PmuFrame]:
        for _ in range(count):
            yield self.generate_frame()

    def to_apx_text(self) -> str:
        frame = self.generate_frame()
        lines = [
            f"=== PMU Snapshot @ {frame.timestamp.strftime('%Y-%m-%dT%H:%M:%SZ')} ===",
            f"node_id: {frame.node_id}",
            f"sve2_utilization_pct: {frame.sve2_utilization_pct}",
            f"dram_bandwidth_pct: {frame.dram_bandwidth_pct}",
            f"cache_miss_rate_pct: {frame.cache_miss_rate_pct}",
            "",
            "=== Hotspots (top 5) ===",
        ]
        for h in frame.hotspots:
            lines.append(f"  {h.samples_pct}%  {h.symbol}  [{h.module}]")
        return "\n".join(lines) + "\n"
