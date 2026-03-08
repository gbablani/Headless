"""Pydantic models and configuration for the Runner."""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
class RunnerConfig(BaseModel):
    broker_url: str = os.getenv("BROKER_URL", "ws://localhost:8000/runner/ws")
    # Intranet site settings (single site).
    intranetStartUrl: str = os.getenv("INTRANET_START_URL", "https://login.microsoftonline.com")
    postLoginUrlPrefix: Optional[str] = os.getenv("POST_LOGIN_URL_PREFIX", None)
    session_ttl_minutes: int = int(os.getenv("SESSION_TTL_MINUTES", "480"))
    dom_max_text_length: int = int(os.getenv("DOM_MAX_TEXT_LENGTH", "200"))
    heartbeat_interval_seconds: int = int(os.getenv("HEARTBEAT_INTERVAL_SECONDS", "15"))
    # Entra client app registration for device-code flow.
    client_id: str = os.getenv("RUNNER_CLIENT_ID", "")
    tenant_id: str = os.getenv("RUNNER_TENANT_ID", "")
    broker_scope: str = os.getenv("RUNNER_BROKER_SCOPE", "")


# ---------------------------------------------------------------------------
# Wire protocol (mirrors broker models)
# ---------------------------------------------------------------------------
class WireRequest(BaseModel):
    request_id: str
    tool: str
    params: Dict[str, Any] = {}


class WireResponse(BaseModel):
    request_id: str
    success: bool
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class HeartbeatMessage(BaseModel):
    type: str = "heartbeat"
    runner_version: Optional[str] = None
    device_name: Optional[str] = None
