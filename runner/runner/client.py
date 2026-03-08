"""WebSocket client that connects to the Broker and processes commands."""

from __future__ import annotations

import asyncio
import json
import logging
import socket
from typing import Optional

import websockets  # type: ignore

from .browser import BrowserManager
from .models import HeartbeatMessage, RunnerConfig, WireRequest, WireResponse
from .tools import dispatch_tool

logger = logging.getLogger(__name__)


class RunnerClient:
    """Persistent WebSocket client that talks to the ACA MCP Broker."""

    def __init__(self, config: RunnerConfig, bm: BrowserManager, access_token: str):
        self.config = config
        self.bm = bm
        self.access_token = access_token
        self._ws: Optional[websockets.WebSocketClientProtocol] = None  # type: ignore[name-defined]
        self._running = False

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------

    async def connect(self) -> None:
        """Connect to the Broker WebSocket and enter the read loop."""
        self._running = True
        extra_headers = self._auth_headers()

        while self._running:
            try:
                logger.info("Connecting to Broker at %s …", self.config.broker_url)
                async with websockets.connect(
                    self.config.broker_url,
                    extra_headers=extra_headers,
                    ping_interval=30,
                    ping_timeout=10,
                    close_timeout=5,
                ) as ws:
                    self._ws = ws
                    await self._send_hello()
                    # Start heartbeat in background.
                    hb_task = asyncio.create_task(self._heartbeat_loop())
                    try:
                        await self._read_loop()
                    finally:
                        hb_task.cancel()
                        self._ws = None
            except (
                websockets.ConnectionClosed,
                ConnectionRefusedError,
                OSError,
            ) as exc:
                logger.warning("Connection lost (%s). Reconnecting in 5s…", exc)
                await asyncio.sleep(5)
            except Exception:
                logger.exception("Unexpected error. Reconnecting in 10s…")
                await asyncio.sleep(10)

    async def disconnect(self) -> None:
        self._running = False
        if self._ws:
            await self._ws.close()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _auth_headers(self) -> dict[str, str]:
        """Build authentication headers for the Broker."""
        # In production behind Easy Auth, the Runner authenticates via Entra
        # and the platform injects identity headers.  For dev mode we pass
        # custom dev headers.
        if self.access_token.startswith("dev:"):
            # dev:<tid>:<oid>
            parts = self.access_token.split(":")
            return {
                "x-dev-tid": parts[1],
                "x-dev-oid": parts[2],
            }
        # Real token – the ACA sidecar will validate and inject headers.
        return {"Authorization": f"Bearer {self.access_token}"}

    async def _send_hello(self) -> None:
        hello = {
            "type": "hello",
            "runner_version": "0.1.0",
            "device_name": socket.gethostname(),
        }
        assert self._ws is not None
        await self._ws.send(json.dumps(hello))
        logger.info("Sent hello to Broker")

    async def _heartbeat_loop(self) -> None:
        interval = self.config.heartbeat_interval_seconds
        while self._running and self._ws:
            try:
                hb = HeartbeatMessage(runner_version="0.1.0", device_name=socket.gethostname())
                await self._ws.send(hb.model_dump_json())
            except Exception:
                break
            await asyncio.sleep(interval)

    async def _read_loop(self) -> None:
        assert self._ws is not None
        async for raw in self._ws:
            try:
                msg = json.loads(raw)
                if "tool" in msg:
                    asyncio.create_task(self._handle_request(msg))
                else:
                    logger.debug("Unknown message: %s", msg)
            except Exception:
                logger.exception("Error processing message")

    async def _handle_request(self, raw: dict) -> None:
        req = WireRequest(**raw)
        try:
            result = await dispatch_tool(self.bm, req.tool, req.params)
            resp = WireResponse(request_id=req.request_id, success=True, result=result)
        except Exception as exc:
            logger.exception("Tool %s failed", req.tool)
            resp = WireResponse(request_id=req.request_id, success=False, error=str(exc))
        if self._ws:
            await self._ws.send(resp.model_dump_json())
