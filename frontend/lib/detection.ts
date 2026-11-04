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

export async function loadDetections(
  storedName: string,
  signal: AbortSignal,
): Promise<DetectionResult> {
  const response = await apiFetch('/api/detect', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ stored_name: storedName }),
    signal,
  });
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
