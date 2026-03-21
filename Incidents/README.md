# Incidents Foundry Agent Project

This folder is now structured as a Microsoft Foundry hosted agent project.
It no longer uses Microsoft 365 Agents Toolkit provisioning files.

## What Changed

- Removed M365 toolkit pipeline definitions (`m365agents.yml`, `m365agents.local.yml`).
- Added Foundry agent configuration (`agent.yaml`).
- Added Foundry workspace metadata (`.foundry/agent-metadata.yaml`).
- Added Foundry environment variables in `env/.env.dev` and `env/.env.local`.

## Project Layout

| Path | Purpose |
| ---- | ------- |
| `.foundry/agent-metadata.yaml` | Environment and deployment metadata used by Foundry workflows |
| `agent.yaml` | Hosted agent manifest for Foundry |
| `instructions/system.txt` | Agent system instructions |
| `openapi.yaml` | Tool contract against the broker MCP HTTP endpoints |
| `env/.env.dev` | Committable dev defaults |
| `env/.env.local` | Local development values |

## Local Setup

1. Fill Foundry settings in `env/.env.local`.
2. Set `BROKER_BASE_URL` to your broker endpoint (for example ngrok or Container App URL).
3. Update `openapi.yaml` server URL to match your broker endpoint.
4. Use this project as your hosted agent source when deploying to Foundry.

## Runtime Expectations

- The agent relies on the broker MCP HTTP routes exposed by this repository's `broker` service.
- A user-local Runner must be connected for browser automation tools to succeed.
- Authentication and user routing remain enforced by the broker (`tid:oid` identity key).

## Notes

- Existing M365 packaging assets under `appPackage/` are retained only as legacy reference.
- New development should use Foundry metadata and deployment workflows.