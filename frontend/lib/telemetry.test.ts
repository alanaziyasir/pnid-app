import { afterEach, expect, it, vi } from 'vitest';
import { apiFetch } from './api';
import { trackEvent } from './telemetry';

vi.mock('./api', () => ({ apiFetch: vi.fn() }));
afterEach(() => vi.resetAllMocks());

it('posts allowlisted event names with coarse status only', () => {
  vi.mocked(apiFetch).mockResolvedValue(new Response('{}', { status: 202 }));
  trackEvent('upload_failed', 415);
  expect(apiFetch).toHaveBeenCalledWith('/api/events', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ events: [{ type: 'upload_failed', status: 415 }] }),
    silent: true,
  });
});

it('omits the status field when none is provided', () => {
  vi.mocked(apiFetch).mockResolvedValue(new Response('{}', { status: 202 }));
  trackEvent('detection_completed');
  const options = vi.mocked(apiFetch).mock.calls[0]?.[1];
  expect(JSON.parse(String(options?.body))).toEqual({
    events: [{ type: 'detection_completed' }],
  });
});

it('swallows report failures instead of surfacing them in the UI', async () => {
  vi.mocked(apiFetch).mockRejectedValue(new Error('API request failed'));
  const consoleError = vi.spyOn(console, 'error').mockImplementation(() => undefined);
  trackEvent('chat_failed');
  await new Promise((resolve) => setTimeout(resolve, 0));
  expect(consoleError).not.toHaveBeenCalled();
  consoleError.mockRestore();
});
