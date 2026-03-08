"""Tool execution handlers – map each MCP tool to Playwright actions."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from playwright.async_api import Error as PlaywrightError, Page

from .browser import BrowserManager, Session

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve_page(sess: Session, page_id: Optional[str]) -> Page:
    """Resolve an existing page by ID, raising a clear error if not found."""
    if page_id is None:
        raise RuntimeError("PAGE_ID_REQUIRED: a 'pageId' parameter is required for this operation")
    page = sess.get_page(page_id)
    if page is None:
        raise RuntimeError(
            f"PAGE_NOT_FOUND: tab '{page_id}' does not exist or was closed. "
            f"Open tabs: {list(sess.list_pages().keys())}"
        )
    return page


# ---------------------------------------------------------------------------
# Tool handlers
# ---------------------------------------------------------------------------

async def handle_session_status(
    bm: BrowserManager, params: Dict[str, Any]
) -> Dict[str, Any]:
    session_id = params.get("sessionId", "default")
    sess = await bm.get_or_create_session(session_id)
    return {
        "runnerConnected": True,
        "authenticated": sess.authenticated,
        "sessionId": session_id,
        "expiresAt": sess.expires_at.isoformat() if sess.expires_at else None,
        "openPages": sess.list_pages(),
    }


async def handle_bootstrap_login(
    bm: BrowserManager, params: Dict[str, Any]
) -> Dict[str, Any]:
    session_id = params.get("sessionId", "default")
    page_id = await bm.bootstrap_login(session_id)
    return {"status": "BOOTSTRAP_COMPLETE", "pageId": page_id}


async def handle_navigate(
    bm: BrowserManager, params: Dict[str, Any]
) -> Dict[str, Any]:
    """Navigate to a URL.
    - If ``pageId`` is omitted → open a new tab.
    - If ``pageId`` is given → reuse that tab (open a new one if it's gone).
    """
    session_id = params.get("sessionId", "default")
    url = params["url"]
    page_id: Optional[str] = params.get("pageId")

    sess = await bm.get_or_create_session(session_id)
    if not sess.authenticated:
        raise RuntimeError("SESSION_NOT_AUTHENTICATED")

    if page_id is not None:
        page = sess.get_page(page_id)
        if page is None:
            # Requested tab is gone – open a new one transparently.
            logger.warning("Tab '%s' not found – opening new tab", page_id)
            page_id, page = await bm.open_new_page(sess)
    else:
        # No pageId → always open a new tab.
        page_id, page = await bm.open_new_page(sess)

    sess.clear_elements(page_id)
    logger.info("Navigating tab %s to %s", page_id, url)
    await page.goto(url, wait_until="domcontentloaded")
    return {"status": "ok", "pageId": page_id, "finalUrl": page.url}


async def handle_inspect_dom(
    bm: BrowserManager, params: Dict[str, Any]
) -> Dict[str, Any]:
    session_id = params.get("sessionId", "default")
    page_id: Optional[str] = params.get("pageId")
    url = params.get("url")

    sess = await bm.get_or_create_session(session_id)
    if not sess.authenticated:
        raise RuntimeError("SESSION_NOT_AUTHENTICATED")

    page = _resolve_page(sess, page_id)
    if url:
        sess.clear_elements(page_id)
        await page.goto(url, wait_until="domcontentloaded")

    dom = await bm.inspect_dom(page, bm.config.dom_max_text_length)
    return {
        "pageId": page_id,
        "url": page.url,
        "title": await page.title(),
        "document": dom,
    }


async def handle_select_element(
    bm: BrowserManager, params: Dict[str, Any]
) -> Dict[str, Any]:
    session_id = params.get("sessionId", "default")
    page_id: Optional[str] = params.get("pageId")
    selector = params["selector"]

    sess = await bm.get_or_create_session(session_id)
    if not sess.authenticated:
        raise RuntimeError("SESSION_NOT_AUTHENTICATED")

    page = _resolve_page(sess, page_id)
    locator = page.locator(selector).first
    await locator.wait_for(state="attached", timeout=5000)
    eid = sess.store_element(page_id, locator)  # type: ignore[arg-type]
    return {"elementId": eid, "pageId": page_id, "selector": selector}


async def handle_click_element(
    bm: BrowserManager, params: Dict[str, Any]
) -> Dict[str, Any]:
    session_id = params.get("sessionId", "default")
    element_id = params["elementId"]

    sess = await bm.get_or_create_session(session_id)
    if not sess.authenticated:
        raise RuntimeError("SESSION_NOT_AUTHENTICATED")

    el = sess.get_element(element_id)
    if el is None:
        raise RuntimeError(f"ELEMENT_NOT_FOUND: element '{element_id}' not found or expired")
    page_id, locator = el

    page = sess.get_page(page_id)
    if page is None:
        raise RuntimeError(
            f"PAGE_NOT_FOUND: tab '{page_id}' (owning element '{element_id}') was closed"
        )

    await locator.click()
    await page.wait_for_load_state("domcontentloaded")
    return {"status": "ok", "pageId": page_id, "finalUrl": page.url}


async def handle_screenshot(
    bm: BrowserManager, params: Dict[str, Any]
) -> Dict[str, Any]:
    session_id = params.get("sessionId", "default")
    page_id: Optional[str] = params.get("pageId")

    sess = await bm.get_or_create_session(session_id)
    if not sess.authenticated:
        raise RuntimeError("SESSION_NOT_AUTHENTICATED")

    page = _resolve_page(sess, page_id)
    b64 = await bm.take_screenshot(page)
    return {"pageId": page_id, "contentType": "image/png", "base64": b64}


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------
TOOL_HANDLERS = {
    "sessionStatus": handle_session_status,
    "bootstrapLogin": handle_bootstrap_login,
    "navigate": handle_navigate,
    "inspectDom": handle_inspect_dom,
    "selectElement": handle_select_element,
    "clickElement": handle_click_element,
    "screenshot": handle_screenshot,
}


# Error messages that indicate the browser process has crashed or been closed.
_BROWSER_DEAD_MARKERS = (
    "Browser has been closed",
    "browser has been closed",
    "Target page, context or browser has been closed",
    "Target closed",
    "Connection closed",
    "Process closed",
)


def _is_browser_dead(exc: BaseException) -> bool:
    """Return True if the exception signals that the browser context is gone."""
    msg = str(exc)
    return any(m in msg for m in _BROWSER_DEAD_MARKERS)


async def dispatch_tool(
    bm: BrowserManager, tool: str, params: Dict[str, Any]
) -> Dict[str, Any]:
    handler = TOOL_HANDLERS.get(tool)
    if handler is None:
        raise RuntimeError(f"Unknown tool: {tool}")
    try:
        return await handler(bm, params)
    except (PlaywrightError, OSError, RuntimeError) as exc:
        if _is_browser_dead(exc):
            logger.warning("Browser appears crashed/closed – restarting: %s", exc)
            try:
                await bm.restart_browser()
            except Exception as restart_exc:
                raise RuntimeError(
                    "BROWSER_CRASHED: The browser was closed and could not be "
                    f"restarted automatically: {restart_exc}"
                ) from exc
            raise RuntimeError(
                "BROWSER_RESTARTED: The browser was closed or crashed and has "
                "been restarted. All previous pages and element handles are "
                "gone. Please call bootstrapLogin or navigate to start fresh."
            ) from exc
        raise
