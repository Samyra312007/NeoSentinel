import pytest

from neosentinel.telemetry.vllm_scraper import (
    VllmMetricsFrame,
    VllmMetricsScraper,
    parse_prometheus_metrics,
)

SAMPLE_METRICS = """\
# HELP vllm_ttft_p99_ms Time to first token p99
vllm_ttft_p99_ms{node="node-001"} 131.0
vllm_tokens_per_sec{node="node-001"} 842.0
vllm_kv_eviction_rate{node="node-001"} 0.1
vllm_requests_per_min{node="node-001"} 400.0
vllm_ttft_p99_ms{node="node-002"} 312.0
vllm_tokens_per_sec{node="node-002"} 510.0
vllm_kv_eviction_rate{node="node-002"} 2.4
vllm_requests_per_min{node="node-002"} 220.0
"""


class TestVllmScraperParser:
    def test_parse_metrics_for_node(self):
        frame = parse_prometheus_metrics(SAMPLE_METRICS, node_id="node-002")
        assert frame.node_id == "node-002"
        assert frame.ttft_p99_ms == 312.0
        assert frame.tokens_per_sec == 510.0
        assert frame.kv_eviction_rate == 2.4
        assert frame.requests_per_min == 220.0

    def test_parse_defaults_to_first_node(self):
        frame = parse_prometheus_metrics(SAMPLE_METRICS)
        assert frame.node_id == "node-001"

    def test_missing_counters_raises(self):
        with pytest.raises(ValueError, match="missing required counters"):
            parse_prometheus_metrics('vllm_ttft_p99_ms{node="node-001"} 131.0')

    def test_frame_stream_fields_valid(self):
        frame = parse_prometheus_metrics(SAMPLE_METRICS, node_id="node-001")
        fields = frame.to_stream_fields()
        assert fields["ttft_p99_ms"] == "131.0"
        assert fields["tokens_per_sec"] == "842.0"
        frame.validate_stream_fields()


class TestVllmMetricsScraper:
    def test_scrape_once_uses_fetcher(self):
        scraper = VllmMetricsScraper(
            "http://mock-vllm",
            "node-001",
            fetcher=lambda _url: SAMPLE_METRICS,
        )
        frame = scraper.scrape_once()
        assert isinstance(frame, VllmMetricsFrame)
        assert frame.ttft_p99_ms == 131.0

    def test_scrape_interval_default(self):
        scraper = VllmMetricsScraper("http://mock-vllm", "node-001")
        assert scraper.interval_s == 5.0

    def test_fetch_failure_raises(self):
        def fail(_url: str) -> str:
            raise OSError("connection refused")

        scraper = VllmMetricsScraper("http://mock-vllm", "node-001", fetcher=fail)
        with pytest.raises(RuntimeError, match="failed to fetch"):
            scraper.scrape_once()
