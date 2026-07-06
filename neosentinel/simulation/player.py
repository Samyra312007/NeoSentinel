"""Simulation player, injector, and replayer for NeoSentinel control plane."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Callable

from neosentinel.dashboard.mock_feed import MockTelemetryFeed
from neosentinel.simulation.catalog import get_scenario

FIXTURES_DIR = Path(__file__).resolve().parents[2] / "scenarios" / "fixtures"


def _load_fixture_events(scenario_name: str) -> list[dict[str, Any]] | None:
    fixture_path = FIXTURES_DIR / f"{scenario_name}.json"
    if not fixture_path.exists():
        return None
    return MockTelemetryFeed(fixtures_dir=FIXTURES_DIR).load_fixture(scenario_name)


def _fallback_events(scenario_name: str) -> list[dict[str, Any]]:
    scenario = get_scenario(scenario_name)
    return [
        {
            "type": "metrics",
            "timestamp": "2026-07-04T14:00:00Z",
            "cluster_id": "cluster-graviton4",
            "nodes": [
                {
                    "node_id": scenario.target_node,
                    "status": "degraded",
                    "ttft_p99_ms": scenario.initial_ttft_ms,
                    "tokens_per_sec": 18.5,
                    "sve2_utilization_pct": scenario.initial_sve2_pct,
                }
            ],
        },
        {
            "type": "agent_thought",
            "timestamp": "2026-07-04T14:00:02Z",
            "decision_id": f"dec-{scenario.name}",
            "node_id": scenario.target_node,
            "chunk": (
                f"Anomaly detected on {scenario.target_node}: "
                f"{scenario.description}. Executing {scenario.expected_action}."
            ),
            "done": True,
        },
        {
            "type": "healing",
            "timestamp": "2026-07-04T14:00:05Z",
            "healing_id": f"heal-{scenario.name}",
            "node_id": scenario.target_node,
            "action": scenario.expected_action,
            "status": "success",
            "before": {
                "ttft_p99_ms": scenario.initial_ttft_ms,
                "tokens_per_sec": 18.5,
                "sve2_utilization_pct": scenario.initial_sve2_pct,
                "dram_bandwidth_pct": 88.5,
                "cache_miss_rate_pct": 45.0,
                "kv_eviction_rate": 4.2,
                "requests_per_min": 340.0,
            },
            "after": {
                "ttft_p99_ms": scenario.recovered_ttft_ms,
                "tokens_per_sec": 44.8,
                "sve2_utilization_pct": scenario.recovered_sve2_pct,
                "dram_bandwidth_pct": 56.0,
                "cache_miss_rate_pct": 14.0,
                "kv_eviction_rate": 0.6,
                "requests_per_min": 340.0,
            },
            "duration_ms": 1500,
        },
        {
            "type": "audit",
            "timestamp": "2026-07-04T14:00:06Z",
            "commit_sha": "c0ffee1234567890abcdef1234567890abcdef12",
            "message": f"Auto-heal: applied {scenario.expected_action} on {scenario.target_node}",
            "node_id": scenario.target_node,
            "action": scenario.expected_action,
            "checkpoint_id": f"chk-{scenario.target_node}-20260704",
        },
    ]


def _resolve_events(scenario_name: str) -> list[dict[str, Any]]:
    events = _load_fixture_events(scenario_name)
    if events is not None:
        return events
    get_scenario(scenario_name)
    return _fallback_events(scenario_name)


def run_simulation(
    scenario_name: str,
    speed: float = 1.0,
    callback: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    if speed <= 0:
        raise ValueError("Speed multiplier must be positive.")

    scenario = get_scenario(scenario_name)
    events = _resolve_events(scenario_name)
    delay = 0.1 / speed

    for event in events:
        if callback:
            callback(event)
        time.sleep(delay)

    healing_events = [e for e in events if e.get("type") == "healing"]
    action_taken = healing_events[0]["action"] if healing_events else scenario.expected_action

    return {
        "status": "success",
        "scenario": scenario.name,
        "target_node": scenario.target_node,
        "action_taken": action_taken,
        "events_dispatched": len(events),
        "speed_multiplier": speed,
        "source": "fixture" if _load_fixture_events(scenario_name) else "synthetic",
    }


def inject_anomaly(
    node_id: str,
    anomaly_type: str,
    *,
    mock: bool = True,
) -> dict[str, Any]:
    if not node_id:
        raise ValueError("Target node_id must be specified.")

    try:
        scenario = get_scenario(anomaly_type)
        target_node = node_id
        description = scenario.description
    except ValueError:
        scenario = None
        target_node = node_id
        description = anomaly_type

    if not mock:
        from neosentinel.cli.daemons import inject_live_anomaly

        live = inject_live_anomaly(target_node, anomaly_type)
        return {
            **live,
            "message": (
                f"Synthetic anomaly '{anomaly_type}' injected on '{target_node}' "
                "via live adapter (Redis telemetry seeded)."
            ),
            "description": description if scenario else None,
        }

    mode = "mock"
    return {
        "status": "injected",
        "node_id": target_node,
        "anomaly_type": anomaly_type,
        "mode": mode,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "message": (
            f"Synthetic anomaly '{anomaly_type}' injected on '{target_node}' "
            f"via {mode} adapter."
        ),
        "description": description if scenario else None,
    }


def replay_stream(stream_name: str, speed: float = 1.0) -> list[dict[str, Any]]:
    if speed <= 0:
        raise ValueError("Speed multiplier must be positive.")

    scenario_name = stream_name.replace("cluster:telemetry:", "").replace("cluster:telemetry", "")
    scenario_name = scenario_name.strip(":") or "sve2_underutilization"
    events = _load_fixture_events(scenario_name)
    if events is None and scenario_name in {
        "sve2_underutilization",
        "kv_eviction_flood",
        "thermal_throttling",
        "memory_leak_degradation",
        "network_partition_latency",
    }:
        events = _resolve_events(scenario_name)

    if events is None:
        events = [
            {"id": "1001", "type": "metrics", "data": "nominal"},
            {"id": "1002", "type": "metrics", "data": "spike_detected"},
            {"id": "1003", "type": "healing", "data": "action_triggered"},
        ]

    delay = 0.05 / speed
    replayed: list[dict[str, Any]] = []
    for item in events:
        time.sleep(delay)
        replayed.append(item)
    return replayed
