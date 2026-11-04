import { apiFetch } from './api';

export interface Detection {
  class_id: number;
  conf: number;
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  image_hw: [number, number];
}

export interface DetectionResult {
  detector: 'template_matching';
  ocr_available: false;
  image_hw: [number, number];
  detections: Detection[];
  limit_reached: boolean;
}

// The detector serves a bounded number of concurrent images and replies 503
// when its slots are full. Detection is a read-only computation on a stored
// upload, so replaying the POST is safe and lets interactive QA survive
// parallel workers and React StrictMode's double-fired effects.
const BUSY_RETRIES = 3;
const BUSY_RETRY_BASE_DELAY_MS = 200;

function waitFor(ms: number, signal: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    if (signal.aborted) {
      reject(new DOMException('Aborted', 'AbortError'));
      return;
    }
    const timer = setTimeout(() => {
      signal.removeEventListener('abort', onAbort);
      resolve();
    }, ms);
    const onAbort = () => {
      clearTimeout(timer);
      reject(new DOMException('Aborted', 'AbortError'));
    };
    signal.addEventListener('abort', onAbort, { once: true });
  });
}

async function requestDetection(storedName: string, signal: AbortSignal): Promise<Response> {
  return apiFetch('/api/detect', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ stored_name: storedName }),
    signal,
  });
}

export async function loadDetections(
  storedName: string,
  signal: AbortSignal,
): Promise<DetectionResult> {
  let response = await requestDetection(storedName, signal);
  for (let attempt = 0; response.status === 503 && attempt < BUSY_RETRIES; attempt++) {
    await waitFor(BUSY_RETRY_BASE_DELAY_MS * 2 ** attempt, signal);
    response = await requestDetection(storedName, signal);
  }
  if (!response.ok) {
    const messages: Record<number, string> = {
      404: 'The uploaded image was not found. Please upload it again.',
      415: 'Detection supports PNG and JPEG images only.',
      422: 'Unable to process this image. Use a valid PNG or JPEG of at most 4 million pixels.',
    };
    throw new Error(messages[response.status] || 'Detection is unavailable. Please try again.');
  }
  return response.json() as Promise<DetectionResult>;
}
