"""CLI entry point for the local Runner.

Usage:
    runner start                   # connect to broker
    runner start --dev             # dev mode (no real Entra auth)
    runner bootstrap --site foo    # force interactive login for a site
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
from pathlib import Path

from .auth import get_access_token
from .browser import BrowserManager
from .client import RunnerClient
from .models import RunnerConfig

logger = logging.getLogger(__name__)

_DEFAULT_CONFIG_PATH = Path(
    os.getenv("LOCALAPPDATA", os.path.expanduser("~")),
    "HeadlessRunner",
    "config.json",
)

# Also check next to the runner package (for dev convenience).
_LOCAL_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.json"


def _load_config(path: Path | None = None) -> RunnerConfig:
    p = path or (_DEFAULT_CONFIG_PATH if _DEFAULT_CONFIG_PATH.exists() else _LOCAL_CONFIG_PATH)
    logger.info("Loading config from: %s (exists=%s)", p, p.exists())
    if p.exists():
        raw = json.loads(p.read_text(encoding="utf-8"))
        return RunnerConfig(
            broker_url=raw.get("broker_url", os.getenv("BROKER_URL", "ws://localhost:8000/runner/ws")),
            intranetStartUrl=raw.get("intranetStartUrl", "https://login.microsoftonline.com"),
            postLoginUrlPrefix=raw.get("postLoginUrlPrefix"),
            session_ttl_minutes=raw.get("session_ttl_minutes", 480),
            dom_max_text_length=raw.get("dom_max_text_length", 200),
            heartbeat_interval_seconds=raw.get("heartbeat_interval_seconds", 15),
            client_id=raw.get("client_id", os.getenv("RUNNER_CLIENT_ID", "")),
            tenant_id=raw.get("tenant_id", os.getenv("RUNNER_TENANT_ID", "")),
            broker_scope=raw.get("broker_scope", os.getenv("RUNNER_BROKER_SCOPE", "")),
        )
    return RunnerConfig()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="runner", description="Headless MCP Runner")
    sub = parser.add_subparsers(dest="command")

    start_p = sub.add_parser("start", help="Connect to the broker and listen for tool calls")
    start_p.add_argument("--config", type=Path, default=None, help="Path to config.json")
    start_p.add_argument("--dev", action="store_true", help="Dev mode (skip Entra auth)")
    start_p.add_argument("--dev-tid", default="dev-tenant", help="Fake tenant ID for dev")
    start_p.add_argument("--dev-oid", default="dev-user", help="Fake object ID for dev")

    bs_p = sub.add_parser("bootstrap", help="Force interactive login")
    bs_p.add_argument("--config", type=Path, default=None)

    return parser.parse_args()


async def _run_start(args: argparse.Namespace) -> None:
    config = _load_config(args.config)

    # Authenticate.
    if args.dev:
        token = f"dev:{args.dev_tid}:{args.dev_oid}"
        logger.info("Dev mode – using fake identity %s:%s", args.dev_tid, args.dev_oid)
    else:
        if not config.client_id or not config.tenant_id or not config.broker_scope:
            print(
                "ERROR: Entra app settings (client_id, tenant_id, broker_scope) "
                "must be set in config or environment variables.",
                file=sys.stderr,
            )
            sys.exit(1)
        scopes = [config.broker_scope]
        token = get_access_token(config.client_id, config.tenant_id, scopes)

    # Start browser manager.
    bm = BrowserManager(config)
    await bm.start()

    # Connect to broker.
    client = RunnerClient(config, bm, token)
    try:
        await client.connect()
    except KeyboardInterrupt:
        pass
    finally:
        await client.disconnect()
        await bm.stop()


async def _run_bootstrap(args: argparse.Namespace) -> None:
    config = _load_config(args.config)
    bm = BrowserManager(config)
    await bm.start()
    try:
        await bm.bootstrap_login()
        print("Bootstrap login completed.")
    finally:
        await bm.stop()


def main() -> None:
    logging.basicConfig(
        level=logging.DEBUG if os.getenv("RUNNER_DEBUG") else logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s  %(message)s",
    )
    args = _parse_args()
    if args.command == "start":
        asyncio.run(_run_start(args))
    elif args.command == "bootstrap":
        asyncio.run(_run_bootstrap(args))
    else:
        print("Usage: runner {start|bootstrap} [options]")
        sys.exit(1)


if __name__ == "__main__":
    main()
