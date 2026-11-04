import { expect, it } from 'vitest';
import { GET } from './route';

it('exposes a credential-free frontend liveness probe', async () => {
  const response = GET();
  expect(response.status).toBe(200);
  expect(await response.json()).toEqual({ status: 'healthy', service: 'frontend' });
});
