# start_server.py
"""Web server setup following the M365 Agents SDK pattern.

Hosts:
  - POST /api/messages  → M365 Agents SDK conversation endpoint
  - GET  /api/messages   → health probe
  - WS   /runner/ws      → Runner WebSocket endpoint
  - GET  /health         → simple health check
"""

from os import environ

from microsoft_agents.hosting.core import AgentApplication, AgentAuthConfiguration
from microsoft_agents.hosting.aiohttp import (
    start_agent_process,
    jwt_authorization_middleware,
    CloudAdapter,
)
from aiohttp.web import Request, Response, Application, run_app

from app.ws_aiohttp import runner_ws_handler


def start_server(
    agent_application: AgentApplication,
    auth_configuration: AgentAuthConfiguration,
):
    async def entry_point(req: Request) -> Response:
        agent: AgentApplication = req.app["agent_app"]
        adapter: CloudAdapter = req.app["adapter"]
        return await start_agent_process(req, agent, adapter)

    async def health(req: Request) -> Response:
        return Response(text='{"status":"ok"}', content_type="application/json")

    APP = Application(middlewares=[jwt_authorization_middleware])

    # --- M365 Agents SDK conversation endpoint ---
    APP.router.add_post("/api/messages", entry_point)
    APP.router.add_get("/api/messages", lambda _: Response(status=200))

    # --- Runner WebSocket endpoint ---
    APP.router.add_get("/runner/ws", runner_ws_handler)

    # --- Health ---
    APP.router.add_get("/health", health)

    # --- App state ---
    APP["agent_configuration"] = auth_configuration
    APP["agent_app"] = agent_application
    APP["adapter"] = agent_application.adapter

    port = int(environ.get("PORT", 8000))
    try:
        run_app(APP, host="localhost", port=port)
    except Exception as error:
        raise error
