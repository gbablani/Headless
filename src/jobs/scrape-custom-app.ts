
import { chromium } from 'playwright';
import { writeJson } from '../utils/storage';

const url = process.argv[2];
(async () => {
  const browser = await chromium.launch();
  const context = await browser.newContext({ storageState: 'auth.json' });
  const page = await context.newPage();
  await page.goto(url, { waitUntil: 'networkidle' });
  const headings = await page.$$eval('h1, h2, h3', els => els.map(e => e.textContent?.trim() ?? ''));
  const navLinks = await page.$$eval('nav a', els => els.map(e => ({ href: (e as HTMLAnchorElement).href, text: e.textContent?.trim() ?? '' })));
  await writeJson('custom/exports/page.json', { url, headings, navLinks });
  await browser.close();
})();
