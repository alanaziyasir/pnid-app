export async function register(): Promise<void> {
  const { initErrorTracking } = await import('./lib/error-tracking');
  initErrorTracking(process.env.NEXT_PUBLIC_SENTRY_DSN);
}
