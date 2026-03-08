# app.py
"""M365 Agents SDK entry point for the Intranet Browser Agent.

This agent receives conversational messages from M365 Copilot / Teams and
translates them into MCP tool calls dispatched to the user's local Runner.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env before anything reads env vars.
load_dotenv(Path(__file__).resolve().parent / ".env")

from microsoft_agents.hosting.core import (
    AgentApplication,
    TurnState,
    TurnContext,
    MemoryStorage,
)
from microsoft_agents.hosting.aiohttp import CloudAdapter

from start_server import start_server
from app.registry import registry
from app.models import ErrorCode

logging.basicConfig(
    level=logging.DEBUG if os.getenv("BROKER_DEV_MODE") else logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)

_dev = os.getenv("BROKER_DEV_MODE", "").lower() in ("1", "true", "yes")
if _dev:
    logger.warning("Broker running in DEV MODE")
else:
    logger.info("Broker running in PRODUCTION mode")


# ---------------------------------------------------------------------------
# Agent Application
# ---------------------------------------------------------------------------

AGENT_APP = AgentApplication[TurnState](
    storage=MemoryStorage(), adapter=CloudAdapter()
)

# Default user key for dev mode (Runner connects with this identity).
_DEV_USER_KEY = "dev-tenant:dev-user"


def _user_key_from_context(context: TurnContext) -> str:
    """Extract a user key from the conversation context.

    In production the identity comes from Entra claims on the activity.
    In dev mode we always use the fixed dev key so it matches the Runner.
    """
    if _dev:
        logger.debug("Dev mode: using fixed user key %s", _DEV_USER_KEY)
        return _DEV_USER_KEY

    tid = None
    aad_oid = None

    # Try channel data for tenant id.
    cd = context.activity.channel_data
    if isinstance(cd, dict):
        tenant = cd.get("tenant") or {}
        if isinstance(tenant, dict):
            tid = tenant.get("id")

    # Try from_property for AAD object ID.
    from_prop = context.activity.from_property
    if from_prop:
        aad_oid = getattr(from_prop, "aad_object_id", None) or (
            from_prop.id if hasattr(from_prop, "id") else None
        )

    logger.debug("Resolved identity: tid=%s aad_oid=%s", tid, aad_oid)

    if tid and aad_oid:
        return f"{tid}:{aad_oid}"

    logger.warning("No Entra identity on activity and not in dev mode; no user key")
    return _DEV_USER_KEY


# ---------------------------------------------------------------------------
# Tool dispatch helper
# ---------------------------------------------------------------------------

async def _dispatch_tool(context: TurnContext, tool: str, params: dict) -> str:
    """Dispatch a tool call to the user's Runner and return a text result."""
    user_key = _user_key_from_context(context)

    if not registry.is_connected(user_key):
        return (
            "❌ Your local Runner is not connected. "
            "Please start the Runner on your Windows machine and try again.\n\n"
            "Run: `runner start` (or `runner start --dev` for dev mode)"
        )

    try:
        wire_resp = await registry.dispatch(user_key, tool, params)
    except TimeoutError:
        return "⏱️ The action did not complete in time. Check your VPN connectivity and retry."
    except Exception as exc:
        logger.exception("Dispatch error for %s/%s", user_key, tool)
        return f"❌ Error: {exc}"

    if not wire_resp.success:
        error_text = wire_resp.error or "Unknown error"
        if "SESSION_NOT_AUTHENTICATED" in error_text:
            return (
                "🔐 You need to sign in to the intranet first.\n\n"
                "Say **\"log me in\"** and I'll open a browser window on your machine."
            )
        if "BROWSER_RESTARTED" in error_text:
            return (
                "🔄 The browser was closed or crashed and has been restarted automatically.\n\n"
                "All previous pages and element handles are gone. "
                "Say **\"log me in\"** or **\"go to <url>\"** to start fresh."
            )
        if "BROWSER_CRASHED" in error_text:
            return (
                "💥 The browser crashed and could not be restarted. "
                "Please restart the Runner manually."
            )
        return f"❌ Runner error: {error_text}"

    return json.dumps(wire_resp.result, indent=2)


# ---------------------------------------------------------------------------
# Conversation handlers
# ---------------------------------------------------------------------------

HELP_TEXT = (
    "👋 **Intranet Browser Agent**\n\n"
    "I can browse intranet pages using a browser on your machine. Here's what I can do:\n\n"
    "- **Check status** — \"Is my session active?\"\n"
    "- **Log in** — \"Log me in to the intranet\"\n"
    "- **Navigate** — \"Go to https://portal.microsofticm.com/...\"\n"
    "- **Inspect page** — \"What's on the current page?\"\n"
    "- **Click** — \"Click the Active Outages link\"\n"
    "- **Screenshot** — \"Take a screenshot\"\n\n"
    "Make sure the **Runner** is running on your Windows machine."
)


async def _on_members_added(context: TurnContext, _: TurnState):
    await context.send_activity(HELP_TEXT)


AGENT_APP.conversation_update("membersAdded")(_on_members_added)
AGENT_APP.message("/help")(_on_members_added)


@AGENT_APP.activity("message")
async def on_message(context: TurnContext, _: TurnState):
    text = (context.activity.text or "").strip().lower()

    # --- Status ---
    if any(kw in text for kw in ["status", "connected", "session", "active"]):
        result = await _dispatch_tool(context, "sessionStatus", {})
        await context.send_activity(f"**Session Status:**\n```json\n{result}\n```")
        return

    # --- Bootstrap login ---
    if any(kw in text for kw in ["log me in", "login", "sign in", "bootstrap", "authenticate"]):
        await context.send_activity("🔐 Opening a browser window on your machine for sign-in. Please complete the login there.")
        result = await _dispatch_tool(context, "bootstrapLogin", {})
        await context.send_activity(f"Bootstrap result: {result}")
        return

    # --- Navigate ---
    if text.startswith(("go to ", "navigate to ", "open ")):
        # Extract URL from the message.
        url = text.split(maxsplit=2)[-1].strip()
        if not url.startswith("http"):
            url = "https://" + url
        result = await _dispatch_tool(context, "navigate", {
            "url": url,
        })
        await context.send_activity(f"**Navigation:**\n```json\n{result}\n```")
        return

    # --- Screenshot ---
    if any(kw in text for kw in ["screenshot", "screen shot", "capture", "snap"]):
        result = await _dispatch_tool(context, "screenshot", {})
        # Result is JSON with base64 — just confirm.
        try:
            data = json.loads(result)
            if "base64" in data:
                await context.send_activity("📸 Screenshot captured! (base64 image data available)")
            else:
                await context.send_activity(f"Screenshot result:\n```json\n{result}\n```")
        except (json.JSONDecodeError, TypeError):
            await context.send_activity(result)
        return

    # --- Inspect DOM ---
    if any(kw in text for kw in ["inspect", "dom", "what's on", "page content", "describe", "summarize"]):
        # Check if there's a URL in the message.
        words = text.split()
        url = None
        for w in words:
            if w.startswith("http"):
                url = w
                break

        params: dict = {}
        if url:
            params["url"] = url
        result = await _dispatch_tool(context, "inspectDom", params)
        # Truncate if very long.
        if len(result) > 3000:
            result = result[:3000] + "\n... (truncated)"
        await context.send_activity(f"**Page DOM:**\n```json\n{result}\n```")
        return

    # --- Select element ---
    if any(kw in text for kw in ["select element", "find element", "selector"]):
        # Try to extract a CSS selector (in quotes or after "selector").
        selector = text
        for prefix in ["select element ", "find element ", "selector "]:
            if prefix in text:
                selector = text.split(prefix, 1)[1].strip().strip("\"'")
                break
        result = await _dispatch_tool(context, "selectElement", {
            "selector": selector,
        })
        await context.send_activity(f"**Element:**\n```json\n{result}\n```")
        return

    # --- Click element ---
    if any(kw in text for kw in ["click "]):
        # Try to extract elementId or treat as selector search + click.
        element_id = text.replace("click ", "").strip().strip("\"'")
        if len(element_id) == 12 and element_id.isalnum():
            # Looks like an elementId.
            result = await _dispatch_tool(context, "clickElement", {
                "elementId": element_id,
            })
        else:
            # Treat as a selector — select first, then click.
            sel_result = await _dispatch_tool(context, "selectElement", {
                "selector": element_id,
            })
            try:
                sel_data = json.loads(sel_result)
                eid = sel_data.get("elementId")
                if eid:
                    result = await _dispatch_tool(context, "clickElement", {
                        "elementId": eid,
                    })
                else:
                    result = sel_result
            except (json.JSONDecodeError, TypeError):
                result = sel_result
        await context.send_activity(f"**Click result:**\n```json\n{result}\n```")
        return

    # --- Fallback ---
    await context.send_activity(
        f"I'm not sure what you mean. {HELP_TEXT}"
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    try:
        start_server(AGENT_APP, None)
    except Exception as error:
        raise error
