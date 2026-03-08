"""WebSocket endpoint for Runner connections.

Each Runner connects here, authenticates via headers (Easy Auth or dev mode),
and then enters a read loop where it sends heartbeats and tool responses.
"""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from .auth import require_user_ws
from .models import HeartbeatMessage, WireResponse
from .registry import registry

logger = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/runner/ws")
async def runner_ws(ws: WebSocket) -> None:
    """Accept a Runner WebSocket connection."""
    await ws.accept()

    # --- authenticate from headers ---
    raw_headers = {k.decode(): v.decode() for k, v in ws.scope.get("headers", [])}
    logger.debug("Runner WS headers: %s", {k: v for k, v in raw_headers.items() if k.startswith(("x-ms-", "x-dev-", "authorization"))})
    user = await require_user_ws(raw_headers)
    if user is None:
        logger.warning("Unauthenticated Runner connection rejected (no user_key derived from headers)")
        await ws.close(code=4003, reason="Authentication required")
        return

    user_key = user.key
    logger.info("Runner WS authenticated: user_key=%s", user_key)
    connection_id: str | None = None

    try:
        # First message from Runner should be a "hello" carrying metadata.
        hello_raw = await ws.receive_text()
        hello = json.loads(hello_raw)
        runner_version = hello.get("runner_version")
        device_name = hello.get("device_name")

        connection_id = await registry.register(
            user_key, ws, runner_version=runner_version, device_name=device_name
        )
        logger.info("Runner %s connected (conn=%s)", user_key, connection_id)

        # --- read loop ---
        while True:
            data = await ws.receive_text()
            msg = json.loads(data)
            msg_type = msg.get("type", "response")

            if msg_type == "heartbeat":
                hb = HeartbeatMessage(**msg)
                registry.update_heartbeat(user_key)
                logger.debug("Heartbeat from %s", user_key)
            else:
                # Treat as tool response.
                resp = WireResponse(**msg)
                registry.handle_response(user_key, resp)

    except WebSocketDisconnect:
        logger.info("Runner %s disconnected normally", user_key)
    except Exception:
        logger.exception("Runner WS error for %s", user_key)
    finally:
        if connection_id:
            await registry.unregister(user_key, connection_id)
