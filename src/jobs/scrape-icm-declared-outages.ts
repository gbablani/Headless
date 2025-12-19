
import { writeJson } from '../utils/storage';
import { toCsv } from '../utils/csv';
import { createAuthenticatedBrowser } from '../utils/auth-check';

// Usage: pnpm run scrape:icm -- https://portal.microsofticm.com/imp/v3/outages/dashboard/azure/declaredoutages
const targetUrl = process.argv[2] || 'https://portal.microsofticm.com/imp/v3/outages/dashboard/azure/declaredoutages';

// Heuristics for finding JSON responses powering the grid
const HINTS = ['declaredoutages', 'outages', 'dashboard', 'imp/v3'];

(async () => {
  console.log('🚀 Starting ICM Declared Outages scraper...\n');
  
  const { browser, context } = await createAuthenticatedBrowser();
  const page = await context.newPage();

  const captured: Array<{ url: string; data: any }> = [];

  page.on('response', async (resp) => {
    try {
      const url = resp.url();
      const ct = resp.headers()['content-type'] || '';
      if (HINTS.some(h => url.includes(h)) && ct.includes('application/json')) {
        const buf = await resp.body();
        const text = Buffer.from(buf).toString('utf-8');
        const data = JSON.parse(text);
        captured.push({ url, data });
      }
    } catch { /* ignore parse errors */ }
  });

  await page.goto(targetUrl, { waitUntil: 'networkidle' });

  // Give the grid time to load and any lazy requests to fire
  await page.waitForTimeout(3000);

  // Fallback DOM extraction: try common grid/table patterns
  const domRows = await page.$$eval('table tr', rows => rows.map(r => Array.from(r.querySelectorAll('td,th')).map(c => c.textContent?.trim() ?? '')));

  // Normalize JSON if captured
  let normalized: any[] = [];
  if (captured.length > 0) {
    // Attempt to find an array of outages from captured payloads
    for (const entry of captured) {
      const root = entry.data;
      if (Array.isArray(root)) normalized = root;
      else if (Array.isArray(root?.items)) normalized = root.items;
      else if (Array.isArray(root?.data)) normalized = root.data;
      if (normalized.length) break;
    }
  }

  // If still empty, convert DOM rows into simple objects
  if (normalized.length === 0 && domRows.length > 1) {
    const header = domRows[0];
    normalized = domRows.slice(1).map(r => Object.fromEntries(r.map((v, i) => [header[i] || `col_${i+1}`, v])));
  }

  // Persist outputs
  await writeJson('icm/declared_outages.json', { url: targetUrl, capturedUrls: captured.map(c => c.url), records: normalized });

  // Also write CSV locally or to blob (if configured)
  const csvText = toCsv(normalized);
  await writeJson('icm/declared_outages.csv', csvText);

  console.log(`✅ Scraped ${normalized.length} records from ICM Declared Outages.`);
  console.log('✅ Scraping complete!\n');
  await browser.close();
})();
