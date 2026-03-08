````markdown
# PRD: MCP Broker + Local Playwright Runner (Windows, VPN-only) for Intranet Web Inspection

## 1) Summary

Build a **Model Context Protocol (MCP) server** hosted in **Azure Container Apps** (the “Broker”) that can be called by a **Microsoft 365 Copilot declarative agent**. The Broker securely routes tool calls to a **per-user local Windows Runner** that hosts **Playwright** and can open a **headed browser** for interactive intranet login.  

The system supports multiple users. Each user runs the Runner on their Windows machine (VPN-only). After a one-time interactive login, the Runner keeps an authenticated Playwright session alive so **multiple MCP requests** can be executed against the **same session** without re-authentication.

> Key constraint: The cloud agent cannot directly reach `localhost` or launch a local browser. Users must have the Runner installed and running (or started on demand), with an outbound connection to the Broker.

---

## 2) Goals

- Allow an M365 declarative agent to invoke MCP tools that:
  - return a JSON description of a page DOM,
  - select an element,
  - click an element,
  - (optionally) navigate and/or screenshot for reliability/debug.
- Support intranet sites requiring interactive web login by using **local headed Playwright** for bootstrap authentication.
- Persist per-user sessions so repeated tool calls reuse the authenticated browser context.
- Enforce **Microsoft Entra ID (AAD)** authentication at the Broker boundary.
- Operate **VPN-only**, Windows-only, without centralized distribution tooling (users install Runner binary manually).

---

## 3) Non-Goals

- Bypassing intranet auth or automating credential injection.
- Token forwarding/replay into the browser session.
- Running Playwright in the cloud Broker.
- Supporting macOS/Linux runners.
- Offline or non-VPN access.
- Enterprise rollout (Intune/MECM) and fleet management (out of scope for MVP).

---

## 4) Personas & Assumptions

### Personas
- **End user:** A company user on Windows, connected to corporate VPN, using M365 Copilot agent.
- **Admin/Dev:** Publishes Broker and provides Runner installer + basic setup instructions.

### Assumptions
- Users can install and run a signed executable on Windows.
- Users can access intranet sites only when on VPN.
- M365 Copilot declarative agent can authenticate to the Broker using Entra SSO.
- Users will keep Runner running during agent interactions (or start it when instructed).

---

## 5) High-Level Architecture

### Components
1. **MCP Broker (Azure Container Apps)**
   - Hosts MCP server endpoint invoked by Copilot.
   - Enforces Entra authentication (ACA Authentication / “Easy Auth”).
   - Maintains a registry of active Runner connections keyed by user identity.
   - Forwards tool calls to the correct user’s Runner and returns results.

2. **Local Runner (Windows)**
   - Connects outbound to Broker using a persistent channel.
   - Authenticates to Broker using Entra (interactive once, then cached).
   - Hosts Playwright and maintains per-user sessions (contexts/pages).
   - Opens a headed browser for bootstrap login when needed.
   - Executes DOM inspection and interaction commands.

### Network
- **VPN-only** to reach intranet.  
- Runner → Broker uses outbound HTTPS (works through most corporate networks).

---

## 6) Authentication & Authorization

### 6.1 Broker Authentication (MUST)
- All Broker endpoints MUST require Entra authentication.
- Anonymous requests are rejected.
- Broker identifies user by `(tid, oid)` from validated identity headers/claims.

### 6.2 Runner Authentication to Broker (MUST)
- Runner MUST authenticate to Broker with Entra and bind its connection to the same `(tid, oid)` identity.
- Broker MUST refuse Runner connections that are unauthenticated or that cannot provide a stable user identity.

### 6.3 Routing Authorization (MUST)
- Broker MUST route tool calls only to the Runner connection whose `(tid, oid)` matches the caller.
- Caller must NOT be able to specify a different user/device target.

### 6.4 No Token Forwarding (MUST NOT)
- Broker MUST NOT forward Entra access tokens to Runner as browser credentials.
- Runner MUST NOT inject Entra tokens into browser sessions as an authentication mechanism.
- Browser authentication is performed only via interactive login during bootstrap.

---

## 7) Connection Model (Broker ↔ Runner)

### 7.1 Transport Options
MVP choice: **WebSocket over HTTPS** to Broker (simple, self-contained).  
Alternatives (future): Azure Web PubSub / SignalR / Azure Relay.

### 7.2 Runner Presence Registry
Broker maintains an in-memory (or small persistent) mapping:
- `userKey = tid:oid`
- `connectionId`
- `connectedAt`, `lastSeenAt`
- `runnerVersion`, optional `deviceName`

### 7.3 Heartbeats
- Runner sends heartbeat every N seconds.
- Broker drops connection after timeout.

### 7.4 Single vs Multiple Devices per User
MVP: **one active Runner per user**. If a second connects, Broker can:
- disconnect old connection, or
- keep newest and mark the other as standby.

---

## 8) Session Model (Runner)

### 8.1 Per-User Sessions
Runner maintains:
- 1 browser instance (shared per local process)
- 1 browser context per intranet “site” (or per `sessionId`)
- 1 active page per session (MVP), with optional support for multiple tabs later.

### 8.2 Session Identifiers
- Default session: `default`
- Optional: allow multiple `sessionId`s for different intranet apps.

### 8.3 Session Lifetime
- Sessions have TTL (e.g., 8 hours) and renew on activity.
- If intranet session expires, Runner enters `AUTH_REQUIRED` state.

### 8.4 Storage State
- Runner stores Playwright `storageState` **locally**.
- Storage state MUST be encrypted at rest (Windows DPAPI).
- Storage state MUST be scoped by:
  - user `(tid, oid)` (implicitly the Windows user running Runner), and
  - `siteKey` (intranet base URL or configured identifier).

---

## 9) Bootstrap Login (Local, Headed)

### 9.1 Trigger Conditions
Runner MUST initiate bootstrap login when:
- no stored `storageState` exists, OR
- stored `storageState` fails to authenticate (detected by post-login selector checks), OR
- user explicitly requests `bootstrapLogin` tool.

### 9.2 Bootstrap Mechanism
- Runner opens Playwright in **headed mode** (visible window).
- Navigates to a configured `INTRANET_START_URL`.
- User completes interactive sign-in.
- Runner detects completion by:
  - presence of a configured `POST_LOGIN_SELECTOR` OR
  - navigation to a configured post-login URL prefix.
- Runner saves `storageState` and returns `READY`.

### 9.3 User Experience
When the agent needs login:
- Broker returns an error indicating Runner will open a login window (if connected),
  or instructs the user to start Runner if not connected.

---

## 10) MCP Tool Surface (Broker-Exposed Tools)

> The following tools are exposed by the Broker via MCP and executed by the Runner.

### 10.1 `sessionStatus`
**Purpose:** Check if Runner is connected and if intranet session is authenticated.

**Input**
```json
{
  "siteKey": "string",
  "sessionId": "string (optional, default 'default')"
}
````

**Output**

```json
{
  "runnerConnected": true,
  "authenticated": true,
  "sessionId": "default",
  "expiresAt": "ISO-8601",
  "siteKey": "intranetA"
}
```

**Errors**

* `RUNNER_NOT_CONNECTED`
* `SESSION_NOT_AUTHENTICATED` (include `action: "BOOTSTRAP_REQUIRED"`)

---

### 10.2 `bootstrapLogin`

**Purpose:** Force interactive login locally (headed Playwright).

**Input**

```json
{
  "siteKey": "string",
  "sessionId": "string (optional)"
}
```

**Output**

```json
{
  "status": "BOOTSTRAP_STARTED"
}
```

**Notes**

* Runner may immediately open a browser window.
* Tool returns quickly; session becomes usable once Runner reports READY.
* Broker should encourage user to retry the original action after completion.

---

### 10.3 `navigate`

**Purpose:** Navigate the active page within an authenticated session.

**Input**

```json
{
  "siteKey": "string",
  "sessionId": "string (optional)",
  "url": "string"
}
```

**Output**

```json
{
  "status": "ok",
  "finalUrl": "string"
}
```

---

### 10.4 `inspectDom`

**Purpose:** Return a JSON representation of the DOM for the current page (or a URL).

**Input**

```json
{
  "siteKey": "string",
  "sessionId": "string (optional)",
  "url": "string (optional)"
}
```

**Output**

```json
{
  "url": "string",
  "title": "string",
  "document": {
    "tag": "html",
    "attrs": {},
    "text": "",
    "children": [
      {
        "tag": "body",
        "attrs": {},
        "text": "",
        "children": []
      }
    ]
  }
}
```

**DOM JSON Requirements**

* Include: `tag`, `attrs`, `children`
* Include `text` with normalization and truncation (configurable max length)
* Include a stable `nodeId` for nodes (see 10.5) OR include a path-based identifier.

---

### 10.5 `selectElement`

**Purpose:** Resolve a selector to a stable element handle reference.

**Input**

```json
{
  "siteKey": "string",
  "sessionId": "string (optional)",
  "selector": "string"
}
```

**Output**

```json
{
  "elementId": "string",
  "selector": "string"
}
```

**Element ID Rules**

* Element IDs are ephemeral and scoped to `(siteKey, sessionId, pageContext)`
* Expire on navigation or after TTL.

---

### 10.6 `clickElement`

**Purpose:** Click a previously resolved element.

**Input**

```json
{
  "siteKey": "string",
  "sessionId": "string (optional)",
  "elementId": "string"
}
```

**Output**

```json
{
  "status": "ok",
  "finalUrl": "string (optional)"
}
```

---

### 10.7 Optional: `screenshot`

**Purpose:** Diagnostic aid and grounding validation.

**Input**

```json
{
  "siteKey": "string",
  "sessionId": "string (optional)"
}
```

**Output**

```json
{
  "contentType": "image/png",
  "base64": "string"
}
```

---

## 11) Broker Error Contracts (Standardized)

Broker MUST return structured errors when it cannot fulfill a request.

### 11.1 Runner Not Connected

```json
{
  "error": "RUNNER_NOT_CONNECTED",
  "message": "Your local Runner is not connected. Start the Runner and try again."
}
```

### 11.2 Session Not Authenticated

```json
{
  "error": "SESSION_NOT_AUTHENTICATED",
  "message": "You need to sign in to the intranet. A browser window will open on your machine.",
  "action": "BOOTSTRAP_REQUIRED"
}
```

### 11.3 Action Timeout

```json
{
  "error": "ACTION_TIMEOUT",
  "message": "The action did not complete in time. Retry or check VPN connectivity."
}
```

---

## 12) Concurrency & Ordering

### 12.1 Serialization Per Session (MUST)

Runner MUST serialize commands per `(siteKey, sessionId)` to prevent races.

### 12.2 Timeouts

* Each action has a default timeout (e.g., 30s) configurable per tool.
* Navigation/click should wait for a defined readiness state:

  * `domcontentloaded` or `networkidle` (configurable).

---

## 13) Security Requirements

* Broker:

  * Entra authentication required.
  * Strict user-to-runner routing; no impersonation.
  * Rate limits per user.
* Runner:

  * Stores session state encrypted (DPAPI).
  * Does not expose an inbound HTTP server on localhost by default.
  * Accepts commands only over authenticated Broker channel.
* Both:

  * Do not log sensitive page content by default.
  * Audit log tool name + timestamps + success/failure + (tid, oid), but not secrets.

---

## 14) Observability

### Broker Logs (structured)

* `timestamp`, `userKey (tid:oid)`, `tool`, `status`, `durationMs`, `errorCode?`, `runnerConnectionId`

### Runner Logs (local)

* `timestamp`, `tool`, `status`, `durationMs`, `errorCode?`, `pageUrl?` (optional, configurable)

---

## 15) Configuration

### Broker (env)

* `ALLOWED_TENANT_IDS` (optional)
* `RUNNER_WS_PATH` (e.g., `/runner/ws`)
* `BROKER_REQUEST_TIMEOUT_MS`
* `MAX_INFLIGHT_PER_USER`

### Runner (config file / env)

* `BROKER_URL`
* `SITE_CONFIG` list:

  * `siteKey`
  * `intranetStartUrl`
  * `postLoginSelector` or `postLoginUrlPrefix`
* `SESSION_TTL_MINUTES`
* `DOM_MAX_TEXT_LENGTH`
* `HEARTBEAT_INTERVAL_SECONDS`

---

## 16) Packaging & Installation (Runner)

* Provide a signed Windows binary (EXE).
* Installation is manual (download + run).
* Runner should support:

  * `runner.exe start` (starts and connects)
  * `runner.exe bootstrap --site intranetA`
  * optional `--tray` mode

---

## 17) MVP Acceptance Criteria

1. A user installs and runs Runner on Windows while on VPN.
2. User invokes the M365 Copilot declarative agent tool.
3. Broker authenticates the user via Entra and detects connected Runner.
4. If not logged in, Runner opens a headed browser and user signs in once.
5. After login, user can invoke:

   * `navigate`
   * `inspectDom` (gets DOM JSON)
   * `selectElement`
   * `clickElement`
6. Multiple sequential calls operate on the same session without re-authentication until TTL/session expiry.
7. Sessions are isolated per user; one user cannot drive another user’s Runner.

---

## 18) Open Questions (for implementation choice)

* Transport: direct WebSocket vs Web PubSub/SignalR (MVP recommends direct WebSocket).
* DOM JSON format: full tree vs filtered summary (MVP: full tree with truncation limits).
* Element identity strategy: selector/path IDs vs Playwright handles mapping (MVP: ephemeral `elementId` mapped in Runner memory).
* Browser choice: bundled Chromium vs system Edge (MVP: Playwright Chromium; optional Edge channel support later).

---

```

```
