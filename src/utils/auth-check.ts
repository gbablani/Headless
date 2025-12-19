
import { chromium } from 'playwright';
import { existsSync } from 'fs';

/**
 * Check if auth.json exists and is valid
 */
export async function ensureAuthenticated(): Promise<void> {
  if (!existsSync('auth.json')) {
    console.error('❌ Authentication state not found!');
    console.error('\nPlease run the authentication setup first:');
    console.error('  npm run auth:bootstrap\n');
    process.exit(1);
  }

  // Quick validation: try to create a context with the stored state
  try {
    console.log('🔍 Validating authentication state...');
    const browser = await chromium.launch({ headless: true });
    const context = await browser.newContext({ storageState: 'auth.json' });
    await context.close();
    await browser.close();
    console.log('✅ Authentication state is valid\n');
  } catch (err) {
    console.error('❌ Authentication state appears to be invalid or corrupted!');
    console.error('\nPlease re-run authentication setup:');
    console.error('  npm run auth:bootstrap\n');
    console.error('Error details:', err instanceof Error ? err.message : String(err));
    process.exit(1);
  }
}

/**
 * Wrapper to initialize browser with authentication
 */
export async function createAuthenticatedBrowser() {
  await ensureAuthenticated();
  
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ storageState: 'auth.json' });
  
  return { browser, context };
}
