
import { writeJson } from '../utils/storage';
import { createAuthenticatedBrowser } from '../utils/auth-check';

const url = process.argv[2];

if (!url) {
  console.error('❌ Error: URL argument is required');
  console.error('Usage: npm run scrape:custom -- <url>');
  process.exit(1);
}

(async () => {
  console.log('🚀 Starting custom app scraper...\n');
  
  const { browser, context } = await createAuthenticatedBrowser();
  const page = await context.newPage();
  await page.goto(url, { waitUntil: 'networkidle' });
  
  console.log('📊 Extracting data from page...');
  const headings = await page.$$eval('h1, h2, h3', els => els.map(e => e.textContent?.trim() ?? ''));
  const navLinks = await page.$$eval('nav a', els => els.map(e => ({ href: (e as HTMLAnchorElement).href, text: e.textContent?.trim() ?? '' })));
  
  await writeJson('custom/exports/page.json', { url, headings, navLinks });
  
  console.log(`✅ Extracted ${headings.length} headings and ${navLinks.length} navigation links`);
  console.log('✅ Scraping complete!\n');
  await browser.close();
})();
