---
name: pnid-change
description: Implement and validate changes to this P&ID Next.js/FastAPI application. Use when changing upload, template detection, analysis, chat, or shared QA tooling.
---

# P&ID change workflow

1. Read `AGENTS.md`, the current diff, and the affected route/page/helper. Confirm
   whether behavior is template-matched or provider-backed before making claims.
   Template matching has fixed scale/orientation limits; OCR is unavailable.
2. Add a meaningful regression test. Use temporary storage and the in-memory
   provider fixture for API tests. Never contact Groq or use private diagrams.
3. Implement the focused change. Preserve unrelated work, API wire keys,
   request-ID propagation, and the logging allowlist.
4. Run the relevant unit suite, then `make check` and `make test`.
5. If routes or models changed, run `make schema` and review the schema diff.
   If UI behavior changed, run `make build` and `make e2e` with Chromium installed.
6. For manual QA run `make qa`, use the bundled example diagram, test preview,
   overlay tabs, and the labeled stub chat, then stop the launcher.
7. Report the commands actually run and any limitations. Do not commit, publish,
   create issues, or deploy unless the user explicitly requests it.
