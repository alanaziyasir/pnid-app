import { afterEach, expect, it, vi } from 'vitest';
import { apiFetch } from './api';
import { loadDetections } from './detection';

vi.mock('./api', () => ({ apiFetch: vi.fn() }));
afterEach(() => vi.resetAllMocks());

it('posts the stored upload identity and forwards cancellation without adding sample data', async () => {
  const result = {
    detector: 'template_matching',
    image_hw: [80, 120],
    detections: [],
    ocr_available: false,
    limit_reached: false,
  };
  vi.mocked(apiFetch).mockResolvedValue(Response.json(result));
  const signal = new AbortController().signal;
  expect(await loadDetections('stored.png', signal)).toEqual(result);
  expect(apiFetch).toHaveBeenCalledWith('/api/detect', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ stored_name: 'stored.png' }),
    signal,
  });
});

it.each([
  [404, 'not found'],
  [415, 'PNG and JPEG'],
  [422, '4 million pixels'],
  [503, 'unavailable'],
])(
  'maps HTTP %s to a safe error instead of displaying response content',
  async (status, message) => {
    vi.mocked(apiFetch).mockResolvedValue(new Response('private backend detail', { status }));
    await expect(loadDetections('stored.png', new AbortController().signal)).rejects.toThrow(
      String(message),
    );
  },
);

it('propagates network failures without returning stale sample results', async () => {
  vi.mocked(apiFetch).mockRejectedValue(new Error('API request failed'));
  await expect(loadDetections('stored.png', new AbortController().signal)).rejects.toThrow(
    'API request failed',
  );
});
