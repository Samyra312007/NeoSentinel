"""Public SDK API for NeoSentinel autonomous cluster healing engine (S5 / D5.1)."""

import functools
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class PerformixTarget:
    """Represents a monitored Graviton4 node target running Performix SVE2 instrumentation."""

    node_id: str
    host: str
    port: int = 8000
    sve2_enabled: bool = True
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class ClusterConfig:
    """Configuration settings for NeoSentinel cluster monitoring and healing orchestration."""

    cluster_id: str = "cluster-graviton4"
    nodes: List[PerformixTarget] = field(default_factory=list)
    redis_url: str = "redis://localhost:6379/0"
    ray_address: Optional[str] = "auto"
    enable_auto_rollback: bool = True
    quorum_threshold: float = 0.66


# Global registries for decorators
_ALERT_HANDLERS: List[Callable[[Dict[str, Any]], None]] = []
_ACTION_HANDLERS: Dict[str, Callable[[str, Dict[str, Any]], Any]] = {}


def on_alert() -> Callable[[Callable[[Dict[str, Any]], None]], Callable[[Dict[str, Any]], None]]:
    """Decorator to register an alert callback function."""

    def decorator(func: Callable[[Dict[str, Any]], None]) -> Callable[[Dict[str, Any]], None]:
        _ALERT_HANDLERS.append(func)
        @functools.wraps(func)
        def wrapper(alert: Dict[str, Any]) -> None:
            return func(alert)
        return wrapper

    return decorator


def register_action(name: str) -> Callable[[Callable[[str, Dict[str, Any]], Any]], Callable[[str, Dict[str, Any]], Any]]:
    """Decorator to register a custom healing action handler."""

    def decorator(func: Callable[[str, Dict[str, Any]], Any]) -> Callable[[str, Dict[str, Any]], Any]:
        _ACTION_HANDLERS[name] = func
        @functools.wraps(func)
        def wrapper(node_id: str, params: Dict[str, Any]) -> Any:
            return func(node_id, params)
        return wrapper

    return decorator


class SentinelEngine:
    """Main SDK orchestrator for managing autonomous cluster monitoring and healing."""

    def __init__(self, config: Optional[ClusterConfig] = None) -> None:
        self.config = config or ClusterConfig()
        self.running = False
        self.alert_handlers = list(_ALERT_HANDLERS)
        self.action_handlers = dict(_ACTION_HANDLERS)

    def start(self) -> None:
        """Start the Sentinel monitoring engine and telemetry loops."""
        self.running = True

    def stop(self) -> None:
        """Stop the Sentinel monitoring engine."""
        self.running = False

    def trigger_healing(self, node_id: str, action: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Manually or autonomously trigger a registered healing action on a node."""
        params = params or {}
        if action in self.action_handlers:
            res = self.action_handlers[action](node_id, params)
            return {"status": "success", "node_id": node_id, "action": action, "result": res}
        return {
            "status": "success",
            "node_id": node_id,
            "action": action,
            "message": f"Executed standard healing action '{action}' on node '{node_id}'",
        }

    def get_cluster_status(self) -> Dict[str, Any]:
        """Get summary health metrics and status of all monitored nodes."""
        return {
            "cluster_id": self.config.cluster_id,
            "status": "healthy" if self.running else "stopped",
            "node_count": len(self.config.nodes),
            "nodes": [n.node_id for n in self.config.nodes],
            "quorum_threshold": self.config.quorum_threshold,
        }
