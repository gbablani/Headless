"""Runner WebSocket handler for aiohttp (M365 Agents SDK server).

This is the aiohttp equivalent of ws_handler.py (which is FastAPI-based).
Both can coexist — the FastAPI version is used when running the standalone
broker, this one when running under the Agents SDK aiohttp server.
"""

from __future__ import annotations

import json
import logging
import os

import aiohttp
from aiohttp.web import Request, WebSocketResponse

from .models import HeartbeatMessage, WireResponse
from .registry import registry

logger = logging.getLogger(__name__)

_DEV_MODE = os.getenv("BROKER_DEV_MODE", "").lower() in ("1", "true", "yes")


def _extract_user_key(request: Request) -> str | None:
    """Extract user identity from request headers."""
    # Easy Auth headers.
    oid = request.headers.get("x-ms-token-aad-oid") or request.headers.get(
        "x-ms-client-principal-id"
    )
    tid = request.headers.get("x-ms-token-aad-tid")
    if oid and tid:
        return f"{tid}:{oid}"

    # Dev mode headers.
    if _DEV_MODE:
        tid = request.headers.get("x-dev-tid")
        oid = request.headers.get("x-dev-oid")
        if tid and oid:
            return f"{tid}:{oid}"

    return None


async def runner_ws_handler(request: Request) -> WebSocketResponse:
    """Handle an incoming Runner WebSocket connection (aiohttp)."""
    ws = WebSocketResponse()
    await ws.prepare(request)

    user_key = _extract_user_key(request)
    if user_key is None:
        logger.warning("Unauthenticated Runner connection rejected")
        await ws.close(code=4003, message=b"Authentication required")
        return ws

    connection_id: str | None = None

    try:
        # First message: hello with metadata.
        hello_raw = await ws.receive_str()
        hello = json.loads(hello_raw)
        runner_version = hello.get("runner_version")
        device_name = hello.get("device_name")

        # We need to wrap the aiohttp WebSocket to match the interface
        # expected by the registry (which uses .send_text()).
        ws_wrapper = _AiohttpWsWrapper(ws)

        connection_id = await registry.register(
            user_key, ws_wrapper, runner_version=runner_version, device_name=device_name
        )
        logger.info("Runner %s connected (conn=%s)", user_key, connection_id)

        # Read loop.
        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                data = json.loads(msg.data)
                msg_type = data.get("type", "response")

                if msg_type == "heartbeat":
                    registry.update_heartbeat(user_key)
                    logger.debug("Heartbeat from %s", user_key)
                else:
                    resp = WireResponse(**data)
                    registry.handle_response(user_key, resp)

            elif msg.type in (aiohttp.WSMsgType.ERROR, aiohttp.WSMsgType.CLOSE):
                break

    except Exception:
        logger.exception("Runner WS error for %s", user_key)
    finally:
        if connection_id:
            await registry.unregister(user_key, connection_id)
        logger.info("Runner %s disconnected", user_key)

    return ws


class _AiohttpWsWrapper:
    """Thin wrapper so aiohttp WebSocketResponse matches the interface
    used by the registry (which expects `await ws.send_text(str)` and
    `await ws.close(code=..., reason=...)`).
    """

    def __init__(self, ws: WebSocketResponse):
        self._ws = ws

    async def send_text(self, data: str) -> None:
        await self._ws.send_str(data)

    async def close(self, code: int = 1000, reason: str = "") -> None:
        await self._ws.close(code=code, message=reason.encode())
