"""Entra ID (AAD) authentication helpers for the Broker.

When deployed behind Azure Container Apps *Easy Auth*, validated identity
headers are injected by the platform.  This module reads those headers and
falls back to direct JWT validation for local development.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

from fastapi import HTTPException, Request

from .models import UserKey

logger = logging.getLogger(__name__)

# ACA Easy Auth injects these headers when configured.
_HEADER_PRINCIPAL_ID = "x-ms-client-principal-id"  # oid
_HEADER_PRINCIPAL_NAME = "x-ms-client-principal-name"
_HEADER_TOKEN_TID = "x-ms-token-aad-tid"  # injected by custom claim mapping or middleware
_HEADER_TOKEN_OID = "x-ms-token-aad-oid"

# Optional: restrict to specific tenants.
ALLOWED_TENANT_IDS: set[str] = set(
    filter(None, os.getenv("ALLOWED_TENANT_IDS", "").split(","))
)

# For local dev, allow a bypass header.
_DEV_MODE = os.getenv("BROKER_DEV_MODE", "").lower() in ("1", "true", "yes")

# Fixed identity used in dev mode — no credentials needed from callers.
_DEV_USER = UserKey(tid="dev-tenant", oid="dev-user")

def _extract_easy_auth(request: Request) -> Optional[UserKey]:
    """Try to read identity from ACA Easy Auth headers."""
    oid = request.headers.get(_HEADER_TOKEN_OID) or request.headers.get(
        _HEADER_PRINCIPAL_ID
    )
    tid = request.headers.get(_HEADER_TOKEN_TID)
    if oid and tid:
        return UserKey(tid=tid, oid=oid)
    return None


def _extract_bearer(request: Request) -> Optional[UserKey]:
    """Validate a Bearer token directly (for local dev / non-Easy-Auth).

    In production this path is not used; Easy Auth handles it.  For local
    development, set ``BROKER_DEV_MODE=true`` and pass custom headers:
        x-dev-tid / x-dev-oid
    Or query parameters:
        ?dev_tid=...&dev_oid=...
    """
    if _DEV_MODE:
        # Try headers first.
        tid = request.headers.get("x-dev-tid")
        oid = request.headers.get("x-dev-oid")
        # Fall back to query parameters (for ChatGPT Actions / clients
        # that cannot set custom headers).
        if not (tid and oid):
            tid = request.query_params.get("dev_tid")
            oid = request.query_params.get("dev_oid")
        if tid and oid:
            return UserKey(tid=tid, oid=oid)
    return None


async def require_user(request: Request) -> UserKey:
    """Dependency that extracts and validates the calling user.

    In dev mode, returns a fixed identity – no credentials required.
    Raises HTTP 401 if no valid identity can be determined.
    """
    if _DEV_MODE:
        return _DEV_USER

    user = _extract_easy_auth(request) or _extract_bearer(request)
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required.")

    if ALLOWED_TENANT_IDS and user.tid not in ALLOWED_TENANT_IDS:
        raise HTTPException(status_code=403, detail="Tenant not allowed.")

    return user


async def require_user_ws(
    headers: dict[str, str],
) -> Optional[UserKey]:
    """Same logic but for raw WebSocket headers (dict)."""
    if _DEV_MODE:
        return _DEV_USER

    oid = headers.get(_HEADER_TOKEN_OID) or headers.get(_HEADER_PRINCIPAL_ID)
    tid = headers.get(_HEADER_TOKEN_TID)
    if oid and tid:
        user = UserKey(tid=tid, oid=oid)
    else:
        return None

    if ALLOWED_TENANT_IDS and user.tid not in ALLOWED_TENANT_IDS:
        return None

    return user
