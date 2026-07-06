from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

CONFIG_DIR = Path(".neosentinel")
CONFIG_FILE = CONFIG_DIR / "config.json"


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class LocalConfig:
    cluster_id: str = "cluster-graviton4"
    dashboard_port: int = 8080
    redis_url: str = "redis://127.0.0.1:6379"
    mock_mode: bool = True
    redis_cluster: bool = False
    scenario: str = "sve2_underutilization"
    vllm_base_url: str = "http://127.0.0.1:8000"
    orchestrator_interval_s: float = 5.0
    node_hosts: tuple[str, ...] = ("node-001", "node-002", "node-003")

    def to_dict(self) -> dict[str, object]:
        return {
            "cluster_id": self.cluster_id,
            "dashboard_port": self.dashboard_port,
            "redis_url": self.redis_url,
            "mock_mode": self.mock_mode,
            "redis_cluster": self.redis_cluster,
            "scenario": self.scenario,
            "vllm_base_url": self.vllm_base_url,
            "orchestrator_interval_s": self.orchestrator_interval_s,
            "node_hosts": list(self.node_hosts),
        }


def init_local_config(root: Path | None = None) -> Path:
    base = root or Path.cwd()
    config_dir = base / CONFIG_DIR
    config_dir.mkdir(parents=True, exist_ok=True)
    config_path = config_dir / "config.json"
    if not config_path.exists():
        config_path.write_text(
            json.dumps(LocalConfig().to_dict(), indent=2),
            encoding="utf-8",
        )
    return config_path


def load_local_config(root: Path | None = None) -> LocalConfig:
    base = root or Path.cwd()
    config_path = base / CONFIG_FILE
    data: dict[str, object] = {}
    if config_path.exists():
        data = json.loads(config_path.read_text(encoding="utf-8"))

    mock_mode = _env_bool("NEOSENTINEL_MOCK_MODE", bool(data.get("mock_mode", True)))
    redis_cluster = _env_bool(
        "NEOSENTINEL_REDIS_CLUSTER",
        bool(data.get("redis_cluster", False)),
    )
    redis_url = os.environ.get("NEOSENTINEL_REDIS_URL") or str(
        data.get("redis_url", "redis://127.0.0.1:6379")
    )
    cluster_id = os.environ.get("NEOSENTINEL_CLUSTER_ID") or str(
        data.get("cluster_id", "cluster-graviton4")
    )
    scenario = os.environ.get("NEOSENTINEL_SCENARIO") or str(
        data.get("scenario", "sve2_underutilization")
    )
    vllm_base_url = os.environ.get("NEOSENTINEL_VLLM_URL") or str(
        data.get("vllm_base_url", "http://127.0.0.1:8000")
    )
    dashboard_port = int(
        os.environ.get("NEOSENTINEL_DASHBOARD_PORT", data.get("dashboard_port", 8080))
    )
    orchestrator_interval_s = float(
        os.environ.get(
            "NEOSENTINEL_ORCHESTRATOR_INTERVAL_S",
            data.get("orchestrator_interval_s", 5.0),
        )
    )
    raw_hosts = data.get("node_hosts", ["node-001", "node-002", "node-003"])
    if isinstance(raw_hosts, list):
        node_hosts = tuple(str(host) for host in raw_hosts)
    else:
        node_hosts = LocalConfig.node_hosts

    return LocalConfig(
        cluster_id=cluster_id,
        dashboard_port=dashboard_port,
        redis_url=redis_url,
        mock_mode=mock_mode,
        redis_cluster=redis_cluster,
        scenario=scenario,
        vllm_base_url=vllm_base_url,
        orchestrator_interval_s=orchestrator_interval_s,
        node_hosts=node_hosts,
    )
