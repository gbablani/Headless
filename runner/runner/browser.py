"""Playwright browser and session management.

Uses a **persistent browser context** backed by a stable Edge profile directory
so that cookies, MDM enrollment, and SSO state survive across Runner restarts.
The browser always runs in **headed** mode using the system-installed Edge.
"""

from __future__ import annotations

import asyncio
import base64
import datetime as _dt
import logging
import os
import random
import uuid
from typing import Any, Dict, Optional

from playwright.async_api import (
    BrowserContext,
    Page,
    Playwright,
    async_playwright,
)

from .models import RunnerConfig

logger = logging.getLogger(__name__)

# Default location of the persistent Edge profile used by the Runner.
_DEFAULT_PROFILE_DIR = os.path.join(
    os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
    "HeadlessRunner",
    "EdgeProfile",
)


class Session:
    """Tracks multiple browser tabs (pages) for a site, plus element handles."""

    def __init__(
        self,
        authenticated: bool = False,
        expires_at: Optional[_dt.datetime] = None,
    ):
        self.authenticated = authenticated
        self.expires_at = expires_at
        # Open pages keyed by pageId.
        self._pages: Dict[str, Page] = {}
        # Ephemeral element handle map (elementId → (pageId, locator)).
        self._elements: Dict[str, tuple[str, Any]] = {}

    # -- page management --------------------------------------------------

    def add_page(self, page: Page) -> str:
        """Register a page and return its pageId."""
        page_id = uuid.uuid4().hex[:8]
        self._pages[page_id] = page
        return page_id

    def remove_page(self, page_id: str) -> None:
        """Remove a page and clean up its associated elements."""
        self._pages.pop(page_id, None)
        self._elements = {
            eid: val for eid, val in self._elements.items() if val[0] != page_id
        }

    def get_page(self, page_id: str) -> Page | None:
        """Return the page if it exists and is still open, else None."""
        p = self._pages.get(page_id)
        if p is not None and p.is_closed():
            del self._pages[page_id]
            return None
        return p

    def list_pages(self) -> Dict[str, str]:
        """Return {pageId: url} for all live pages."""
        alive: Dict[str, str] = {}
        dead: list[str] = []
        for pid, p in self._pages.items():
            if p.is_closed():
                dead.append(pid)
            else:
                alive[pid] = p.url
        for pid in dead:
            del self._pages[pid]
        return alive

    def has_live_pages(self) -> bool:
        return any(not p.is_closed() for p in self._pages.values())

    # -- element management -----------------------------------------------

    def store_element(self, page_id: str, locator: Any) -> str:
        eid = uuid.uuid4().hex[:12]
        self._elements[eid] = (page_id, locator)
        return eid

    def get_element(self, eid: str) -> tuple[str, Any] | None:
        """Return (pageId, locator) or None."""
        return self._elements.get(eid)

    def clear_elements(self, page_id: str | None = None) -> None:
        if page_id is None:
            self._elements.clear()
        else:
            self._elements = {
                eid: val for eid, val in self._elements.items() if val[0] != page_id
            }


class BrowserManager:
    """Manages a persistent Edge browser context and sessions (tabs)."""

    def __init__(self, config: RunnerConfig):
        self.config = config
        self._pw: Optional[Playwright] = None
        self._context: Optional[BrowserContext] = None
        self._sessions: Dict[str, Session] = {}  # key = sessionId
        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        self._pw = await async_playwright().start()
        await self._launch_context()

    async def _launch_context(self) -> None:
        """(Re)launch the persistent browser context."""
        profile_dir = os.environ.get("RUNNER_PROFILE_DIR", _DEFAULT_PROFILE_DIR)
        os.makedirs(profile_dir, exist_ok=True)
        assert self._pw is not None

        launch_kwargs: Dict[str, Any] = {
            "channel": "msedge",
            "headless": False,
            "args": ["--no-first-run", "--disable-popup-blocking"],
            "locale": self.config.browser_locale,
            "viewport": {
                "width": self.config.viewport_width,
                "height": self.config.viewport_height,
            },
        }
        if self.config.browser_timezone_id:
            launch_kwargs["timezone_id"] = self.config.browser_timezone_id
        if self.config.browser_user_agent:
            launch_kwargs["user_agent"] = self.config.browser_user_agent

        self._context = await self._pw.chromium.launch_persistent_context(
            profile_dir,
            **launch_kwargs,
        )
        logger.info("Browser started (headed, Edge, profile=%s)", profile_dir)

    # ------------------------------------------------------------------
    # Human-like pacing helpers
    # ------------------------------------------------------------------

    async def human_pause(self, min_ms: Optional[int] = None, max_ms: Optional[int] = None) -> None:
        """Sleep for a small random interval to avoid robotic timing patterns."""
        lo = self.config.human_delay_min_ms if min_ms is None else min_ms
        hi = self.config.human_delay_max_ms if max_ms is None else max_ms
        lo = max(0, lo)
        hi = max(lo, hi)
        await asyncio.sleep(random.uniform(lo, hi) / 1000.0)

    def human_typing_delay_ms(self) -> int:
        """Return a per-keystroke delay in ms for human-like typing."""
        lo = max(0, self.config.typing_delay_min_ms)
        hi = max(lo, self.config.typing_delay_max_ms)
        return random.randint(lo, hi)

    async def human_after_navigation(self, page: Page) -> None:
        """Apply tiny post-navigation interactions that resemble normal browsing."""
        await self.human_pause(200, 700)
        if not self.config.human_scroll_after_navigation:
            return
        try:
            await page.evaluate(
                """() => {
                    const amount = Math.floor(80 + Math.random() * 220);
                    window.scrollBy({ top: amount, behavior: 'smooth' });
                }"""
            )
            await self.human_pause(120, 320)
            await page.evaluate("window.scrollBy({ top: -80, behavior: 'smooth' })")
        except Exception:
            # Non-fatal: some pages disallow scrolling while loading.
            logger.debug("Skipping post-navigation scroll simulation", exc_info=True)

    async def restart_browser(self) -> None:
        """Close the crashed/dead context and launch a fresh one.

        All sessions are cleared because pages belong to the old context.
        """
        logger.warning("Restarting browser context…")
        self._sessions.clear()
        if self._context:
            try:
                await self._context.close()
            except Exception:
                pass
            self._context = None
        await self._launch_context()

    async def stop(self) -> None:
        for sess in self._sessions.values():
            for p in list(sess._pages.values()):
                try:
                    if not p.is_closed():
                        await p.close()
                except Exception:
                    pass
        self._sessions.clear()
        if self._context:
            await self._context.close()
        if self._pw:
            await self._pw.stop()
        logger.info("Browser stopped")

    # ------------------------------------------------------------------
    # Session helpers
    # ------------------------------------------------------------------

    async def get_or_create_session(
        self, session_id: str = "default"
    ) -> Session:
        async with self._lock:
            existing = self._sessions.get(session_id)
            if existing is not None:
                return existing

            assert self._context is not None

            # Optimistically mark authenticated if cookies exist.
            authenticated = await self._has_cookies_for(self.config.intranetStartUrl)

            expires = _dt.datetime.utcnow() + _dt.timedelta(
                minutes=self.config.session_ttl_minutes
            )
            sess = Session(
                authenticated=authenticated,
                expires_at=expires,
            )
            self._sessions[session_id] = sess
            logger.info(
                "Session created '%s' (authenticated=%s)", session_id, authenticated
            )
            return sess

    async def open_new_page(self, session: Session) -> tuple[str, Page]:
        """Open a new tab in the persistent context and register it on the session."""
        assert self._context is not None
        page = await self._context.new_page()
        page_id = session.add_page(page)

        # Listen for user (or programmatic) close so we clean up immediately.
        def _on_page_close(_page: Page) -> None:
            logger.info("Tab %s was closed by the user or externally", page_id)
            session.remove_page(page_id)

        page.on("close", _on_page_close)
        logger.info("Opened new tab %s", page_id)
        return page_id, page

    async def close_session(self, session_id: str = "default") -> None:
        async with self._lock:
            sess = self._sessions.pop(session_id, None)
            if sess:
                for p in list(sess._pages.values()):
                    if not p.is_closed():
                        await p.close()

    async def _has_cookies_for(self, url: str) -> bool:
        """Check whether the persistent context already has cookies for a URL."""
        assert self._context is not None
        try:
            cookies = await self._context.cookies([url])
            return len(cookies) > 0
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Bootstrap login (in the same browser)
    # ------------------------------------------------------------------

    async def bootstrap_login(
        self, session_id: str = "default"
    ) -> str:
        """Navigate a new tab to the intranet login URL and wait for sign-in.
        Returns the pageId of the bootstrap tab.
        """
        sess = await self.get_or_create_session(session_id)

        page_id, page = await self.open_new_page(sess)

        logger.info("Bootstrap: navigating tab %s to %s", page_id, self.config.intranetStartUrl)
        await page.goto(self.config.intranetStartUrl, wait_until="domcontentloaded")

        # Wait for the post-login URL prefix.
        try:
            if self.config.postLoginUrlPrefix:
                for _ in range(300):  # 5 min at 1s intervals
                    await asyncio.sleep(1)
                    if page.url.startswith(self.config.postLoginUrlPrefix):
                        break
                else:
                    logger.warning("Bootstrap timed out waiting for URL prefix %s", self.config.postLoginUrlPrefix)
            else:
                # No prefix configured — wait 60 seconds.
                await asyncio.sleep(60)
        except Exception:
            logger.warning("Bootstrap wait interrupted", exc_info=True)

        sess.authenticated = True
        logger.info("Bootstrap login complete (tab %s)", page_id)
        return page_id

    # ------------------------------------------------------------------
    # DOM helpers
    # ------------------------------------------------------------------

    async def inspect_dom(self, page: Page, max_text: int) -> dict:
        """Return a JSON-serialisable DOM tree."""
        return await page.evaluate(
            """(maxText) => {
                function walk(node) {
                    if (node.nodeType === 3) {  // text
                        const t = node.textContent.trim();
                        return t ? t.substring(0, maxText) : null;
                    }
                    if (node.nodeType !== 1) return null;
                    const el = node;
                    const obj = {
                        tag: el.tagName.toLowerCase(),
                        attrs: {},
                        text: "",
                        children: []
                    };
                    for (const a of el.attributes) {
                        obj.attrs[a.name] = a.value.substring(0, maxText);
                    }
                    for (const child of el.childNodes) {
                        const c = walk(child);
                        if (c === null) continue;
                        if (typeof c === 'string') {
                            obj.text += (obj.text ? ' ' : '') + c;
                        } else {
                            obj.children.push(c);
                        }
                    }
                    obj.text = obj.text.substring(0, maxText);
                    return obj;
                }
                return walk(document.documentElement);
            }""",
            max_text,
        )

    async def take_screenshot(self, page: Page) -> str:
        """Return a base64-encoded PNG screenshot."""
        buf = await page.screenshot(type="png", full_page=False)
        return base64.b64encode(buf).decode("ascii")
