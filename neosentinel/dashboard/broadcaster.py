import asyncio
import logging
from typing import Any
from fastapi import WebSocket, WebSocketDisconnect
from neosentinel.dashboard.mock_feed import MockTelemetryFeed

logger = logging.getLogger(__name__)


class TelemetryBroadcaster:
    """Manages active WebSocket clients and broadcasts live telemetry from Mock feed or Redis."""

    def __init__(self, use_redis: bool = False, redis_url: str = "redis://localhost:6379") -> None:
        self.use_redis = use_redis
        self.redis_url = redis_url
        self.active_connections: set[WebSocket] = set()
        self._stream_task: asyncio.Task[None] | None = None
        self._running = False

    async def connect(self, websocket: WebSocket) -> None:
        """Accept a new WebSocket connection and track it."""
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.debug(f"Client connected. Active clients: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove a disconnected client from tracking."""
        self.active_connections.discard(websocket)
        logger.debug(f"Client disconnected. Active clients: {len(self.active_connections)}")

    async def broadcast(self, message: dict[str, Any] | str) -> int:
        """Broadcast an event to all connected clients concurrently.

        Returns the number of clients successfully reached.
        """
        if not self.active_connections:
            return 0

        to_remove: set[WebSocket] = set()
        successful = 0

        for connection in list(self.active_connections):
            try:
                if isinstance(message, str):
                    await connection.send_text(message)
                else:
                    await connection.send_json(message)
                successful += 1
            except (WebSocketDisconnect, RuntimeError, Exception) as err:
                logger.debug(f"Failed to send to client, removing: {err}")
                to_remove.add(connection)

        for connection in to_remove:
            self.disconnect(connection)

        return successful

    async def _stream_from_mock(self, scenario_name: str, delay_sec: float) -> None:
        """Stream simulated events from disk JSON fixtures."""
        feed = MockTelemetryFeed()
        await asyncio.sleep(0.5)
        while self._running:
            async for event in feed.stream_events(scenario_name, delay_sec=delay_sec):
                if not self._running:
                    break
                await self.broadcast(event)
            await asyncio.sleep(delay_sec)

    async def _stream_from_redis(self) -> None:
        """Stream telemetry events from Redis XREAD (Sahil's streams)."""
        try:
            import redis.asyncio as redis  # type: ignore[import-untyped, import-not-found]
        except ImportError as err:
            raise RuntimeError("Redis module is not installed for use_redis=True mode.") from err

        try:
            client = redis.from_url(self.redis_url)
            try:
                streams = {
                    "neosentinel:telemetry:pmu": "$",
                    "neosentinel:telemetry:vllm": "$",
                    "neosentinel:telemetry:decisions": "$",
                    "neosentinel:telemetry:healing": "$",
                }
                while self._running:
                    response = await client.xread(streams, count=10, block=100)
                    if response:
                        for _stream_name, messages in response:
                            for _msg_id, fields in messages:
                                event_data = {
                                    k.decode("utf-8") if isinstance(k, bytes) else k: (
                                        v.decode("utf-8") if isinstance(v, bytes) else v
                                    )
                                    for k, v in fields.items()
                                }
                                await self.broadcast(event_data)
                    await asyncio.sleep(0.01)
            finally:
                await client.aclose()
        except Exception as err:
            raise RuntimeError(f"Failed to connect to Redis or read stream: {err}") from err

    async def start_streaming(
        self, scenario_name: str = "sve2_underutilization", delay_sec: float = 1.0
    ) -> None:
        """Start the background broadcasting loop."""
        if self._running:
            return
        self._running = True

        if self.use_redis:
            self._stream_task = asyncio.create_task(self._stream_from_redis())
        else:
            self._stream_task = asyncio.create_task(
                self._stream_from_mock(scenario_name, delay_sec)
            )

    async def stop_streaming(self) -> None:
        """Stop the background broadcasting loop and disconnect clients."""
        self._running = False
        if self._stream_task and not self._stream_task.done():
            self._stream_task.cancel()
            try:
                await self._stream_task
            except asyncio.CancelledError:
                pass
        self._stream_task = None
