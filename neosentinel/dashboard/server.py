from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from neosentinel.cli.config import load_local_config
from neosentinel.dashboard.broadcaster import TelemetryBroadcaster

_REPO_ROOT = Path(__file__).resolve().parents[2]
_UI_DIST = _REPO_ROOT / "dashboard-ui" / "dist"

app = FastAPI(title="NeoSentinel Dashboard API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _build_broadcaster() -> TelemetryBroadcaster:
    config = load_local_config(_REPO_ROOT)
    return TelemetryBroadcaster(
        use_redis=not config.mock_mode,
        redis_url=config.redis_url,
        redis_cluster=config.redis_cluster,
        cluster_id=config.cluster_id,
    )


broadcaster = _build_broadcaster()


@app.get("/health")
async def health_check() -> dict[str, str]:
    config = load_local_config(_REPO_ROOT)
    mode = "mock" if config.mock_mode else "live"
    return {"status": "ok", "service": "dashboard", "mode": mode}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    config = load_local_config(_REPO_ROOT)
    await broadcaster.connect(websocket)
    await broadcaster.start_streaming(
        scenario_name=config.scenario,
        delay_sec=1.5,
    )
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
            else:
                await websocket.send_json({"status": "received", "data": data})
    except WebSocketDisconnect:
        pass
    finally:
        broadcaster.disconnect(websocket)


def _mount_ui() -> None:
    if not _UI_DIST.is_dir():
        return
    assets_dir = _UI_DIST / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/")
    async def serve_index() -> FileResponse:
        return FileResponse(_UI_DIST / "index.html")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str) -> FileResponse:
        candidate = _UI_DIST / full_path
        if candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(_UI_DIST / "index.html")


_mount_ui()
