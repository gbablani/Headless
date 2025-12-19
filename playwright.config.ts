
import { defineConfig } from '@playwright/test';
export default defineConfig({
  retries: 2,
  use: {
    headless: true,
    storageState: 'auth.json',
    screenshot: 'only-on-failure',
    trace: 'on-first-retry',
    viewport: { width: 1366, height: 900 },
  },
});
