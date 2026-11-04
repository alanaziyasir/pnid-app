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
])(
  'maps HTTP %s to a safe error instead of displaying response content',
  async (status, message) => {
    vi.mocked(apiFetch).mockResolvedValue(new Response('private backend detail', { status }));
    await expect(loadDetections('stored.png', new AbortController().signal)).rejects.toThrow(
      String(message),
    );
  },
);

it('retries a busy detector with backoff before surfacing a safe error', async () => {
  vi.useFakeTimers();
  try {
    vi.mocked(apiFetch).mockResolvedValue(new Response('Detector busy', { status: 503 }));
    const pending = loadDetections('stored.png', new AbortController().signal);
    const assertion = expect(pending).rejects.toThrow('unavailable');
    await vi.advanceTimersByTimeAsync(2_000);
    await assertion;
    expect(apiFetch).toHaveBeenCalledTimes(4);
  } finally {
    vi.useRealTimers();
  }
});

it('recovers when the detector frees a slot between retries', async () => {
  vi.useFakeTimers();
  try {
    const result = {
      detector: 'template_matching',
      image_hw: [80, 120],
      detections: [],
      ocr_available: false,
      limit_reached: false,
    };
    vi.mocked(apiFetch)
      .mockResolvedValueOnce(new Response('Detector busy', { status: 503 }))
      .mockResolvedValueOnce(Response.json(result));
    const pending = loadDetections('stored.png', new AbortController().signal);
    const assertion = pending.then((value) => expect(value).toEqual(result));
    await vi.advanceTimersByTimeAsync(500);
    await assertion;
    expect(apiFetch).toHaveBeenCalledTimes(2);
  } finally {
    vi.useRealTimers();
  }
});

it('stops retrying when the caller aborts during backoff', async () => {
  vi.useFakeTimers();
  try {
    vi.mocked(apiFetch).mockResolvedValue(new Response('Detector busy', { status: 503 }));
    const controller = new AbortController();
    const pending = loadDetections('stored.png', controller.signal);
    const assertion = expect(pending).rejects.toThrow();
    controller.abort();
    await vi.advanceTimersByTimeAsync(2_000);
    await assertion;
    expect(apiFetch).toHaveBeenCalledTimes(1);
  } finally {
    vi.useRealTimers();
  }
});

it('propagates network failures without returning stale sample results', async () => {
  vi.mocked(apiFetch).mockRejectedValue(new Error('API request failed'));
  await expect(loadDetections('stored.png', new AbortController().signal)).rejects.toThrow(
    'API request failed',
  );
});
