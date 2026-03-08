# Local Playwright Runner

The **Runner** is a Windows application that connects outbound to the ACA MCP
Broker and executes Playwright-based browser automation commands on behalf of
the authenticated user.

## Quick Start (Dev Mode)

```bash
cd runner
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate  # macOS / Linux

pip install -r requirements.txt

# Start in dev mode (no Entra auth, connects to local broker)
python -m runner.main start --dev
```

> **Note:** The Runner uses the system-installed Microsoft Edge (`channel="msedge"`).
> No separate browser download (e.g. `playwright install chromium`) is required.

## Configuration

Copy `config.sample.json` to `%LOCALAPPDATA%\HeadlessRunner\config.json`
and customise:

```json
{
    "broker_url": "wss://mcp-broker.<FQDN>/runner/ws",
    "intranetStartUrl": "https://intranet.example.com",
    "postLoginUrlPrefix": "https://intranet.example.com/home",
    "client_id": "<ENTRA_CLIENT_ID>",
    "tenant_id": "<ENTRA_TENANT_ID>",
    "broker_scope": "api://<BROKER_APP_ID>/.default"
}
```

## Commands

| Command | Description |
|---------|-------------|
| `runner start` | Connect to broker and listen for tool calls |
| `runner start --dev` | Dev mode with fake identity |
| `runner bootstrap` | Force interactive login |

## Building the Windows Executable

```bash
pip install pyinstaller
python build.py
```

The executable is created at `dist/runner.exe`.

> **Note:** Playwright browser binaries are NOT bundled in the EXE. The Runner
> uses the system-installed Microsoft Edge, so no separate browser download is
> required. Ensure Edge is installed on the target machine.

## How It Works

1. Runner authenticates to the Broker via Entra (device-code flow, one-time).
2. Connects over WebSocket to the Broker.
3. Broker dispatches MCP tool calls (from Copilot) to the Runner.
4. Runner executes Playwright actions and returns results.
5. For first-time site login, a **headed** browser window opens for interactive auth.
6. Storage state is saved encrypted (Windows DPAPI) for subsequent headless use.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `BROKER_URL` | `ws://localhost:3978/runner/ws` | Broker WebSocket URL |
| `RUNNER_CLIENT_ID` | *(empty)* | Entra app client ID |
| `RUNNER_TENANT_ID` | *(empty)* | Entra tenant ID |
| `RUNNER_BROKER_SCOPE` | *(empty)* | Broker API scope |
| `RUNNER_DEBUG` | `false` | Enable debug logging |
| `SESSION_TTL_MINUTES` | `480` | Session time-to-live |
| `DOM_MAX_TEXT_LENGTH` | `200` | Max text length in DOM nodes |
| `HEARTBEAT_INTERVAL_SECONDS` | `15` | Heartbeat interval |
