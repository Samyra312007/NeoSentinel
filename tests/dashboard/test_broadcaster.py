import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import WebSocket, WebSocketDisconnect

from neosentinel.dashboard.broadcaster import TelemetryBroadcaster


@pytest.fixture
def mock_websocket() -> MagicMock:
    ws = MagicMock(spec=WebSocket)
    ws.accept = AsyncMock()
    ws.send_json = AsyncMock()
    ws.send_text = AsyncMock()
    return ws


@pytest.mark.asyncio
async def test_connect_and_disconnect(mock_websocket: MagicMock) -> None:
    broadcaster = TelemetryBroadcaster()
    assert len(broadcaster.active_connections) == 0

    await broadcaster.connect(mock_websocket)
    assert len(broadcaster.active_connections) == 1
    mock_websocket.accept.assert_awaited_once()

    broadcaster.disconnect(mock_websocket)
    assert len(broadcaster.active_connections) == 0


@pytest.mark.asyncio
async def test_broadcast_json_to_multiple_clients() -> None:
    broadcaster = TelemetryBroadcaster()
    ws1 = MagicMock(spec=WebSocket)
    ws1.send_json = AsyncMock()
    ws2 = MagicMock(spec=WebSocket)
    ws2.send_json = AsyncMock()

    broadcaster.active_connections.add(ws1)
    broadcaster.active_connections.add(ws2)

    msg = {"type": "test", "value": 123}
    count = await broadcaster.broadcast(msg)
    assert count == 2
    ws1.send_json.assert_awaited_once_with(msg)
    ws2.send_json.assert_awaited_once_with(msg)


@pytest.mark.asyncio
async def test_broadcast_removes_disconnected_clients() -> None:
    broadcaster = TelemetryBroadcaster()
    ws_good = MagicMock(spec=WebSocket)
    ws_good.send_text = AsyncMock()

    ws_bad = MagicMock(spec=WebSocket)
    ws_bad.send_text = AsyncMock(side_effect=WebSocketDisconnect())

    broadcaster.active_connections.add(ws_good)
    broadcaster.active_connections.add(ws_bad)

    count = await broadcaster.broadcast("ping")
    assert count == 1
    assert len(broadcaster.active_connections) == 1
    assert ws_good in broadcaster.active_connections
    assert ws_bad not in broadcaster.active_connections


@pytest.mark.asyncio
async def test_start_and_stop_streaming_mock() -> None:
    broadcaster = TelemetryBroadcaster(use_redis=False)
    ws = MagicMock(spec=WebSocket)
    ws.send_json = AsyncMock()
    broadcaster.active_connections.add(ws)

    await broadcaster.start_streaming("sve2_underutilization", delay_sec=0.1)
    await asyncio.sleep(0.7)
    await broadcaster.stop_streaming()

    assert ws.send_json.await_count >= 1
    assert not broadcaster._running


@pytest.mark.asyncio
async def test_start_streaming_redis_error() -> None:
    broadcaster = TelemetryBroadcaster(use_redis=True, redis_url="redis://invalid-host:12345")
    broadcaster._running = True
    with pytest.raises(
        RuntimeError, match="Failed to connect to Redis|Redis module is not installed"
    ):
        await broadcaster._stream_from_redis()
