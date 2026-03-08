# ACA MCP Broker

The **ACA MCP Broker** acts as a relay between M365 Copilot / Teams and
per-user local Playwright Runners connected via WebSocket.

It supports **two modes**:

| Mode | Framework | Entry Point | Default Port | Use Case |
|------|-----------|-------------|--------------|----------|
| **Agents SDK** | aiohttp (M365 Agents SDK) | `python app.py` | 8000 | Teams / M365 Copilot conversational agent |
| **Standalone** | FastAPI | `uvicorn app.main:app` | 8000 | REST API for direct tool calls, ChatGPT, curl |

Both modes share the same Runner WebSocket infrastructure and registry.

## Quick Start — Agents SDK Mode (M365 Copilot)

```bash
cd broker
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate  # macOS / Linux

pip install -r requirements.txt

# Dev mode
BROKER_DEV_MODE=true python app.py
# → Listening on http://localhost:8000
```

Then configure your Teams / M365 Copilot app to point at
`https://<your-tunnel>/api/messages`.

## Quick Start — Standalone FastAPI Mode

```bash
cd broker
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate  # macOS / Linux

pip install -r requirements.txt

# Dev mode – skip real Entra auth
BROKER_DEV_MODE=true uvicorn app.main:app --reload --port 8000
```

## API Endpoints

### Agents SDK mode (`python app.py`)

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/messages` | M365 Agents SDK conversation endpoint |
| `GET`  | `/api/messages` | Health probe |
| `WS`   | `/runner/ws` | Runner WebSocket endpoint |
| `GET`  | `/health` | Health check |

### Standalone mode (`uvicorn app.main:app`)

| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/health` | Health check |
| `WS`   | `/runner/ws` | Runner WebSocket endpoint |
| `POST` | `/mcp/tools/sessionStatus` | Check session status |
| `POST` | `/mcp/tools/bootstrapLogin` | Trigger interactive login |
| `POST` | `/mcp/tools/navigate` | Navigate to a URL |
| `POST` | `/mcp/tools/inspectDom` | Get DOM tree as JSON |
| `POST` | `/mcp/tools/selectElement` | Resolve a CSS selector |
| `POST` | `/mcp/tools/clickElement` | Click a resolved element |
| `POST` | `/mcp/tools/screenshot` | Take a page screenshot |
| `GET`  | `/mcp/tools/list` | MCP tool manifest |

## Deploy to Azure Container Apps

```bash
# Build & push image
az acr build --registry <ACR> --image broker:latest .

# Create Container App (Agents SDK mode — default)
az containerapp create \
  --name mcp-broker \
  --resource-group <RG> \
  --image <ACR>.azurecr.io/broker:latest \
  --target-port 8000 \
  --ingress external \
  --env-vars ALLOWED_TENANT_IDS=<tid>

# Or, for standalone FastAPI mode:
az containerapp create \
  --name mcp-broker \
  --resource-group <RG> \
  --image <ACR>.azurecr.io/broker:latest \
  --target-port 8000 \
  --ingress external \
  --env-vars ALLOWED_TENANT_IDS=<tid> \
  --command "uvicorn" --args "app.main:app" "--host" "0.0.0.0" "--port" "8000"
```

Then enable **Authentication** (Entra ID provider) in the Azure portal
for the Container App.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `BROKER_DEV_MODE` | `false` | Enable dev mode (fake auth headers) |
| `ALLOWED_TENANT_IDS` | *(empty)* | Comma-separated allowed tenant IDs |
| `BROKER_REQUEST_TIMEOUT_MS` | `30000` | Timeout for Runner responses |
| `MAX_INFLIGHT_PER_USER` | `10` | Max concurrent requests per user |
| `PORT` | `8000` | Port for Agents SDK mode |
