
import yaml

from tests.conftest import COMPOSE_FILE, TRAEFIK_DYNAMIC, TRAEFIK_STATIC


class TestTraefikStaticConfig:
    def test_static_config_exists(self):
        assert TRAEFIK_STATIC.exists()

    def test_entry_points_defined(self):
        config = yaml.safe_load(TRAEFIK_STATIC.read_text())
        assert "web" in config["entryPoints"]
        assert config["entryPoints"]["web"]["address"] == ":80"

    def test_file_provider_watches_dynamic_dir(self):
        config = yaml.safe_load(TRAEFIK_STATIC.read_text())
        assert config["providers"]["file"]["directory"] == "/etc/traefik/dynamic"
        assert config["providers"]["file"]["watch"] is True


class TestTraefikDynamicConfig:
    def _load(self) -> dict:
        return yaml.safe_load(TRAEFIK_DYNAMIC.read_text())

    def test_round_robin_three_backends(self):
        servers = self._load()["http"]["services"]["vllm-lb"]["loadBalancer"]["servers"]
        assert len(servers) == 3
        urls = {s["url"] for s in servers}
        assert "http://vllm-worker-1:8000" in urls
        assert "http://vllm-worker-2:8000" in urls
        assert "http://vllm-worker-3:8000" in urls

    def test_health_check_interval_10s(self):
        hc = self._load()["http"]["services"]["vllm-lb"]["loadBalancer"]["healthCheck"]
        assert hc["interval"] == "10s"
        assert hc["path"] == "/health"

    def test_circuit_breaker_above_50_percent_errors(self):
        cb = self._load()["http"]["middlewares"]["circuit-breaker"]["circuitBreaker"]
        assert "0.50" in cb["expression"]

    def test_rate_limit_1000_per_minute(self):
        rl = self._load()["http"]["middlewares"]["rate-limit"]["rateLimit"]
        assert rl["average"] == 17
        assert rl["period"] == "1s"

    def test_completions_route_uses_middlewares(self):
        router = self._load()["http"]["routers"]["vllm-completions"]
        assert "rate-limit" in router["middlewares"]
        assert "circuit-breaker" in router["middlewares"]
        assert router["service"] == "vllm-lb"

    def test_compose_references_traefik_config(self):
        compose = yaml.safe_load(COMPOSE_FILE.read_text())
        traefik = compose["services"]["traefik"]
        volume_paths = [v.split(":")[0] for v in traefik["volumes"]]
        assert any("traefik.yml" in p for p in volume_paths)
        assert any("dynamic" in p for p in volume_paths)
