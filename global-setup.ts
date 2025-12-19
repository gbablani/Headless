
import { chromium, FullConfig } from '@playwright/test';
import 'dotenv/config';

export default async function globalSetup(_config: FullConfig) {
  const browser = await chromium.launch({ headless: false });
  const page = await browser.newPage();

  await page.goto(process.env.APP_ENTRY_URL!);

  await page.locator('#i0116').fill(process.env.APP_USER!);
  await page.locator('#idSIButton9').click();
  await page.locator('#i0118').fill(process.env.APP_PASSWORD!);
  await page.locator('#idSIButton9').click();

  if (process.env.MFA_MODE === 'TOTP') {
    try {
      await page.waitForSelector('input[name="otc"]', { timeout: 15000 });
      const code = await getTotp();
      await page.locator('input[name="otc"]').fill(code);
      await page.locator('button[type="submit"]').click();
    } catch {}
  } else {
    console.log('Approve MFA (PUSH) on device.');
  }

  try {
    await page.waitForSelector('#idBtn_Back', { timeout: 3000 });
    await page.click('#idBtn_Back');
  } catch {}

  await page.waitForLoadState('networkidle');
  await page.context().storageState({ path: 'auth.json' });
  await browser.close();
}

async function getTotp(): Promise<string> {
  const { TOTP } = await import('otpauth');
  const secret = process.env.TOTP_SECRET!;
  const totp = new TOTP({ secret, digits: 6 });
  return totp.generate();
}
