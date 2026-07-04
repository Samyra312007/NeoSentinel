from __future__ import annotations

import re
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import UTC, datetime

from neosentinel.contracts.streams import VLLM_STREAM_FIELDS

_METRIC_RE = re.compile(
    r"^vllm_(ttft_p99_ms|tokens_per_sec|kv_eviction_rate|requests_per_min)"
    r'\{node="([^"]+)"\}\s+([\d.eE+-]+)\s*$'
)


@dataclass(frozen=True)
class VllmMetricsFrame:
    node_id: str
    timestamp: datetime
    ttft_p99_ms: float
    tokens_per_sec: float
    kv_eviction_rate: float
    requests_per_min: float

    def to_stream_fields(self) -> dict[str, str]:
        return {
            "node_id": self.node_id,
            "timestamp": self.timestamp.isoformat(),
            "ttft_p99_ms": str(self.ttft_p99_ms),
            "tokens_per_sec": str(self.tokens_per_sec),
            "kv_eviction_rate": str(self.kv_eviction_rate),
            "requests_per_min": str(self.requests_per_min),
        }

    def validate_stream_fields(self) -> None:
        fields = {f.name for f in VLLM_STREAM_FIELDS if f.required}
        missing = fields - set(self.to_stream_fields())
        if missing:
            raise ValueError(f"vLLM frame missing required stream fields: {missing}")


def parse_prometheus_metrics(
    text: str,
    *,
    node_id: str | None = None,
    timestamp: datetime | None = None,
) -> VllmMetricsFrame:
    metrics: dict[str, float] = {}
    resolved_node = node_id

    for line in text.splitlines():
        match = _METRIC_RE.match(line.strip())
        if not match:
            continue
        metric_name, metric_node, value = match.group(1), match.group(2), float(match.group(3))
        if resolved_node is None:
            resolved_node = metric_node
        elif metric_node != resolved_node:
            continue
        metrics[metric_name] = value

    if resolved_node is None:
        raise ValueError("metrics text contains no vLLM counters")

    required = ("ttft_p99_ms", "tokens_per_sec", "kv_eviction_rate", "requests_per_min")
    missing = [name for name in required if name not in metrics]
    if missing:
        raise ValueError(f"metrics text missing required counters: {missing}")

    frame = VllmMetricsFrame(
        node_id=resolved_node,
        timestamp=timestamp or datetime.now(UTC),
        ttft_p99_ms=metrics["ttft_p99_ms"],
        tokens_per_sec=metrics["tokens_per_sec"],
        kv_eviction_rate=metrics["kv_eviction_rate"],
        requests_per_min=metrics["requests_per_min"],
    )
    frame.validate_stream_fields()
    return frame


class VllmMetricsScraper:
    def __init__(
        self,
        base_url: str,
        node_id: str,
        *,
        interval_s: float = 5.0,
        fetcher: Callable[[str], str] | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.node_id = node_id
        self.interval_s = interval_s
        self._fetcher = fetcher or self._default_fetcher

    def _default_fetcher(self, url: str) -> str:
        try:
            with urllib.request.urlopen(url, timeout=10) as resp:
                return resp.read().decode()
        except (urllib.error.URLError, OSError) as exc:
            raise RuntimeError(f"failed to fetch vLLM metrics from {url}") from exc

    def scrape_once(self) -> VllmMetricsFrame:
        url = f"{self.base_url}/metrics"
        try:
            text = self._fetcher(url)
        except RuntimeError:
            raise
        except (urllib.error.URLError, OSError) as exc:
            raise RuntimeError(f"failed to fetch vLLM metrics from {url}") from exc
        return parse_prometheus_metrics(text, node_id=self.node_id)

    def stream(self, *, max_frames: int | None = None) -> Iterator[VllmMetricsFrame]:
        count = 0
        while max_frames is None or count < max_frames:
            yield self.scrape_once()
            count += 1
            if max_frames is None or count < max_frames:
                time.sleep(self.interval_s)
