"""In-memory registry of connected Runner WebSocket sessions."""

from __future__ import annotations

import asyncio
import datetime as _dt
import logging
import uuid
from typing import Any, Dict, Optional, Protocol

from .models import BrokerError, ErrorCode, RunnerInfo, WireRequest, WireResponse

logger = logging.getLogger(__name__)

# Default timeout waiting for a Runner response.
DEFAULT_TIMEOUT_S = float(__import__("os").getenv("BROKER_REQUEST_TIMEOUT_MS", "30000")) / 1000
MAX_INFLIGHT = int(__import__("os").getenv("MAX_INFLIGHT_PER_USER", "10"))


class WebSocketLike(Protocol):
    """Minimal interface for both FastAPI WebSocket and aiohttp wrapper."""

    async def send_text(self, data: str) -> None: ...
    async def close(self, code: int = 1000, reason: str = "") -> None: ...


class _RunnerConnection:
    """Wraps one Runner WebSocket plus its in-flight request map."""

    def __init__(self, ws: WebSocketLike, info: RunnerInfo):
        self.ws = ws
        self.info = info
        self._pending: Dict[str, asyncio.Future[WireResponse]] = {}

    # -- outbound -----------------------------------------------------------

    async def send_request(
        self, tool: str, params: dict[str, Any], timeout: float = DEFAULT_TIMEOUT_S
    ) -> WireResponse:
        if len(self._pending) >= MAX_INFLIGHT:
            raise RuntimeError("Too many in-flight requests for this user.")

        request_id = uuid.uuid4().hex
        wire = WireRequest(request_id=request_id, tool=tool, params=params)
        loop = asyncio.get_running_loop()
        fut: asyncio.Future[WireResponse] = loop.create_future()
        self._pending[request_id] = fut

        try:
            await self.ws.send_text(wire.model_dump_json())
            return await asyncio.wait_for(fut, timeout=timeout)
        except asyncio.TimeoutError:
            raise TimeoutError(f"Runner did not respond within {timeout}s")
        finally:
            self._pending.pop(request_id, None)

    # -- inbound ------------------------------------------------------------

    def resolve(self, response: WireResponse) -> None:
        fut = self._pending.get(response.request_id)
        if fut and not fut.done():
            fut.set_result(response)

    def cancel_all(self) -> None:
        for fut in self._pending.values():
            if not fut.done():
                fut.cancel()
        self._pending.clear()


class RunnerRegistry:
    """Thread-safe registry of Runner connections keyed by user_key."""

    def __init__(self) -> None:
        self._connections: Dict[str, _RunnerConnection] = {}
        self._lock = asyncio.Lock()

    # -- lifecycle ----------------------------------------------------------

    async def register(self, user_key: str, ws: WebSocketLike, **meta: Any) -> str:
        connection_id = uuid.uuid4().hex
        info = RunnerInfo(
            user_key=user_key,
            connection_id=connection_id,
            runner_version=meta.get("runner_version"),
            device_name=meta.get("device_name"),
        )
        async with self._lock:
            old = self._connections.pop(user_key, None)
            if old:
                logger.info("Replacing existing Runner for %s", user_key)
                old.cancel_all()
                try:
                    await old.ws.close(code=4001, reason="Replaced by new connection")
                except Exception:
                    pass
            self._connections[user_key] = _RunnerConnection(ws, info)
        logger.info("Runner registered: user=%s conn=%s", user_key, connection_id)
        return connection_id

    async def unregister(self, user_key: str, connection_id: str) -> None:
        async with self._lock:
            conn = self._connections.get(user_key)
            if conn and conn.info.connection_id == connection_id:
                conn.cancel_all()
                del self._connections[user_key]
                logger.info("Runner unregistered: user=%s", user_key)

    def is_connected(self, user_key: str) -> bool:
        return user_key in self._connections

    # -- dispatch -----------------------------------------------------------

    async def dispatch(
        self,
        user_key: str,
        tool: str,
        params: dict[str, Any],
        timeout: float = DEFAULT_TIMEOUT_S,
    ) -> WireResponse:
        conn = self._connections.get(user_key)
        if conn is None:
            raise LookupError("Runner not connected")
        return await conn.send_request(tool, params, timeout)

    # -- inbound from Runner ------------------------------------------------

    def handle_response(self, user_key: str, response: WireResponse) -> None:
        conn = self._connections.get(user_key)
        if conn:
            conn.resolve(response)

    def update_heartbeat(self, user_key: str) -> None:
        conn = self._connections.get(user_key)
        if conn:
            conn.info.last_seen_at = _dt.datetime.utcnow()


# Singleton used by the application.
registry = RunnerRegistry()
