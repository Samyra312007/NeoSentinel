"""Unit tests for NeoSentinel public SDK API (D5.1)."""

from typing import Any, Dict

from neosentinel.engine import (
    ClusterConfig,
    PerformixTarget,
    SentinelEngine,
    on_alert,
    register_action,
)


def test_sdk_classes_and_defaults() -> None:
    """Test PerformixTarget, ClusterConfig, and SentinelEngine initialization."""
    target = PerformixTarget(node_id="node-001", host="10.0.0.1", sve2_enabled=True)
    config = ClusterConfig(cluster_id="test-cluster", nodes=[target])
    engine = SentinelEngine(config)

    status = engine.get_cluster_status()
    assert status["cluster_id"] == "test-cluster"
    assert status["node_count"] == 1
    assert status["nodes"] == ["node-001"]
    assert status["status"] == "stopped"

    engine.start()
    assert engine.get_cluster_status()["status"] == "healthy"
    engine.stop()
    assert engine.get_cluster_status()["status"] == "stopped"


def test_decorators_and_trigger_healing() -> None:
    """Test @on_alert and @register_action decorators."""
    alerts_received = []

    @on_alert()
    def handle_alert(alert: Dict[str, Any]) -> None:
        alerts_received.append(alert)

    @register_action("custom_requantize")
    def custom_requantize(node_id: str, params: Dict[str, Any]) -> str:
        return f"Requantized {node_id} with bitwidth {params.get('bits', 8)}"

    engine = SentinelEngine()
    assert len(engine.alert_handlers) >= 1
    assert "custom_requantize" in engine.action_handlers

    res = engine.trigger_healing("node-002", "custom_requantize", {"bits": 4})
    assert res["status"] == "success"
    assert res["result"] == "Requantized node-002 with bitwidth 4"

    res_default = engine.trigger_healing("node-003", "standard_action")
    assert res_default["status"] == "success"
    assert "standard_action" in res_default["message"]
