
# Intranet Scraper (Playwright + Entra ID)

Headless browser scraper that authenticates via Microsoft Entra ID, persists signed-in state, and scrapes intranet pages. Designed for SharePoint/LOB sites published with Entra pre-auth (Application Proxy) or cloud-hosted M365.

## Quick start
1. Install deps:
   ```bash
   pnpm install
   npx playwright install --with-deps
   ```
2. Create `.env` from `.env.example` and fill secrets.
3. Bootstrap auth (headed once):
   ```bash
   pnpm run auth:bootstrap
   ```
4. Run a scrape (headless):
   ```bash
   pnpm run scrape:icm -- https://portal.microsofticm.com/imp/v3/outages/dashboard/azure/declaredoutages
   ```
