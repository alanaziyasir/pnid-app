import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  workers: 1,
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
