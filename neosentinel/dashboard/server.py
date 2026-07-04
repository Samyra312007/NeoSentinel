import asyncio
import json
from typing import Any
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="NeoSentinel Dashboard API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Dashboard liveness probe."""
    return {"status": "healthy", "service": "dashboard"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """Live dashboard WebSocket event stream stub."""
    await websocket.accept()
    try:
        while True:
            # Wait for client message or ping
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
            else:
                await websocket.send_json({"status": "received", "data": data})
    except WebSocketDisconnect:
        pass
