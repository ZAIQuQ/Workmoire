// Drive one submission per PDF through the isolated candidate app.
const fs = require('node:fs');
const { chromium } = require('playwright');

async function evaluate(page, origin, sample, timeout) {
  const started = performance.now();
  let outcome = 'prepare_failed';
  try {
    await page.goto(origin);
    await page.locator('#list-new').click();
    await page.locator('[data-template="paper"]').click();
    const dialog = page.locator('.paper-import-dialog');
    await dialog.locator('#paper-reference').fill(sample.reference);
    await dialog.locator('#paper-pdf-input').setInputFiles(sample.pdf);
    await dialog.locator('#paper-prepare').click();
    const generate = dialog.locator('#paper-generate');
    await generate.click({ trial: true, timeout: 60000 });
    outcome = 'analysis_failed';
    const terminal = page.waitForResponse(async response => {
      if (response.url().endsWith('/api/papers/draft') && response.status() >= 400) return true;
      if (!response.url().includes('/api/papers/jobs/')) return false;
      const job = await response.json().catch(() => ({}));
      return ['completed', 'failed'].includes(job.status);
    }, { timeout: (timeout + 15) * 1000 });
    const [response] = await Promise.all([terminal, generate.click()]);
    const job = await response.json();
    if (job.status !== 'completed') return { status: outcome, error: job.error_code || 'request_failed' };
    await dialog.locator('.paper-analysis-result').waitFor({ state: 'visible', timeout: 5000 });
    return { status: 'preview', report: job.result.content, trace: job.trace_id, seconds: (performance.now() - started) / 1000 };
  } catch {
    return { status: outcome };
  }
}

async function main() {
  const { origin, password, timeout, cases } = JSON.parse(fs.readFileSync(0, 'utf8'));
  const browser = await chromium.launch();
  try {
    const context = await browser.newContext();
    context.setDefaultTimeout(10000);
    const setup = await context.request.post(origin + '/api/setup', {
      data: { username: 'acceptance', password }
    });
    if (!setup.ok()) throw Error('Could not create isolated benchmark account');
    const page = await context.newPage();
    const results = [];
    for (const sample of cases) {
      results.push({ id: sample.id, ...await evaluate(page, origin, sample, timeout) });
      process.stderr.write(`Paper ${results.length}/${cases.length}: ${results.at(-1).status}\n`);
    }
    process.stdout.write(JSON.stringify(results));
  } finally {
    await browser.close();
  }
}

main().catch(() => {
  process.stderr.write('Benchmark browser could not complete\n');
  process.exitCode = 1;
});
