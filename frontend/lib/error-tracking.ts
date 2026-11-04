import * as Sentry from '@sentry/nextjs';

// Optional error tracking. Without a DSN nothing is initialized, no network
// calls happen, and no PII ever leaves the browser or the server runtime.
// Instrumentation files call this on boot; the DSN comes from the environment.
export function initErrorTracking(dsn: string | undefined): boolean {
  if (!dsn) return false;
  Sentry.init({
    dsn,
    tracesSampleRate: 0,
    // v11 replacement for sendDefaultPII=false: collect no user-identifying
    // data — no user fields, cookies, headers, bodies, or query parameters.
    dataCollection: {
      userInfo: false,
      cookies: false,
      httpHeaders: false,
      httpBodies: [],
      urlQueryParams: false,
    },
  });
  return true;
}
