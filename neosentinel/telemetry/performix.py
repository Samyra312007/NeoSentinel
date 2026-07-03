from __future__ import annotations

import json
import re
import subprocess
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from neosentinel.contracts.streams import PMU_STREAM_FIELDS
from neosentinel.contracts.telemetry import HotspotEntry

_FLOAT_RE = re.compile(r"^([a-z0-9_]+):\s*([\d.]+)\s*$")
_HOTSPOT_RE = re.compile(r"^\s*([\d.]+)%\s+(\S+)\s+\[(\S+)\]\s*$")


@dataclass(frozen=True)
class PmuFrame:
    node_id: str
    timestamp: datetime
    sve2_utilization_pct: float
    dram_bandwidth_pct: float
    cache_miss_rate_pct: float
    hotspots: tuple[HotspotEntry, ...]

    def to_stream_fields(self) -> dict[str, str]:
        return {
            "node_id": self.node_id,
            "timestamp": self.timestamp.isoformat(),
            "sve2_utilization_pct": str(self.sve2_utilization_pct),
            "dram_bandwidth_pct": str(self.dram_bandwidth_pct),
            "cache_miss_rate_pct": str(self.cache_miss_rate_pct),
            "hotspots_json": json.dumps(
                [h.model_dump() for h in self.hotspots],
                separators=(",", ":"),
            ),
        }

    def validate_stream_fields(self) -> None:
        fields = {f.name for f in PMU_STREAM_FIELDS if f.required}
        missing = fields - set(self.to_stream_fields())
        if missing:
            raise ValueError(f"PMU frame missing required stream fields: {missing}")


def parse_apx_output(text: str, *, node_id: str = "node-001") -> PmuFrame:
    sve2 = dram = cache_miss = None
    hotspots: list[HotspotEntry] = []
    timestamp = datetime.now(UTC)
    in_hotspots = False

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("=== PMU Snapshot"):
            ts_match = re.search(r"@\s*(.+?)\s*===", stripped)
            if ts_match:
                timestamp = datetime.fromisoformat(ts_match.group(1).replace("Z", "+00:00"))
            continue
        if stripped.startswith("node_id:"):
            node_id = stripped.split(":", 1)[1].strip()
            continue
        if stripped.startswith("=== Hotspots"):
            in_hotspots = True
            continue
        if in_hotspots:
            match = _HOTSPOT_RE.match(stripped)
            if match:
                hotspots.append(
                    HotspotEntry(
                        symbol=match.group(2),
                        samples_pct=float(match.group(1)),
                        module=match.group(3),
                    )
                )
            continue
        match = _FLOAT_RE.match(stripped)
        if match:
            key, value = match.group(1), float(match.group(2))
            if key == "sve2_utilization_pct":
                sve2 = value
            elif key == "dram_bandwidth_pct":
                dram = value
            elif key == "cache_miss_rate_pct":
                cache_miss = value

    if sve2 is None or dram is None or cache_miss is None:
        raise ValueError("apx output missing required PMU counters")

    return PmuFrame(
        node_id=node_id,
        timestamp=timestamp,
        sve2_utilization_pct=sve2,
        dram_bandwidth_pct=dram,
        cache_miss_rate_pct=cache_miss,
        hotspots=tuple(hotspots[:5]),
    )


class PerformixDaemon:
    def __init__(
        self,
        node_id: str,
        apx_path: str | Path = "apx",
        interval_hz: float = 1.0,
        runner: Callable[[list[str]], str] | None = None,
    ) -> None:
        self.node_id = node_id
        self.apx_path = str(apx_path)
        self.interval_s = 1.0 / interval_hz
        self._runner = runner or self._default_runner

    def _default_runner(self, cmd: list[str]) -> str:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=30)
        return result.stdout

    def collect_once(self) -> PmuFrame:
        output = self._runner(
            [
                self.apx_path,
                "pmu",
                "collect",
                "--node",
                self.node_id,
                "--format",
                "text",
            ]
        )
        return parse_apx_output(output, node_id=self.node_id)

    def stream(self, *, max_frames: int | None = None) -> Iterator[PmuFrame]:
        count = 0
        while max_frames is None or count < max_frames:
            yield self.collect_once()
            count += 1
            if max_frames is None or count < max_frames:
                time.sleep(self.interval_s)
