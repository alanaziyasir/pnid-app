import { expect, test, Page } from '@playwright/test';
import { readFile } from 'node:fs/promises';
import path from 'node:path';

const api = 'http://127.0.0.1:8100';
const diagram = path.resolve('public/example.png');

async function detectionResponse(page: Page): Promise<Response> {
  // The detector serves bounded concurrency and replies 503 when its slots
  // are full; the app retries those transparently. The settled response,
  // not the first transient one, is what the UI and this suite rely on.
  const detectPost = () =>
    page.waitForResponse(
      (response) =>
        response.url() === `${api}/api/detect` && response.request().method() === 'POST',
    );
  let response = await detectPost();
  while (response.status() === 503) {
    response = await detectPost();
  }
  return response;
}

test('upload, preview, analysis tabs, and chat through the real API', async ({ page, request }) => {
  const errors: string[] = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.goto('/');
  await expect(page.getByRole('button', { name: 'Process diagram' })).toBeDisabled();
  const uploaded = page.waitForResponse(
    (response) => response.url() === `${api}/api/upload` && response.request().method() === 'POST',
  );
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
  const detected = detectionResponse(page);
  await page.getByRole('button', { name: 'Process diagram' }).click();
  const detection = await detected;
  expect(detection.status()).toBe(200);
  expect(detection.request().postDataJSON()).toEqual({ stored_name: file.stored_name });
  expect(detection.request().headers()['x-request-id']).toBeTruthy();
  const result = await detection.json();
  expect(result.detector).toBe('template_matching');
  expect(result.image_hw).toEqual([1500, 1500]);
  expect(result.ocr_available).toBe(false);
  const count = result.detections.length;
  expect(count).toBeGreaterThan(0);
  await expect(page).toHaveURL(/\/analysis\?/);
  await expect(page.getByRole('heading', { name: 'Summary', exact: true })).toBeVisible();
  await expect(page.locator('.diagram-overlay-image')).toHaveJSProperty('naturalWidth', 1500);
  await expect(page.locator('.component-box')).toHaveCount(count);
  await expect(page.locator('.component-item')).toHaveCount(count);
  await expect(page.locator('.detection-count')).toHaveText(`${count} components detected`);
  const first = result.detections[0];
  const overlay = page.locator('.component-box').first();
  expect(
    await overlay.evaluate((element) => parseFloat((element as HTMLElement).style.left)),
  ).toBeCloseTo((first.x1 / result.image_hw[1]) * 100, 3);
  await expect(
    page.getByText('OCR is unavailable. No text recognition was performed.'),
  ).toBeVisible();
  await page.getByRole('button', { name: 'Tags 0', exact: true }).click();
  await expect(page.locator('.ocr-box')).toHaveCount(0);
  await expect(page.locator('.component-box')).toHaveCount(0);
  await page.getByRole('button', { name: `Components ${count}`, exact: true }).click();
  await expect(page.locator('.component-box')).toHaveCount(count);
  await page.getByRole('button', { name: 'All', exact: true }).click();
  await expect(page.locator('.component-box')).toHaveCount(count);

  await page.getByPlaceholder('Type your message...').fill('Which components are connected?');
  const completion = page.waitForResponse(`${api}/api/chat/completions`);
  await page.getByRole('button', { name: 'Send message' }).click();
  expect((await completion).status()).toBe(200);
  await expect(page.locator('.chat-message.assistant')).toHaveText(
    '[Local QA stub, no AI inference] Received: Which components are connected?',
  );
  expect(errors).toEqual([]);
});

test('a blank non-square image returns an honest empty state', async ({ page }) => {
  await page.goto('/');
  const buffer = await blankImage(page);
  await page.getByLabel('Upload diagram').setInputFiles({
    name: 'blank.png',
    mimeType: 'image/png',
    buffer,
  });
  await expect(page.getByText('Uploaded', { exact: true })).toBeVisible();
  const detected = detectionResponse(page);
  await page.getByRole('button', { name: 'Process diagram' }).click();
  const response = await detected;
  expect(response.status()).toBe(200);
  const result = await response.json();
  expect(result.image_hw).toEqual([180, 320]);
  expect(result.detections).toEqual([]);
  await expect(page.getByRole('status')).toHaveText('No matching components found.');
  await expect(page.locator('.component-box')).toHaveCount(0);
  await expect(page.locator('.component-item')).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Tags 0', exact: true })).toBeVisible();
});

test('corrupt uploads show a detection error and retry without sample fallback', async ({
  page,
}) => {
  await page.goto('/');
  await page.getByLabel('Upload diagram').setInputFiles({
    name: 'corrupt.png',
    mimeType: 'image/png',
    buffer: Buffer.from('not a valid image'),
  });
  await expect(page.getByText('Uploaded', { exact: true })).toBeVisible();
  const detected = detectionResponse(page);
  await page.getByRole('button', { name: 'Process diagram' }).click();
  expect((await detected).status()).toBe(422);
  const error = page.locator('.summary-container').getByRole('alert');
  await expect(error).toContainText('Use a valid PNG or JPEG');
  await expect(page.locator('.component-box')).toHaveCount(0);
  await expect(page.locator('.component-item')).toHaveCount(0);
  const retried = detectionResponse(page);
  await page.getByRole('button', { name: 'Try again' }).click();
  expect((await retried).status()).toBe(422);
  await expect(error).toBeVisible();
});

test('changing upload cancels stale detection results while showing loading', async ({
  page,
  request,
}) => {
  await page.goto('/');
  const blank = await blankImage(page);
  const uploaded = await request.post(`${api}/api/upload`, {
    multipart: {
      file: { name: 'example.png', mimeType: 'image/png', buffer: await readFile(diagram) },
    },
  });
  const { file: first } = await uploaded.json();
  const secondUpload = await request.post(`${api}/api/upload`, {
    multipart: { file: { name: 'blank.png', mimeType: 'image/png', buffer: blank } },
  });
  const { file: second } = await secondUpload.json();
  let release = () => {};
  const hold = new Promise<void>((resolve) => {
    release = resolve;
  });
  let ready = () => {};
  const resultReady = new Promise<void>((resolve) => {
    ready = resolve;
  });
  await page.route(`${api}/api/detect`, async (route) => {
    if (route.request().postDataJSON().stored_name !== first.stored_name) {
      await route.continue();
      return;
    }
    const response = await route.fetch();
    expect(response.status()).toBe(200);
    expect((await response.json()).detections.length).toBeGreaterThan(0);
    ready();
    await hold;
    // Navigating to the second upload may already have aborted this request.
    await route.fulfill({ response }).catch(() => {});
  });
  await page.goto(
    `/analysis?file=${encodeURIComponent(first.url)}&stored_name=${first.stored_name}`,
  );
  await expect(page.getByRole('status')).toHaveText('Detecting components...');
  await resultReady;
  const detected = detectionResponse(page);
  await page.evaluate((file) => {
    window.history.pushState(
      {},
      '',
      `/analysis?file=${encodeURIComponent(file.url)}&stored_name=${file.stored_name}`,
    );
  }, second);
  expect((await detected).status()).toBe(200);
  await expect(page.getByRole('status')).toHaveText('No matching components found.');
  release();
  await page.unrouteAll({ behavior: 'wait' });
  await expect(page.locator('.component-item')).toHaveCount(0);
  await expect(page.locator('.diagram-overlay-image')).toHaveJSProperty('naturalWidth', 320);
  await expect(page.locator('.detection-count')).toHaveText('0 components detected');
});

async function blankImage(page: Page) {
  const data = await page.evaluate(() => {
    const canvas = document.createElement('canvas');
    canvas.width = 320;
    canvas.height = 180;
    const context = canvas.getContext('2d')!;
    context.fillStyle = 'white';
    context.fillRect(0, 0, canvas.width, canvas.height);
    return canvas.toDataURL('image/png').split(',')[1];
  });
  return Buffer.from(data, 'base64');
}

test('remove a preview and reject unsupported uploads', async ({ page, request }) => {
  await page.goto('/');
  await page.getByLabel('Upload diagram').setInputFiles(diagram);
  await expect(page.getByText('Uploaded', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Remove diagram' }).click();
  await expect(page.getByText('Upload Your Diagram', { exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Process diagram' })).toBeDisabled();

  const rejected = await request.post(`${api}/api/upload`, {
    multipart: {
      file: { name: 'invalid.txt', mimeType: 'text/plain', buffer: Buffer.from('invalid') },
    },
  });
  expect(rejected.status()).toBe(400);
  expect((await rejected.json()).detail).toContain('not allowed');
});
