from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from neosentinel.contracts.telemetry import HotspotEntry
from neosentinel.telemetry.performix import parse_apx_output

RecipeRunner = Callable[[list[str]], str]

_DEFAULT_HOTSPOTS = (
    ("gemm_kernel", "vllm", 42.0),
    ("attention_fwd", "vllm", 18.5),
    ("kv_cache_update", "vllm", 12.3),
)


def _mock_hotspots_output(node_id: str) -> str:
    lines = [
        "=== PMU Snapshot @ 2026-07-04T12:00:00Z ===",
        f"node_id: {node_id}",
        "sve2_utilization_pct: 29.0",
        "dram_bandwidth_pct: 88.5",
        "cache_miss_rate_pct: 45.0",
        "",
        "=== Hotspots (top 5) ===",
    ]
    for symbol, module, pct in _DEFAULT_HOTSPOTS:
        lines.append(f"  {pct}%  {symbol}  [{module}]")
    return "\n".join(lines) + "\n"


def _mock_bandwidth_output(node_id: str) -> str:
    return (
        f"=== Memory Bandwidth Report @ 2026-07-04T12:00:00Z ===\n"
        f"node_id: {node_id}\n"
        "dram_read_gbps: 180.5\n"
        "dram_write_gbps: 92.3\n"
        "l3_miss_rate_pct: 12.4\n"
        "sve2_utilization_pct: 29.0\n"
        "dram_bandwidth_pct: 88.5\n"
        "cache_miss_rate_pct: 45.0\n"
    )


@dataclass(frozen=True)
class PerformixRecipeReport:
    recipe: str
    node_id: str
    hotspots: tuple[HotspotEntry, ...]
    dram_bandwidth_pct: float
    cache_miss_rate_pct: float
    sve2_utilization_pct: float
    raw_output: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "recipe": self.recipe,
            "node_id": self.node_id,
            "hotspots": [h.model_dump() for h in self.hotspots],
            "dram_bandwidth_pct": self.dram_bandwidth_pct,
            "cache_miss_rate_pct": self.cache_miss_rate_pct,
            "sve2_utilization_pct": self.sve2_utilization_pct,
        }


def run_code_hotspots(
    node_id: str,
    *,
    apx_path: str = "apx",
    runner: RecipeRunner | None = None,
) -> PerformixRecipeReport:
    execute = runner or (lambda cmd: _mock_hotspots_output(node_id))
    output = execute(
        [apx_path, "recipe", "code_hotspots", "--node", node_id, "--format", "text"]
    )
    frame = parse_apx_output(output, node_id=node_id)
    return PerformixRecipeReport(
        recipe="code_hotspots",
        node_id=node_id,
        hotspots=frame.hotspots,
        dram_bandwidth_pct=frame.dram_bandwidth_pct,
        cache_miss_rate_pct=frame.cache_miss_rate_pct,
        sve2_utilization_pct=frame.sve2_utilization_pct,
        raw_output=output,
    )


def run_memory_bandwidth(
    node_id: str,
    *,
    apx_path: str = "apx",
    runner: RecipeRunner | None = None,
) -> PerformixRecipeReport:
    execute = runner or (lambda cmd: _mock_bandwidth_output(node_id))
    output = execute(
        [apx_path, "recipe", "memory_bandwidth", "--node", node_id, "--format", "text"]
    )
    frame = parse_apx_output(output, node_id=node_id)
    return PerformixRecipeReport(
        recipe="memory_bandwidth",
        node_id=node_id,
        hotspots=frame.hotspots,
        dram_bandwidth_pct=frame.dram_bandwidth_pct,
        cache_miss_rate_pct=frame.cache_miss_rate_pct,
        sve2_utilization_pct=frame.sve2_utilization_pct,
        raw_output=output,
    )


def parse_recipe_json(text: str) -> dict[str, Any]:
    return json.loads(text)
