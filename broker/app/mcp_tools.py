"""MCP tool surface exposed by the Broker to M365 Copilot (or any MCP client).

Each tool authenticates the caller, resolves the matching Runner, and
dispatches the request over WebSocket.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from .auth import require_user
from .models import (
    BootstrapLoginInput,
    BootstrapLoginOutput,
    BrokerError,
    ClickElementInput,
    ClickElementOutput,
    ErrorCode,
    InspectDomInput,
    InspectDomOutput,
    NavigateInput,
    NavigateOutput,
    ScreenshotInput,
    ScreenshotOutput,
    SelectElementInput,
    SelectElementOutput,
    SessionStatusInput,
    SessionStatusOutput,
    UserKey,
)
from .registry import DEFAULT_TIMEOUT_S, registry

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/mcp/tools", tags=["MCP Tools"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _error_response(code: ErrorCode, message: str, action: str | None = None, status: int = 502) -> JSONResponse:
    body = BrokerError(error=code, message=message, action=action)
    return JSONResponse(content=body.model_dump(), status_code=status)


async def _dispatch(user: UserKey, tool: str, params: Dict[str, Any]) -> JSONResponse:
    """Dispatch *tool* to the user's Runner and return the result."""
    user_key = user.key
    if not registry.is_connected(user_key):
        return _error_response(
            ErrorCode.RUNNER_NOT_CONNECTED,
            "Your local Runner is not connected. Start the Runner and try again.",
            status=503,
        )
    try:
        wire_resp = await registry.dispatch(user_key, tool, params)
    except TimeoutError:
        return _error_response(
            ErrorCode.ACTION_TIMEOUT,
            "The action did not complete in time. Retry or check VPN connectivity.",
        )
    except Exception as exc:
        logger.exception("Dispatch error for %s/%s", user_key, tool)
        return _error_response(ErrorCode.INTERNAL_ERROR, str(exc))

    if not wire_resp.success:
        error_text = wire_resp.error or "Unknown runner error"
        # Map specific runner errors.
        if "SESSION_NOT_AUTHENTICATED" in error_text:
            return _error_response(
                ErrorCode.SESSION_NOT_AUTHENTICATED,
                "You need to sign in to the intranet. A browser window will open on your machine.",
                action="BOOTSTRAP_REQUIRED",
            )
        if "BROWSER_RESTARTED" in error_text:
            return _error_response(
                ErrorCode.BROWSER_RESTARTED,
                "The browser was closed or crashed and has been restarted. "
                "All previous pages and element handles are gone. "
                "Please call bootstrapLogin or navigate again to continue.",
                action="RETRY",
                status=503,
            )
        if "BROWSER_CRASHED" in error_text:
            return _error_response(
                ErrorCode.INTERNAL_ERROR,
                "The browser crashed and could not be restarted automatically. "
                "Please restart the Runner manually.",
                status=503,
            )
        return _error_response(ErrorCode.INTERNAL_ERROR, error_text)

    return JSONResponse(content=wire_resp.result or {})


# ---------------------------------------------------------------------------
# Tool endpoints
# ---------------------------------------------------------------------------

@router.post("/sessionStatus")
async def session_status(body: SessionStatusInput, user: UserKey = Depends(require_user)):
    return await _dispatch(user, "sessionStatus", body.model_dump())


@router.post("/bootstrapLogin")
async def bootstrap_login(body: BootstrapLoginInput, user: UserKey = Depends(require_user)):
    return await _dispatch(user, "bootstrapLogin", body.model_dump())


@router.post("/navigate")
async def navigate(body: NavigateInput, user: UserKey = Depends(require_user)):
    return await _dispatch(user, "navigate", body.model_dump())


@router.post("/inspectDom")
async def inspect_dom(body: InspectDomInput, user: UserKey = Depends(require_user)):
    return await _dispatch(user, "inspectDom", body.model_dump())


@router.post("/selectElement")
async def select_element(body: SelectElementInput, user: UserKey = Depends(require_user)):
    return await _dispatch(user, "selectElement", body.model_dump())


@router.post("/clickElement")
async def click_element(body: ClickElementInput, user: UserKey = Depends(require_user)):
    return await _dispatch(user, "clickElement", body.model_dump())


@router.post("/screenshot")
async def screenshot(body: ScreenshotInput, user: UserKey = Depends(require_user)):
    return await _dispatch(user, "screenshot", body.model_dump())


# ---------------------------------------------------------------------------
# MCP manifest / tool list (for MCP discovery)
# ---------------------------------------------------------------------------

MCP_TOOLS_MANIFEST = [
    {
        "name": "sessionStatus",
        "description": "Check if the local Runner is connected and the intranet session is authenticated.",
        "inputSchema": SessionStatusInput.model_json_schema(),
    },
    {
        "name": "bootstrapLogin",
        "description": "Force an interactive login locally (headed Playwright) for the given site.",
        "inputSchema": BootstrapLoginInput.model_json_schema(),
    },
    {
        "name": "navigate",
        "description": "Navigate the active page within an authenticated session to the given URL.",
        "inputSchema": NavigateInput.model_json_schema(),
    },
    {
        "name": "inspectDom",
        "description": "Return a JSON representation of the DOM for the current page.",
        "inputSchema": InspectDomInput.model_json_schema(),
    },
    {
        "name": "selectElement",
        "description": "Resolve a CSS selector to a stable element handle reference.",
        "inputSchema": SelectElementInput.model_json_schema(),
    },
    {
        "name": "clickElement",
        "description": "Click a previously resolved element by its elementId.",
        "inputSchema": ClickElementInput.model_json_schema(),
    },
    {
        "name": "screenshot",
        "description": "Take a PNG screenshot of the current page for diagnostic purposes.",
        "inputSchema": ScreenshotInput.model_json_schema(),
    },
]


@router.get("/list")
async def list_tools(user: UserKey = Depends(require_user)):
    """Return the MCP tool manifest."""
    return {"tools": MCP_TOOLS_MANIFEST}
