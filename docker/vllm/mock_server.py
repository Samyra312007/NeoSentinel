import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer

NODE_ID = os.environ.get("NODE_ID", "node-001")
MODEL = os.environ.get("VLLM_MODEL", "meta-llama/Llama-3.2-7B-Instruct")


class VllmMockHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        pass

    def _send_json(self, status: int, body: dict) -> None:
        payload = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _send_text(self, status: int, body: str, content_type: str = "text/plain") -> None:
        payload = body.encode()
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self) -> None:
        if self.path == "/health":
            self._send_json(200, {"status": "ok", "node_id": NODE_ID})
            return
        if self.path == "/metrics":
            metrics = (
                f'vllm_ttft_p99_ms{{node="{NODE_ID}"}} 131.0\n'
                f'vllm_tokens_per_sec{{node="{NODE_ID}"}} 842.0\n'
                f'vllm_kv_eviction_rate{{node="{NODE_ID}"}} 0.1\n'
                f'vllm_requests_per_min{{node="{NODE_ID}"}} 400.0\n'
            )
            self._send_text(200, metrics, "text/plain; version=0.0.4")
            return
        self._send_json(404, {"error": "not found"})

    def do_POST(self) -> None:
        if self.path != "/v1/completions":
            self._send_json(404, {"error": "not found"})
            return
        length = int(self.headers.get("Content-Length", 0))
        if length:
            self.rfile.read(length)
        self._send_json(
            200,
            {
                "id": f"cmpl-{NODE_ID}",
                "object": "text_completion",
                "model": MODEL,
                "choices": [
                    {
                        "text": "NeoSentinel mock completion.",
                        "index": 0,
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 12, "completion_tokens": 4, "total_tokens": 16},
            },
        )


def main() -> None:
    port = int(os.environ.get("PORT", "8000"))
    server = HTTPServer(("0.0.0.0", port), VllmMockHandler)
    server.serve_forever()


if __name__ == "__main__":
    main()
