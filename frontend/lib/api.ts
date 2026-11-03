// Browser-visible URL, shared by uploads, previews, and chat.
export const API_URL = (
  process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
).replace(/\/$/, '');
