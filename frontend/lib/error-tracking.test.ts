import { afterEach, expect, it, vi } from 'vitest';
import { initErrorTracking } from './error-tracking';

vi.mock('@sentry/nextjs', () => ({ init: vi.fn() }));
afterEach(() => vi.resetAllMocks());

it('stays fully disabled without a DSN', async () => {
  const { init } = await import('@sentry/nextjs');
  expect(initErrorTracking(undefined)).toBe(false);
  expect(init).not.toHaveBeenCalled();
});

it('initializes with a DSN but never collects user-identifying data', async () => {
  const { init } = await import('@sentry/nextjs');
  expect(initErrorTracking('https://public@sentry.invalid/1')).toBe(true);
  const options = vi.mocked(init).mock.calls[0]?.[0] as Record<string, unknown>;
  const dataCollection = options.dataCollection as object;
  expect(options.dsn).toBe('https://public@sentry.invalid/1');
  expect(dataCollection).toEqual({
    userInfo: false,
    cookies: false,
    httpHeaders: false,
    httpBodies: [],
    urlQueryParams: false,
  });
  expect(options.tracesSampleRate).toBe(0);
});
