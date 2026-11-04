import { expect, test } from '@playwright/test';
import { readFile } from 'node:fs/promises';

const api = 'http://127.0.0.1:8100';

test('running public surfaces expose safe headers and no source files', async ({ request }) => {
  const frontend = await request.get('/health');
  expect(frontend.status()).toBe(200);
  expect(frontend.headers()['x-content-type-options']).toBe('nosniff');
  expect(frontend.headers()['x-frame-options']).toBe('DENY');
  const backend = await request.get(`${api}/health`, {
    headers: { 'X-Request-ID': 'security-qa' },
  });
  expect(backend.status()).toBe(200);
  expect(backend.headers()['x-request-id']).toBe('security-qa');
  expect(backend.headers()['x-content-type-options']).toBe('nosniff');
  for (const path of ['/.env', '/config.py', '/uploads/%2e%2e%2fconfig.py']) {
    expect((await request.get(`${api}${path}`)).status()).toBe(404);
  }
  const cors = await request.fetch(`${api}/api/upload`, {
    method: 'OPTIONS',
    headers: { Origin: 'https://untrusted.example', 'Access-Control-Request-Method': 'POST' },
  });
  expect(cors.status()).toBe(400);
  expect(cors.headers()['access-control-allow-origin']).toBeUndefined();
});

test('user filenames render as text instead of executing markup', async ({ page }) => {
  const filename = '<img src=x onerror=alert(1)>.png';
  const dialogs: string[] = [];
  page.on('dialog', async (dialog) => {
    dialogs.push(dialog.message());
    await dialog.dismiss();
  });
  await page.goto('/');
  await page.getByLabel('Upload diagram').setInputFiles({
    name: filename,
    mimeType: 'image/png',
    buffer: await readFile('public/example.png'),
  });
  await expect(page.getByText('Uploaded', { exact: true })).toBeVisible();
  await expect(page.locator('.file-name')).toHaveText(filename);
  expect(dialogs).toEqual([]);
  await expect(page.locator('img[onerror]')).toHaveCount(0);
});
