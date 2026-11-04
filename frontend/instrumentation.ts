export async function register(): Promise<void> {
  if (process.env.NEXT_RUNTIME !== 'nodejs') return;
  const { initErrorTracking } = await import('./lib/error-tracking');
  initErrorTracking(process.env.SENTRY_DSN);
}
