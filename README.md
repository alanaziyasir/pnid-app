# P&ID Digitization

A Next.js browser UI and FastAPI API for uploading piping and instrumentation
diagrams, inspecting template-matched component overlays, and asking a Groq-backed
assistant about optional GraphML connectivity data.

**Current limitation:** detection uses ten bundled symbol templates, not a trained
model. Matches depend on the uploaded pixels, but only support similar symbols at
the original scale and orientation. Scores are correlations, not probabilities.
OCR is unavailable; no sample tags are shown. Local QA replaces only the external
chat provider with a clearly labeled stub.

`POST /api/detect` processes the `stored_name` returned by upload. Detection accepts
PNG/JPEG images up to four million pixels, with at most 100 results. CAD, PDF, and
other upload formats are not converted. Detected boxes do not generate GraphML or
make chat context specific to the upload.

## Run locally

Use **Node.js 24**, **Python 3.12**, npm, and GNU Make. No login, database, GPU,
model download, or credentials are required for the local QA path.

```bash
make setup
make qa
```

Open `http://127.0.0.1:3000`, upload `frontend/public/example.png`, choose
**Process**, switch overlay tabs, and send a chat question. Ctrl+C stops the
isolated stack and cleans only its temporary uploads.

See [QUICK_START.md](QUICK_START.md) for custom ports, Windows commands,
live-provider configuration, and detailed browser interactions.

Alternatively, open this folder in VS Code and choose **Reopen in Container**.
The [development container](.devcontainer/devcontainer.json) installs both
runtimes, dependencies, hooks, and Chromium with its required system libraries.
Use the same `make qa` workflow and forwarded ports.

## Repository map

| Application | Code | Commands |
| --- | --- | --- |
| Frontend | `frontend/app`, `frontend/lib` | `make test-frontend`, `make build-frontend` |
| Backend | `backend/app`, `backend/config.py` | `make test-backend`; API docs at `/docs` |
| Cross-application tooling | `scripts`, root `Makefile` | `make check`, `make e2e`, `make lock` |

The root Makefile defines application boundaries and orchestrates independent
checks and tests. `make -j2 test` runs both applications' unit suites concurrently.

## Verify changes

```bash
make check
make test
make build
npm --prefix frontend exec playwright install chromium
make e2e
```

CI runs quality checks, enforced coverage, production build timing, and real
browser/API security regressions. Reports are retained as artifacts. Tests never
need a live provider token. Browser retries are reported as flaky and fail CI.

## Environment and secrets

Use [backend/.env.example](backend/.env.example) and
[frontend/.env.example](frontend/.env.example). The backend loads a file only
when Uvicorn receives `--env-file .env`.

- `NEXT_PUBLIC_API_URL`: browser-reachable API URL, defaults to `http://localhost:8000`.
- `GROQ_API_KEY`: optional backend-only live-chat secret. Provision through your
  deployment platform's secret settings, never through source control or public
  frontend variables. Revoke at the provider and rotate the deployment secret if leaked.
- `GROQ_API_URL`: optional compatible provider endpoint.
- `GRAPHML_PATH`: optional graph file, defaults to `data/graph.graphml`.
- `UPLOAD_DIR`: writable upload storage, defaults to `backend/uploads`.
- `FRONTEND_URL`: exact additional CORS origin. Do not enable `ALLOW_ALL_ORIGINS`
  for normal deployments.
- `ENABLE_CHAT`: defaults to `true`; set `false` to disable provider requests and
  the UI chat controls after a backend restart.
- `ENABLE_METRICS`: defaults to `false`; enable `/metrics` only behind a trusted
  network boundary. It exposes operational counts, not user data.

This prototype has **no authentication**. Uploaded diagrams and `/api/files` are
public to anyone who can reach the API. Do not expose it to untrusted users or
upload confidential diagrams without first adding access control and retention.

## More guidance

- [AGENTS.md](AGENTS.md): agent workflow and source-of-truth commands.
- [CONTRIBUTING.md](CONTRIBUTING.md): naming, tests, dependency policy, and review.
- [QUALITY.md](QUALITY.md): formatter, lint, typing, dead-code, and duplication gates.
- [backend/openapi.json](backend/openapi.json): generated, CI-validated API contract.
- [Operations runbook](docs/runbooks/operations.md): request IDs, metrics, outages, profiling.
- [Monitoring setup](monitoring/README.md): local dashboard queries and alert rules.
- [Readiness boundaries](docs/READINESS.md): what requires external setup or history.
