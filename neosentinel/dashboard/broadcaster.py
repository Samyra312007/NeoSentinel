import asyncio
import logging
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

from neosentinel.contracts.streams import (
    STREAM_DECISIONS,
    STREAM_HEALING,
    STREAM_PMU,
    STREAM_VLLM,
)
from neosentinel.dashboard.mock_feed import MockTelemetryFeed
from neosentinel.dashboard.redis_adapter import RedisStreamAdapter

logger = logging.getLogger(__name__)


class TelemetryBroadcaster:
    def __init__(
        self,
        use_redis: bool = False,
        redis_url: str = "redis://localhost:6379",
        *,
        redis_cluster: bool = False,
        cluster_id: str = "cluster-graviton4",
    ) -> None:
        self.use_redis = use_redis
        self.redis_url = redis_url
        self.redis_cluster = redis_cluster
        self.cluster_id = cluster_id
        self.active_connections: set[WebSocket] = set()
        self._stream_task: asyncio.Task[None] | None = None
        self._running = False

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.debug("Client connected. Active clients: %d", len(self.active_connections))

    def disconnect(self, websocket: WebSocket) -> None:
        self.active_connections.discard(websocket)
        logger.debug("Client disconnected. Active clients: %d", len(self.active_connections))

    async def broadcast(self, message: dict[str, Any] | str) -> int:
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
                logger.debug("Failed to send to client, removing: %s", err)
                to_remove.add(connection)

        for connection in to_remove:
            self.disconnect(connection)

        return successful

    async def _stream_from_mock(self, scenario_name: str, delay_sec: float) -> None:
        feed = MockTelemetryFeed()
        await asyncio.sleep(0.5)
        while self._running:
            async for event in feed.stream_events(scenario_name, delay_sec=delay_sec):
                if not self._running:
                    break
                await self.broadcast(event)
            await asyncio.sleep(delay_sec)

    async def _stream_from_redis(self) -> None:
        try:
            import redis.asyncio as aioredis
        except ImportError as err:
            raise RuntimeError("Redis module is not installed for use_redis=True mode.") from err

        adapter = RedisStreamAdapter(cluster_id=self.cluster_id)
        client = aioredis.from_url(self.redis_url, decode_responses=True)
        try:
            streams = {
                STREAM_PMU: "$",
                STREAM_VLLM: "$",
                STREAM_DECISIONS: "$",
                STREAM_HEALING: "$",
            }
            while self._running:
                response = await client.xread(streams, count=10, block=1000)
                if response:
                    for stream_name, messages in response:
                        name = (
                            stream_name.decode("utf-8")
                            if isinstance(stream_name, bytes)
                            else stream_name
                        )
                        for msg_id, fields in messages:
                            stream_id = (
                                msg_id.decode("utf-8") if isinstance(msg_id, bytes) else msg_id
                            )
                            streams[name] = stream_id
                            normalized = {
                                (
                                    k.decode("utf-8") if isinstance(k, bytes) else k
                                ): (
                                    v.decode("utf-8") if isinstance(v, bytes) else v
                                )
                                for k, v in fields.items()
                            }
                            for event in adapter.ingest(name, normalized):
                                await self.broadcast(event)
                await asyncio.sleep(0.01)
        except Exception as err:
            raise RuntimeError(f"Failed to connect to Redis or read stream: {err}") from err
        finally:
            await client.aclose()

    async def start_streaming(
        self, scenario_name: str = "sve2_underutilization", delay_sec: float = 1.0
    ) -> None:
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
        self._running = False
        if self._stream_task and not self._stream_task.done():
            self._stream_task.cancel()
            try:
                await self._stream_task
            except asyncio.CancelledError:
                pass
        self._stream_task = None
