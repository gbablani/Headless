
import { Page } from 'playwright';

export async function extractTable(page: Page, selector: string) {
  await page.waitForSelector(selector, { timeout: 10000 });
  return page.$$eval(`${selector} tr`, rows =>
    rows.map(r => Array.from(r.querySelectorAll('td,th')).map(c => c.textContent?.trim() ?? ''))
  );
}

export async function extractLinks(page: Page, selector: string) {
  return page.$$eval(selector, as =>
    as
      .map(a => ({ href: (a as HTMLAnchorElement).href, text: a.textContent?.trim() ?? '' }))
      .filter(x => !!x.href)
  );
}
