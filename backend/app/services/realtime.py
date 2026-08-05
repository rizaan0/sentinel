"""
Real-time delivery: Redis Pub/Sub -> WebSocket Gateway -> Admin Dashboard.

Architecture: `Transaction Completed Event` fans out in parallel to the
Monitoring Engine and to Redis Pub/Sub - this module owns the Redis side
and fans it out further to every connected admin WebSocket client. It is
fully decoupled from Monitoring: a slow or failing Monitoring Engine can
never delay the live feed.
"""
import asyncio
import json
import logging

import redis as redis_sync
import redis.asyncio as redis_async
from fastapi import WebSocket

from app.core.config import settings

logger = logging.getLogger("sentinel.realtime")

_sync_redis_client: redis_sync.Redis | None = None


def _get_sync_redis() -> redis_sync.Redis:
    global _sync_redis_client
    if _sync_redis_client is None:
        _sync_redis_client = redis_sync.Redis.from_url(settings.REDIS_URL)
    return _sync_redis_client


def publish_event(event_type: str, payload: dict) -> None:
    """Publishes a JSON event onto the admin live-feed Redis channel."""
    try:
        message = json.dumps({"type": event_type, "payload": payload}, default=str)
        _get_sync_redis().publish(settings.REDIS_TRANSACTION_CHANNEL, message)
    except Exception:  # noqa: BLE001
        # The live feed is best-effort; it must never break the caller
        # (payment flow or monitoring engine).
        logger.exception("Failed to publish realtime event %s", event_type)


class ConnectionManager:
    """Tracks WebSocket clients connected to *this* backend process."""

    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self._connections.discard(websocket)

    async def broadcast(self, message: str) -> None:
        stale: list[WebSocket] = []
        for connection in list(self._connections):
            try:
                await connection.send_text(message)
            except Exception:  # noqa: BLE001
                stale.append(connection)
        for connection in stale:
            self.disconnect(connection)


connection_manager = ConnectionManager()

_redis_listener_task: asyncio.Task | None = None


async def _redis_listener() -> None:
    client = redis_async.Redis.from_url(settings.REDIS_URL)
    pubsub = client.pubsub()
    await pubsub.subscribe(settings.REDIS_TRANSACTION_CHANNEL)
    try:
        async for message in pubsub.listen():
            if message.get("type") != "message":
                continue
            data = message["data"]
            if isinstance(data, bytes):
                data = data.decode("utf-8")
            await connection_manager.broadcast(data)
    except asyncio.CancelledError:
        pass
    finally:
        await pubsub.unsubscribe(settings.REDIS_TRANSACTION_CHANNEL)
        await client.aclose()


def start_redis_listener() -> None:
    global _redis_listener_task
    if _redis_listener_task is None or _redis_listener_task.done():
        _redis_listener_task = asyncio.create_task(_redis_listener())


async def stop_redis_listener() -> None:
    """
    Cancels and *awaits* the listener task so it's fully torn down before
    the caller (e.g. app shutdown) proceeds. This matters when the app is
    started/stopped repeatedly on different event loops (e.g. once per
    test), since a task from a closed loop can never be awaited later.
    """
    global _redis_listener_task
    if _redis_listener_task is not None:
        task = _redis_listener_task
        _redis_listener_task = None
        task.cancel()
        try:
            await task
        except (asyncio.CancelledError, Exception):  # noqa: BLE001
            pass
