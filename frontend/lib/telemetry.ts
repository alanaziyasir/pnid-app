import { apiFetch } from './api';

// Allowlisted product events, mirrored from backend/app/routers/events.py.
// Payloads carry only the event name and an optional coarse HTTP status;
// never filenames, content, chat text, or user identifiers.
export type FeatureEvent =
  | 'upload_started'
  | 'upload_completed'
  | 'upload_failed'
  | 'detection_started'
  | 'detection_completed'
  | 'detection_failed'
  | 'chat_sent'
  | 'chat_failed';

interface FeatureEventPayload {
  type: FeatureEvent;
  status?: number;
}

export function trackEvent(event: FeatureEvent, status?: number): void {
  // Fire-and-forget: product analytics must never block or break the UI, and
  // a failed report is not an application error worth surfacing to the user.
  const payload: FeatureEventPayload = { type: event, ...(status ? { status } : {}) };
  void apiFetch('/api/events', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ events: [payload] }),
    silent: true,
  }).catch(() => undefined);
}
