
import { chromium } from 'playwright';
import type { FullConfig } from '@playwright/test';
import 'dotenv/config';
import { promptForCredentials } from './src/utils/auth-prompt.js';

export default async function globalSetup(_config: FullConfig) {
  console.log('\n🔐 Starting Entra ID authentication setup...\n');

  // Get credentials from environment or prompt user
  let username = process.env.APP_USER;
  let password = process.env.APP_PASSWORD;
  let mfaMode = process.env.MFA_MODE as 'TOTP' | 'PUSH' | undefined;
  let totpSecret = process.env.TOTP_SECRET;
  let entryUrl = process.env.APP_ENTRY_URL;

  // If credentials not in environment, prompt user
  if (!username || !password) {
    console.log('⚠️  Credentials not found in environment variables.');
    const creds = await promptForCredentials();
    username = creds.username;
    password = creds.password;
    mfaMode = creds.mfaMode;
    totpSecret = creds.totpSecret;
  }

  // Default entry URL if not set
  if (!entryUrl) {
    entryUrl = 'https://portal.microsofticm.com/imp/';
    console.log(`ℹ️  Using default entry URL: ${entryUrl}`);
  }

  console.log(`✓ Authenticating as: ${username}`);
  console.log('✓ Launching browser (headed mode for authentication)...\n');

  const browser = await chromium.launch({ headless: false });
  const page = await browser.newPage();

  await page.goto(entryUrl);

  // Wait for and fill username
  await page.waitForSelector('#i0116', { timeout: 10000 });
  await page.locator('#i0116').fill(username);
  await page.locator('#idSIButton9').click();

  // Wait for and fill password
  await page.waitForSelector('#i0118', { timeout: 10000 });
  await page.locator('#i0118').fill(password);
  await page.locator('#idSIButton9').click();

  // Handle MFA
  if (mfaMode === 'TOTP' && totpSecret) {
    try {
      await page.waitForSelector('input[name="otc"]', { timeout: 15000 });
      const code = await getTotp(totpSecret);
      console.log('✓ Generated TOTP code');
      await page.locator('input[name="otc"]').fill(code);
      await page.locator('button[type="submit"]').click();
    } catch (err) {
      console.log('⚠️  TOTP entry not found or failed, continuing...');
    }
  } else {
    console.log('⏳ Waiting for MFA approval... Please approve on your device.');
    // Wait longer for manual approval
    await page.waitForTimeout(30000);
  }

  // Handle "Stay signed in?" prompt
  try {
    await page.waitForSelector('#idBtn_Back', { timeout: 5000 });
    await page.click('#idBtn_Back');
    console.log('✓ Handled "Stay signed in" prompt');
  } catch {
    // Prompt may not appear, continue
  }

  // Wait for authentication to complete
  console.log('⏳ Waiting for authentication to complete...');
  await page.waitForLoadState('networkidle', { timeout: 60000 });

  // Save authentication state
  await page.context().storageState({ path: 'auth.json' });
  console.log('✅ Authentication successful! Session saved to auth.json\n');

  await browser.close();
}

async function getTotp(secret: string): Promise<string> {
  const { TOTP } = await import('otpauth');
  const totp = new TOTP({ secret, digits: 6 });
  return totp.generate();
}
