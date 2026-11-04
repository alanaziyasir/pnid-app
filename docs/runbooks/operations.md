# Operations runbook

## First response and health

The repository does not define a production environment or on-call destination.
Use the deployment platform's logs and revision/rollback controls for your
actual service. Never assume that a release here deployed anything.

1. Check frontend `/health` and backend `/health`. Both should return HTTP 200
   with `status: healthy`. These are liveness probes, not provider readiness.
2. Record the affected revision, UTC time window, HTTP status, route template,
   and `X-Request-ID`. Do not collect user filenames, request bodies, or prompts.
3. Correlate the browser API request's ID with backend JSON logs and provider
   request headers. Invalid client IDs are replaced with generated IDs.
4. Check the [local monitoring queries and alerts](../../monitoring/README.md).
   Compare error rate and p95 latency before/after the revision.

## Chat/provider outage

- Inspect status codes only. Provider bodies and exception messages are not
  exposed in errors or logs.
- Three consecutive transient provider failures open the per-process circuit
  for 30 seconds. One half-open probe is allowed, then either recovery or another
  cooldown. Chat POSTs are never retried, avoiding duplicate inference charges.
- Set `ENABLE_CHAT=false` in the backend environment and restart. The API returns
  503 and the frontend disables chat after loading `/api/features`.
- Verify uploads still work. Restore the flag after provider recovery and a
  successful smoke test. Local QA must use `scripts/run_qa.py`, never a real key.
- Multi-worker deployments have one breaker per process; this is not a
  distributed provider quota limiter.

## Upload failures

Check free disk space, writable `UPLOAD_DIR`, the 50 MiB limit, extension, and
CORS origin. Files are streamed with bounded chunks and failed partial writes
are removed. Do not delete existing uploads while diagnosing.
An upload response's browser-visible URL must point at the configured API.

## Deployment impact and rollback

Before rolling out, record a baseline using `pnid_http_requests_total` and
`pnid_http_request_duration_seconds`. Afterward monitor the same queries and
`probe_success` for both services in the Prometheus UI at `http://127.0.0.1:9090`.
These dashboards are local tooling, not evidence that production monitoring is
already connected. Configure your production scrape target and notification
receiver before calling alert delivery operational.

Rollback to the last known-good revision through the deployment platform if
error rate rises or either health probe fails. Recheck upload/preview and chat.
This is a manual playbook; automated deployment and rollback are not configured.

## Safe logging and privacy

Backend logs contain UTC timestamp, level, event, request ID, method, route
template, status, duration, and exception **type** only. Never add arbitrary
exception text, stack locals, Authorization/Cookie headers, URLs with query
strings, filenames, graph data, user identifiers, or chat bodies.
Frontend error logging accepts only event identifiers, request IDs, and status.
Uvicorn's normal access log can include client addresses and raw URLs; launch
production with `--no-access-log` and rely on application telemetry instead.
Configure retention and access control in the log destination; no external log
or error-tracker sink is currently connected.

## Development profiling

Run `make profile-backend`, exercise requests, then stop with Ctrl+C. Inspect
`reports/backend.prof` with `python -m pstats reports/backend.prof` using the venv.
Run `make profile-frontend` for a Node CPU profile in `reports/*.cpuprofile`;
open it in Chrome DevTools Performance. The browser's own Performance panel
profiles diagram interactions. Use only bundled diagrams during profiling.
`make analyze` generates interactive client/server bundle-weight reports.
Do not commit generated profiles or publish them; profiles can contain paths.
