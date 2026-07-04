"""Simulation player, injector, and replayer for NeoSentinel control plane."""

import time
from typing import Any, Callable, Dict, List, Optional

from neosentinel.simulation.catalog import get_scenario


def run_simulation(
    scenario_name: str,
    speed: float = 1.0,
    callback: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> Dict[str, Any]:
    """Execute an end-to-end simulation of an anomaly and autonomous healing workflow."""
    if speed <= 0:
        raise ValueError("Speed multiplier must be positive.")

    scenario = get_scenario(scenario_name)
    delay = 1.0 / speed

    events: List[Dict[str, Any]] = [
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
                "sve2_utilization_pct": scenario.initial_sve2_pct,
            },
            "after": {
                "ttft_p99_ms": scenario.recovered_ttft_ms,
                "sve2_utilization_pct": scenario.recovered_sve2_pct,
            },
            "duration_ms": int(1500 / speed),
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

    for event in events:
        if callback:
            callback(event)
        time.sleep(delay * 0.1)  # scaled sleep for responsiveness

    return {
        "status": "success",
        "scenario": scenario.name,
        "target_node": scenario.target_node,
        "action_taken": scenario.expected_action,
        "events_dispatched": len(events),
        "speed_multiplier": speed,
    }


def inject_anomaly(node_id: str, anomaly_type: str) -> Dict[str, Any]:
    """Inject synthetic degradation on a target cluster node."""
    if not node_id:
        raise ValueError("Target node_id must be specified.")

    return {
        "status": "injected",
        "node_id": node_id,
        "anomaly_type": anomaly_type,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "message": f"Synthetic anomaly '{anomaly_type}' successfully injected on node '{node_id}'.",
    }


def replay_stream(stream_name: str, speed: float = 1.0) -> List[Dict[str, Any]]:
    """Replay historical telemetry stream window at N× speed."""
    if speed <= 0:
        raise ValueError("Speed multiplier must be positive.")

    mock_stream = [
        {"id": "1001", "type": "metrics", "data": "nominal"},
        {"id": "1002", "type": "metrics", "data": "spike_detected"},
        {"id": "1003", "type": "healing", "data": "action_triggered"},
    ]

    delay = 0.05 / speed
    replayed = []
    for item in mock_stream:
        time.sleep(delay)
        replayed.append(item)

    return replayed
