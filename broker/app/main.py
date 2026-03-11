"""FastAPI application – the ACA MCP Broker.

Run locally:
    uvicorn broker.app.main:app --reload --port 8000

Deploy to Azure Container Apps with the provided Dockerfile.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from broker/ directory (parent of app/).
_env_path = Path(__file__).resolve().parent.parent / ".env"
_loaded = load_dotenv(_env_path)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .mcp_tools import router as mcp_router
from .ws_handler import router as ws_router

logging.basicConfig(
    level=logging.DEBUG if os.getenv("BROKER_DEV_MODE") else logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s  %(message)s",
)

logger = logging.getLogger(__name__)
_dev = os.getenv("BROKER_DEV_MODE", "").lower() in ("1", "true", "yes")
if _dev:
    logger.warning("Broker running in DEV MODE – authentication is bypassed via x-dev-* headers")
else:
    logger.info("Broker running in PRODUCTION mode – Entra authentication required")

app = FastAPI(
    title="ACA MCP Broker",
    version="0.1.0",
    description="Model Context Protocol broker that routes tool calls to per-user local Playwright Runners.",
 servers=[
        {"url": "https://7da4-71-231-83-162.ngrok-free.app", "description": "Public tunnel"}
    ]
)

# CORS – allow the M365 Copilot origin (adjust for production).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers.
app.include_router(ws_router)
app.include_router(mcp_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
