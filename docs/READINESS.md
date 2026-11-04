# Readiness boundaries

Local automation is not proof of historical or externally connected signals.
Do not report a new readiness score without a fresh evaluation.

## Implemented locally

- Both applications: lint, formatting, complexity, dead/unused-code checks,
  strict typing, useful tests, naming/test conventions, isolated execution,
  retained timing reports, and enforced coverage for the documented unit scope.
- Shared hooks, size gate, duplication scan, issue-linked debt policy,
  hash-locked Python profiles, npm lockfile, cross-profile drift checks,
  dependency update/delay policy, and root multi-application Make orchestration.
- Real browser QA and dynamic security regression tests, frontend/API health
  probes, request-ID propagation, safe structured logs, backend metrics and
  provider circuit breaker, GET-only exponential backoff, chat kill switch,
  development profiling commands, and optional monitoring rules/runbooks.
- Root setup/agent/contribution docs, validated agent commands and links,
  reusable agent skill, generated OpenAPI snapshot, devcontainer config,
  environment/secret guidance, ownership/templates, and release-note automation.

Frontend metrics currently cover health probes, not browser product analytics.
Frontend unit coverage covers API/detection/logging/format helpers and the health handler;
Playwright exercises React pages. No claim is made that unit coverage covers UI
rendering. Optional ML dependency locks are resolved, not GPU/inference tested.
Local component detection now uses image-dependent fixed-scale template matching,
not a trained ML detector. OCR and upload-specific graph generation remain
unavailable. See the [quick start](../QUICK_START.md) for processing limits.

## Verified locally

- `make check`, pre-commit hooks, production build with bundle reports, and
  `npm audit` (zero findings).
- 71 Python tests, 27 frontend unit tests, and seven real browser/security tests.
  Backend coverage is 98.14%; the documented frontend unit scope reaches 100%.
- Hash-locked installation into a clean temporary Python environment.
- Full development-container build, boot, dependency/browser setup, quality
  checks, unit tests, and browser QA in a disposable checkout.
- Prometheus configuration and alert behavior with promtool, plus a live API
  scrape and successful frontend/backend health probes.
- Actual Python cProfile and Node CPU-profile output after driving health routes.

Validation still emits an upstream Starlette/httpx TestClient deprecation
warning and Next.js's advisory that the optional Next-specific ESLint plugin is
not configured. Checks pass; neither warning is suppressed.

## Requires repository owner or external environment

- **Historical evidence:** sub-10-minute CI, deployment frequency, recent
  committed documentation, active agent co-authorship, bot review comments,
  and backlog health cannot be manufactured by local files.
- **CI and integrations:** commit/push the reviewed changes to run workflows.
  Install/enable Renovate for update PRs. Allow Actions release PRs. Manually
  sync the checked-in label taxonomy. Configure required checks/branch protection.
  No external writes or settings changes were performed for this task.
- **Automated code review:** needs a chosen provider, credentials/installation,
  and explicit permission to post review content. Existing checks do not count
  as generated review comments.
- **Deployment:** no production targets, publishing credentials, or auto-deploy
  policy were supplied. GitHub release automation is not application deployment.
- **Observability:** backend metrics and local alert rules are not a connected
  production paging system. Configure real targets, an Alertmanager receiver,
  dashboards, retention, and access controls. Frontend browser telemetry/APM,
  contextual error tracking, source-map upload, and error-to-issue integration
  require an explicit service/privacy decision and real credentials.
- **Product analytics:** needs approved events, consent/retention policy, and
  an actual analytics destination. No tracking was silently added.
- **Platform portability:** Linux/container execution is verified; native Windows,
  macOS, GPU inference, and production deployment are not verified by these checks.

See [the operations runbook](runbooks/operations.md) for safe rollout checks.
