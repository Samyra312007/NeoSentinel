import asyncio
import time
import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import WebSocket
from neosentinel.dashboard.broadcaster import TelemetryBroadcaster


@pytest.mark.asyncio
async def test_websocket_broadcast_latency_under_50ms() -> None:
    """Verify that broadcasting telemetry events to clients completes in <50ms target latency."""
    broadcaster = TelemetryBroadcaster()
    num_clients = 10
    clients: list[MagicMock] = []

    received_timestamps: list[float] = []

    async def mock_send_json(data: dict) -> None:
        received_timestamps.append(time.perf_counter())

    for _ in range(num_clients):
        ws = MagicMock(spec=WebSocket)
        ws.send_json = AsyncMock(side_effect=mock_send_json)
        broadcaster.active_connections.add(ws)

    event_payload = {
        "type": "metrics",
        "timestamp": "2026-07-04T12:00:00Z",
        "cluster_id": "cluster-graviton4",
        "nodes": [],
    }

    start_time = time.perf_counter()
    count = await broadcaster.broadcast(event_payload)
    end_time = time.perf_counter()

    assert count == num_clients
    assert len(received_timestamps) == num_clients

    # Check total broadcast execution duration is under 50ms
    total_duration_ms = (end_time - start_time) * 1000
    assert total_duration_ms < 50.0, f"Broadcast duration exceeded 50ms: {total_duration_ms:.2f}ms"

    # Check each client received the message in under 50ms from start_time
    for idx, ts in enumerate(received_timestamps):
        client_latency_ms = (ts - start_time) * 1000
        assert (
            client_latency_ms < 50.0
        ), f"Client {idx} delivery latency exceeded 50ms: {client_latency_ms:.2f}ms"
