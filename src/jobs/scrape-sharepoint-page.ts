
import { chromium } from 'playwright';
import { extractTable, extractLinks } from '../utils/dom';
import { writeJson } from '../utils/storage';

const url = process.argv[2];
(async () => {
  const browser = await chromium.launch();
  const context = await browser.newContext({ storageState: 'auth.json' });
  const page = await context.newPage();
  await page.goto(url, { waitUntil: 'domcontentloaded' });
  const tableData = await extractTable(page, 'div[data-automation-id="listViewContainer"] table');
  const links = await extractLinks(page, 'a');
  await writeJson('sharepoint/exports/page.json', { url, tableData, links });
  await browser.close();
})();
