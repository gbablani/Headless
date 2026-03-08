"""Entra ID authentication for the Runner (device-code flow).

The Runner authenticates to the Broker with an Entra access token so the
Broker can map the WebSocket connection to a ``(tid, oid)`` identity.

Tokens are cached via MSAL's built-in serialization so the user only needs
to perform the interactive device-code flow once.
"""

from __future__ import annotations

import json
import logging
import os
import platform
from pathlib import Path

import msal  # type: ignore

logger = logging.getLogger(__name__)

_IS_WINDOWS = platform.system() == "Windows"
_CACHE_DIR = Path(
    os.getenv("LOCALAPPDATA", os.path.expanduser("~")),
    "HeadlessRunner" if _IS_WINDOWS else ".headless_runner",
)
_CACHE_FILE = _CACHE_DIR / "msal_token_cache.bin"


def _load_cache() -> msal.SerializableTokenCache:
    cache = msal.SerializableTokenCache()
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    if _CACHE_FILE.exists():
        cache.deserialize(_CACHE_FILE.read_text(encoding="utf-8"))
    return cache


def _save_cache(cache: msal.SerializableTokenCache) -> None:
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    _CACHE_FILE.write_text(cache.serialize(), encoding="utf-8")


def get_access_token(
    client_id: str,
    tenant_id: str,
    scopes: list[str],
) -> str:
    """Obtain an access token for the Broker, using device-code flow if needed.

    Returns the raw access token string.
    """
    authority = f"https://login.microsoftonline.com/{tenant_id}"
    cache = _load_cache()
    app = msal.PublicClientApplication(
        client_id,
        authority=authority,
        token_cache=cache,
    )

    # Try silent first.
    accounts = app.get_accounts()
    if accounts:
        result = app.acquire_token_silent(scopes, account=accounts[0])
        if result and "access_token" in result:
            _save_cache(cache)
            return result["access_token"]

    # Fall back to device-code flow.
    flow = app.initiate_device_flow(scopes)
    if "user_code" not in flow:
        raise RuntimeError(f"Device-code flow initiation failed: {flow}")

    print("\n" + "=" * 60)
    print("  AUTHENTICATION REQUIRED")
    print(f"  Go to:  {flow['verification_uri']}")
    print(f"  Enter code:  {flow['user_code']}")
    print("=" * 60 + "\n")

    result = app.acquire_token_by_device_flow(flow)
    if "access_token" not in result:
        raise RuntimeError(f"Authentication failed: {result.get('error_description', result)}")

    _save_cache(cache)
    return result["access_token"]
