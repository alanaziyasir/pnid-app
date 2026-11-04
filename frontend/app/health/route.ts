export function GET(): Response {
  return Response.json({ status: 'healthy', service: 'frontend' });
}
