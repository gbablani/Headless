"""Pydantic models shared across the Broker."""

from __future__ import annotations

import datetime as _dt
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Identity
# ---------------------------------------------------------------------------
class UserKey(BaseModel):
    """Unique user identity derived from Entra claims (tid + oid)."""

    tid: str
    oid: str

    @property
    def key(self) -> str:
        return f"{self.tid}:{self.oid}"


# ---------------------------------------------------------------------------
# Runner presence
# ---------------------------------------------------------------------------
class RunnerInfo(BaseModel):
    user_key: str
    connection_id: str
    connected_at: _dt.datetime = Field(default_factory=_dt.datetime.utcnow)
    last_seen_at: _dt.datetime = Field(default_factory=_dt.datetime.utcnow)
    runner_version: Optional[str] = None
    device_name: Optional[str] = None


# ---------------------------------------------------------------------------
# MCP tool IO
# ---------------------------------------------------------------------------
class SessionStatusInput(BaseModel):
    sessionId: str = "default"


class SessionStatusOutput(BaseModel):
    runnerConnected: bool
    authenticated: bool
    sessionId: str
    expiresAt: Optional[str] = None
    openPages: Optional[Dict[str, str]] = None


class BootstrapLoginInput(BaseModel):
    sessionId: str = "default"


class BootstrapLoginOutput(BaseModel):
    status: str = "BOOTSTRAP_COMPLETE"
    pageId: Optional[str] = None


class NavigateInput(BaseModel):
    sessionId: str = "default"
    url: str
    pageId: Optional[str] = None


class NavigateOutput(BaseModel):
    status: str = "ok"
    pageId: Optional[str] = None
    finalUrl: str


class InspectDomInput(BaseModel):
    sessionId: str = "default"
    pageId: Optional[str] = None
    url: Optional[str] = None


class DomNode(BaseModel):
    tag: str
    attrs: Dict[str, str] = {}
    text: str = ""
    nodeId: Optional[str] = None
    children: List["DomNode"] = []


DomNode.model_rebuild()


class InspectDomOutput(BaseModel):
    url: str
    title: str
    document: DomNode


class SelectElementInput(BaseModel):
    sessionId: str = "default"
    pageId: Optional[str] = None
    selector: str


class SelectElementOutput(BaseModel):
    elementId: str
    selector: str


class ClickElementInput(BaseModel):
    sessionId: str = "default"
    elementId: str


class ClickElementOutput(BaseModel):
    status: str = "ok"
    finalUrl: Optional[str] = None


class FillFieldInput(BaseModel):
    sessionId: str = "default"
    pageId: Optional[str] = None
    selector: Optional[str] = None
    elementId: Optional[str] = None
    value: str
    submit: bool = False


class FillFieldOutput(BaseModel):
    status: str = "ok"
    pageId: Optional[str] = None
    finalUrl: Optional[str] = None


class SubmitFormInput(BaseModel):
    sessionId: str = "default"
    pageId: Optional[str] = None
    formSelector: Optional[str] = None
    submitterSelector: Optional[str] = None


class SubmitFormOutput(BaseModel):
    status: str = "ok"
    pageId: Optional[str] = None
    finalUrl: Optional[str] = None


class ScreenshotInput(BaseModel):
    sessionId: str = "default"
    pageId: Optional[str] = None


class ScreenshotOutput(BaseModel):
    contentType: str = "image/png"
    base64: str


# ---------------------------------------------------------------------------
# Broker error envelope
# ---------------------------------------------------------------------------
class ErrorCode(str, Enum):
    RUNNER_NOT_CONNECTED = "RUNNER_NOT_CONNECTED"
    SESSION_NOT_AUTHENTICATED = "SESSION_NOT_AUTHENTICATED"
    BROWSER_RESTARTED = "BROWSER_RESTARTED"
    ACTION_TIMEOUT = "ACTION_TIMEOUT"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class BrokerError(BaseModel):
    error: ErrorCode
    message: str
    action: Optional[str] = None


# ---------------------------------------------------------------------------
# Wire protocol (Broker <-> Runner over WebSocket)
# ---------------------------------------------------------------------------
class WireRequest(BaseModel):
    """Message sent from Broker to Runner."""

    request_id: str
    tool: str
    params: Dict[str, Any] = {}


class WireResponse(BaseModel):
    """Message sent from Runner to Broker."""

    request_id: str
    success: bool
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class HeartbeatMessage(BaseModel):
    type: str = "heartbeat"
    runner_version: Optional[str] = None
    device_name: Optional[str] = None
