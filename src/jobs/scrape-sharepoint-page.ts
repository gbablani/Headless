
import { extractTable, extractLinks } from '../utils/dom';
import { writeJson } from '../utils/storage';
import { createAuthenticatedBrowser } from '../utils/auth-check';

const url = process.argv[2];

if (!url) {
  console.error('❌ Error: URL argument is required');
  console.error('Usage: npm run scrape:sharepoint -- <url>');
  process.exit(1);
}

(async () => {
  console.log('🚀 Starting SharePoint page scraper...\n');
  
  const { browser, context } = await createAuthenticatedBrowser();
  const page = await context.newPage();
  await page.goto(url, { waitUntil: 'domcontentloaded' });
  
  console.log('📊 Extracting data from page...');
  const tableData = await extractTable(page, 'div[data-automation-id="listViewContainer"] table');
  const links = await extractLinks(page, 'a');
  
  await writeJson('sharepoint/exports/page.json', { url, tableData, links });
  
  console.log(`✅ Extracted ${tableData.length} table rows and ${links.length} links`);
  console.log('✅ Scraping complete!\n');
  await browser.close();
})();
