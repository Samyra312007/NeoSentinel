import json
import subprocess
import urllib.request
from pathlib import Path

from tests.conftest import requires_docker

HEALTH_CHECK_SCRIPT = (
    "import urllib.request; "
    "r=urllib.request.urlopen('http://localhost:8000/health'); "
    "print(r.read().decode())"
)


BASE_URL = "http://127.0.0.1"


class TestVllmDocumentation:
    def test_kleidiai_documented(self):
        readme = Path(__file__).resolve().parents[2] / "docker" / "vllm" / "README.md"
        text = readme.read_text()
        assert "KleidiAI" in text
        assert "Llama 3.2 7B" in text
        assert "INT4" in text


@requires_docker
class TestVllmEndpoint:
    def test_completion_via_traefik(self, compose_stack):
        req = urllib.request.Request(
            f"{BASE_URL}/v1/completions",
            data=json.dumps({"prompt": "hello", "max_tokens": 8}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            assert resp.status == 200
            body = json.loads(resp.read())
            assert body["object"] == "text_completion"
            assert len(body["choices"]) == 1
            assert "text" in body["choices"][0]

    def test_metrics_scrape_via_traefik(self, compose_stack):
        with urllib.request.urlopen(f"{BASE_URL}/metrics", timeout=10) as resp:
            text = resp.read().decode()
            assert "vllm_ttft_p99_ms" in text
            assert "vllm_tokens_per_sec" in text
            assert "vllm_kv_eviction_rate" in text

    def test_direct_worker_health(self, compose_stack):
        result = subprocess.run(
            [
                "docker",
                "exec",
                "neosentinel-vllm-1",
                "python",
                "-c",
                HEALTH_CHECK_SCRIPT,
            ],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        assert result.returncode == 0
        body = json.loads(result.stdout.strip())
        assert body["node_id"] == "node-001"
