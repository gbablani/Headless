
# Intranet Scraper (Playwright + Entra ID)

Headless browser scraper that authenticates via Microsoft Entra ID, persists signed-in state, and scrapes intranet pages. Designed for SharePoint/LOB sites published with Entra pre-auth (Application Proxy) or cloud-hosted M365.

## Features

- **Interactive authentication**: Prompts for Entra ID credentials on first run
- **Session persistence**: Saves authentication state for headless scraping
- **MFA support**: Handles both TOTP (authenticator app) and PUSH (approve on device) methods
- **Automatic validation**: Checks authentication state before running scrapes

## Quick start

1. Install dependencies:
   ```bash
   pnpm install
   npx playwright install --with-deps
   ```

2. **(Optional)** Create `.env` from `.env.example` and fill secrets:
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```
   
   If you skip this step, the tool will prompt you interactively for credentials.

3. Bootstrap authentication (runs in headed browser mode):
   ```bash
   pnpm run auth:bootstrap
   ```
   
   This will:
   - Prompt for your Entra ID credentials (if not in `.env`)
   - Open a browser window to complete authentication
   - Handle MFA (TOTP or PUSH)
   - Save the authenticated session to `auth.json`

4. Run scraping jobs (runs in headless mode):
   ```bash
   # Scrape ICM declared outages
   pnpm run scrape:icm -- https://portal.microsofticm.com/imp/v3/outages/dashboard/azure/declaredoutages
   
   # Scrape SharePoint page
   pnpm run scrape:sharepoint -- https://your-sharepoint-site.com
   
   # Scrape custom app
   pnpm run scrape:custom -- https://your-custom-app.com
   ```

## Authentication Flow

1. **Initial Setup** (headed mode): 
   - User runs `auth:bootstrap`
   - Credentials are prompted (or read from `.env`)
   - Browser opens in visible mode
   - User completes Entra ID authentication including MFA
   - Session saved to `auth.json`

2. **Scraping** (headless mode):
   - Script validates `auth.json` exists
   - Headless browser uses saved session
   - No user interaction required

3. **Session Refresh**: If session expires, re-run `auth:bootstrap`

## Environment Variables

See `.env.example` for all available options:

- `APP_ENTRY_URL`: Entry point URL for authentication (default: ICM portal)
- `APP_USER`: Your Entra ID username/email
- `APP_PASSWORD`: Your password
- `MFA_MODE`: Either `TOTP` or `PUSH`
- `TOTP_SECRET`: Base32 secret for TOTP (if using authenticator app)
- `AZURE_STORAGE_CONNECTION_STRING`: Optional, for uploading results to Azure Blob
- `AZURE_BLOB_CONTAINER`: Blob container name for results
