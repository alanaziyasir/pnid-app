# Interactive QA

See [the repository quick start](../QUICK_START.md) for the maintained,
end-to-end QA procedure.

From the repository root, after dependency installation:

```bash
python3 scripts/run_qa.py
```

The launcher waits for FastAPI and Next.js, prints their URLs, isolates uploads,
and replaces the external chat provider with an explicitly labeled local stub.
No services are assumed to be already running.

For automated Chromium coverage of the real frontend/API:

```bash
cd frontend
npx playwright install chromium
npm run test:e2e
```

This tests upload, stored bytes, preview/fullscreen, analysis navigation and tabs,
chat, removal, and file validation. The quick start documents browser system
dependencies, ports, environment variables, expected results, and cleanup.
