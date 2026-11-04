// Browser-visible URL, shared by uploads, previews, and chat.
import { logError } from './logger';

export const API_URL = (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000').replace(
  /\/$/,
  '',
);

export async function apiFetch(path: string, options: RequestInit = {}): Promise<Response> {
  const method = (options.method || 'GET').toUpperCase();
  const attempts = method === 'GET' ? 3 : 1;
  const requestId = crypto.randomUUID
    ? crypto.randomUUID()
    : Array.from(crypto.getRandomValues(new Uint8Array(16)), (byte) =>
        byte.toString(16).padStart(2, '0'),
      ).join('');
  const headers = new Headers(options.headers);
  headers.set('X-Request-ID', requestId);
  const signal = AbortSignal.any(
    [AbortSignal.timeout(60_000), options.signal].filter((s): s is AbortSignal => Boolean(s)),
  );
  for (let attempt = 0; attempt < attempts; attempt++) {
    try {
      const response = await fetch(`${API_URL}${path}`, { ...options, headers, signal });
      if (!response.ok) logError('api_request_failed', { requestId, status: response.status });
      if (![429, 502, 503, 504].includes(response.status) || attempt === attempts - 1) {
        return response;
      }
    } catch {
      if (signal.aborted || attempt === attempts - 1) {
        logError('api_request_failed', { requestId });
        throw new Error('API request failed. Please try again.');
      }
    }
    // Only safe GETs are retried. Uploads and billable chat are never replayed.
    await new Promise<void>((resolve) => setTimeout(resolve, 200 * 2 ** attempt));
  }
  throw new Error('API request failed');
}
