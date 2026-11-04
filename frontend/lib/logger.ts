type Event = 'upload_failed' | 'chat_failed' | 'detection_failed' | 'api_request_failed';
interface Context {
  requestId?: string;
  status?: number;
}

// Only allowlisted operational fields cross this boundary. Never accept Error,
// filenames, query strings, provider responses, chat text, or user identifiers.
export function logError(event: Event, context: Context = {}): void {
  console.error(
    JSON.stringify({
      level: 'error',
      event,
      requestId: context.requestId,
      status: context.status,
    }),
  );
}
