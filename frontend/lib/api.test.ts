import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { apiFetch, API_URL } from './api';

beforeEach(() => {
  vi.spyOn(console, 'error').mockImplementation(() => {});
});
afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

it('propagates a request ID and preserves caller headers', async () => {
  const fetch = vi.fn().mockResolvedValue(new Response('{}'));
  vi.stubGlobal('fetch', fetch);
  await apiFetch('/health', { headers: { Accept: 'application/json' } });
  expect(fetch.mock.calls[0][0]).toBe(`${API_URL}/health`);
  const options = fetch.mock.calls[0][1] as RequestInit;
  expect(new Headers(options.headers).get('X-Request-ID')).toMatch(/^[a-f0-9-]{36}$/);
  expect(new Headers(options.headers).get('Accept')).toBe('application/json');
});

it('generates an opaque request ID on non-secure HTTP origins without randomUUID', async () => {
  const fetch = vi.fn().mockResolvedValue(new Response('{}'));
  vi.stubGlobal('fetch', fetch);
  vi.stubGlobal('crypto', {
    getRandomValues: (bytes: Uint8Array) => bytes.fill(15),
  });
  await apiFetch('/health');
  expect(new Headers(fetch.mock.calls[0][1].headers).get('X-Request-ID')).toBe('0f'.repeat(16));
});

it('retries transient GET failures with exponential backoff and one request ID', async () => {
  const fetch = vi
    .fn()
    .mockResolvedValueOnce(new Response('', { status: 503 }))
    .mockResolvedValue(new Response('ok'));
  vi.stubGlobal('fetch', fetch);
  const result = await apiFetch('/health');
  expect(result.status).toBe(200);
  expect(fetch).toHaveBeenCalledTimes(2);
  expect(new Headers(fetch.mock.calls[0][1].headers).get('X-Request-ID')).toBe(
    new Headers(fetch.mock.calls[1][1].headers).get('X-Request-ID'),
  );
});

it('retries network errors only for GET', async () => {
  const fetch = vi
    .fn()
    .mockRejectedValueOnce(new TypeError('private'))
    .mockResolvedValue(new Response('ok'));
  vi.stubGlobal('fetch', fetch);
  expect((await apiFetch('/health')).status).toBe(200);
  expect(fetch).toHaveBeenCalledTimes(2);
});

it.each(['POST', 'PUT'])('does not replay mutating %s requests', async (method) => {
  const fetch = vi.fn().mockRejectedValue(new TypeError('private'));
  vi.stubGlobal('fetch', fetch);
  await expect(apiFetch('/api/upload', { method })).rejects.toThrow('API request failed');
  expect(fetch).toHaveBeenCalledTimes(1);
});

it('returns terminal HTTP errors without retrying', async () => {
  const fetch = vi.fn().mockResolvedValue(new Response('', { status: 400 }));
  vi.stubGlobal('fetch', fetch);
  expect((await apiFetch('/api/upload', { method: 'POST' })).status).toBe(400);
  expect(fetch).toHaveBeenCalledTimes(1);
});

it('stops after three GET attempts', async () => {
  const fetch = vi.fn().mockResolvedValue(new Response('', { status: 503 }));
  vi.stubGlobal('fetch', fetch);
  expect((await apiFetch('/health')).status).toBe(503);
  expect(fetch).toHaveBeenCalledTimes(3);
});

it('honors caller cancellation without retry', async () => {
  const controller = new AbortController();
  controller.abort();
  const fetch = vi.fn().mockRejectedValue(new DOMException('Cancelled', 'AbortError'));
  vi.stubGlobal('fetch', fetch);
  await expect(apiFetch('/health', { signal: controller.signal })).rejects.toThrow(
    'API request failed',
  );
  expect(fetch).toHaveBeenCalledTimes(1);
});
