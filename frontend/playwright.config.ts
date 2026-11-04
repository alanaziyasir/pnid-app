import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  workers: 2,
  retries: process.env.CI ? 1 : 0,
  failOnFlakyTests: Boolean(process.env.CI),
  reporter: [
    ['list'],
    ['junit', { outputFile: 'test-results/e2e.xml' }],
    ['html', { open: 'never' }],
  ],
  use: {
    baseURL: 'http://127.0.0.1:3100',
    browserName: 'chromium',
    trace: 'retain-on-failure',
  },
  webServer: {
    command: 'python3 ../scripts/run_qa.py --frontend-port 3100 --backend-port 8100',
    url: 'http://127.0.0.1:3100',
    // Never silently reuse another process or an API with live credentials.
    reuseExistingServer: false,
    timeout: 150_000,
    gracefulShutdown: { signal: 'SIGTERM', timeout: 15_000 },
  },
});
