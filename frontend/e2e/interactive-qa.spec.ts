import { expect, test } from '@playwright/test';
import { readFile } from 'node:fs/promises';
import path from 'node:path';

const api = 'http://127.0.0.1:8100';
const diagram = path.resolve('public/example.png');

test('upload, preview, analysis tabs, and chat through the real API', async ({ page, request }) => {
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto('/');
  await expect(page.getByRole('button', { name: 'Process diagram' })).toBeDisabled();
  const uploaded = page.waitForResponse(response =>
    response.url() === `${api}/api/upload` && response.request().method() === 'POST');
  await page.getByLabel('Upload diagram').setInputFiles(diagram);
  const response = await uploaded;
  expect(response.status()).toBe(200);
  const { file } = await response.json();
  await expect(page.getByText('Uploaded', { exact: true })).toBeVisible();
  const preview = page.getByRole('img', { name: 'example.png', exact: true });
  await expect(preview).toHaveJSProperty('naturalWidth', 1500);
  expect(await (await request.get(`${api}${file.url}`)).body()).toEqual(await readFile(diagram));

  await page.getByRole('button', { name: 'Expand diagram' }).click();
  await expect(page.locator('.fullscreen-image')).toBeVisible();
  await page.getByRole('button', { name: 'Close fullscreen' }).click();
  await page.getByRole('button', { name: 'Process diagram' }).click();
  await expect(page).toHaveURL(/\/analysis\?/);
  await expect(page.getByRole('heading', { name: 'Summary', exact: true })).toBeVisible();
  await expect(page.locator('.diagram-overlay-image')).toHaveJSProperty('naturalWidth', 1500);
  await expect(page.locator('.component-box')).toHaveCount(10);
  await page.getByRole('button', { name: 'Tags 10', exact: true }).click();
  await expect(page.locator('.ocr-box')).toHaveCount(10);
  await expect(page.locator('.component-box')).toHaveCount(0);
  await page.getByRole('button', { name: 'All', exact: true }).click();
  await expect(page.locator('.component-box')).toHaveCount(10);

  await page.getByPlaceholder('Type your message...').fill('Which components are connected?');
  const completion = page.waitForResponse(`${api}/api/chat/completions`);
  await page.getByRole('button', { name: 'Send message' }).click();
  expect((await completion).status()).toBe(200);
  await expect(page.locator('.chat-message.assistant')).toHaveText(
    '[Local QA stub, no AI inference] Received: Which components are connected?');
  expect(errors).toEqual([]);
});

test('remove a preview and reject unsupported uploads', async ({ page, request }) => {
  await page.goto('/');
  await page.getByLabel('Upload diagram').setInputFiles(diagram);
  await expect(page.getByText('Uploaded', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Remove diagram' }).click();
  await expect(page.getByText('Upload Your Diagram', { exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Process diagram' })).toBeDisabled();

  const rejected = await request.post(`${api}/api/upload`, {
    multipart: { file: { name: 'invalid.txt', mimeType: 'text/plain', buffer: Buffer.from('invalid') } },
  });
  expect(rejected.status()).toBe(400);
  expect((await rejected.json()).detail).toContain('not allowed');
});
