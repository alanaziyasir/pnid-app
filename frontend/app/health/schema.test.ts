import { readFile } from 'node:fs/promises';
import { join } from 'node:path';
import { expect, it } from 'vitest';
import { GET } from './route';

// The committed contract in frontend/openapi.json must stay in sync with the
// actual route response. If the response shape changes, update the schema in
// the same change, exactly like `make schema` enforces for the backend.
async function committedSchema(): Promise<{
  openapi: string;
  paths: Record<string, Record<string, { responses: Record<string, unknown> }>>;
  components: {
    schemas: Record<string, Record<string, unknown>>;
  };
}> {
  const body = await readFile(join(process.cwd(), 'openapi.json'), 'utf8');
  return JSON.parse(body);
}

it('documents every route response in the committed OpenAPI contract', async () => {
  const schema = await committedSchema();
  expect(schema.openapi).toBe('3.1.0');
  expect(Object.keys(schema.paths)).toEqual(['/health']);
});

it('keeps the /health schema in sync with the route response', async () => {
  const schema = await committedSchema();
  const body = (await GET().json()) as Record<string, string>;
  const ref = (
    schema.paths['/health'].get.responses['200'] as {
      content: { 'application/json': { schema: { $ref: string } } };
    }
  ).content['application/json'].schema.$ref;
  const health = schema.components.schemas[ref.split('/').pop() as string] as {
    required: string[];
    properties: Record<string, { const: string; type: string }>;
  };
  expect(Object.keys(body).sort()).toEqual([...health.required].sort());
  for (const [key, value] of Object.entries(body)) {
    expect(typeof value).toBe(health.properties[key].type);
    expect(value).toBe(health.properties[key].const);
  }
});
