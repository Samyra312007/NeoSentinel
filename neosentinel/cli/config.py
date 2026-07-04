from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

CONFIG_DIR = Path(".neosentinel")
CONFIG_FILE = CONFIG_DIR / "config.json"


@dataclass(frozen=True)
class LocalConfig:
    cluster_id: str = "cluster-graviton4"
    dashboard_port: int = 8080
    redis_url: str = "redis://127.0.0.1:6379"
    mock_mode: bool = True

    def to_dict(self) -> dict[str, object]:
        return {
            "cluster_id": self.cluster_id,
            "dashboard_port": self.dashboard_port,
            "redis_url": self.redis_url,
            "mock_mode": self.mock_mode,
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
