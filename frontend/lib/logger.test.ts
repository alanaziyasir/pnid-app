import { afterEach, expect, it, vi } from 'vitest';
import { logError } from './logger';

afterEach(() => vi.restoreAllMocks());

it('logs only allowlisted metadata even when runtime callers supply private fields', () => {
  const write = vi.spyOn(console, 'error').mockImplementation(() => {});
  const context = { status: 503, requestId: 'req-1', password: 'private', filename: 'private.png' };
  logError('chat_failed', context);
  expect(JSON.parse(write.mock.calls[0][0])).toEqual({
    level: 'error',
    event: 'chat_failed',
    status: 503,
    requestId: 'req-1',
  });
});

it('allows logging a safe event without context', () => {
  const write = vi.spyOn(console, 'error').mockImplementation(() => {});
  logError('upload_failed');
  expect(JSON.parse(write.mock.calls[0][0])).toEqual({ level: 'error', event: 'upload_failed' });
});
