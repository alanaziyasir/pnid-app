# Agent instructions

## Setup and application boundaries

Use Node.js 24 and Python 3.12. The frontend is Next.js/React TypeScript in
`frontend/`; the backend is FastAPI in `backend/`. Commands below run from the
repository root. The Makefile is the shared command contract; do not invent a
second setup path or install optional ML dependencies for normal API work.

```bash
make setup
```

This installs hash-locked runtime/development Python dependencies, runs npm ci,
and installs the checked-in pre-commit hooks.

## Change and verify

1. Read the affected code and current diff. Preserve unrelated user changes.
2. Write meaningful regression tests alongside behavioral changes.
3. Run the smallest relevant suite, then the shared gates:

```bash
make check
make test
make build
```

`make check` validates formatting, complexity, unused code/dependencies, strict
typing, docs/commands, issue-linked debt markers, duplicate code, file sizes,
feature flag lifecycle, dependency drift, dependency weight, and the OpenAPI
snapshots. CI executes these same commands.
Never suppress rules, omit tests, or raise thresholds merely to get green checks.

Backend tests use `backend/tests/test_*.py`; script tests use `scripts/test_*.py`.
Frontend unit tests use `*.test.ts` in `frontend/lib` or `frontend/app`; browser
tests use `frontend/e2e/*.spec.ts`. Python tests run in two isolated workers with
randomized ordering and temporary upload directories. Vitest isolates files.
Backend coverage is at least 85% including branches. Frontend unit coverage
applies to `lib/` and the health handler, not React page rendering. Browser tests
cover the real pages. Do not claim frontend unit coverage covers the entire UI.

## Interactive QA, without secrets

```bash
make qa
```

There is no login. Wait for `QA ready`, open the printed frontend URL, upload
`frontend/public/example.png`, expand/close the preview, choose Process, switch
Components/Tags/All, and send a question. Expect a response labeled Local QA
stub. Remove a second upload. Ctrl+C cleans up this run's processes/storage.
See [QUICK_START.md](QUICK_START.md) for dependencies, ports, and failure recovery.

For automation, install Playwright Chromium once, then:

```bash
make e2e
```

Do not contact Groq or use real user diagrams in tests. The QA launcher overrides
provider settings. Process performs bounded local template matching, not trained
model inference. OCR is unavailable; do not restore fabricated sample tags.

## Conventions and contracts

- Python: snake_case functions/variables/modules, PascalCase classes, UPPER_CASE
  constants. Ruff enforces naming, imports, unused symbols, and complexity.
- TypeScript: camelCase functions/variables, PascalCase React components/types,
  UPPER_CASE module constants. Keep API wire keys snake_case where required.
- Keep functions at complexity 15 or less. Split responsibilities instead of
  adding exemptions. Files must stay below 1 MiB, including assets/lockfiles.
- Route all browser requests through `frontend/lib/api.ts`, and browser errors
  through `frontend/lib/logger.ts`. Never log bodies, filenames, graph content,
  credentials, query strings, or user identifiers. Backend logs only allowlisted
  metadata. Correlate requests using `X-Request-ID`.
- Debt comments must use `TODO(https://github.com/alanaziyasir/pnid-app/issues/123)`
  or the equivalent FIXME form with a real existing issue. Do not invent issues.
- Edit Python dependency inputs (`*.in`), then run `make lock`. Resolve shared
  version drift rather than overriding checks. Wait seven days before merging
  non-emergency dependency updates. See [CONTRIBUTING.md](CONTRIBUTING.md).
- After API changes regenerate the checked-in contract:

```bash
make schema
```

## Safety and operations

No authentication exists. Local QA binds loopback and needs no credentials.
Use `.env.example` files for the documented environment contract, and never
commit real `.env` files. Never publish, change repository settings, create
issues, trigger releases, or deploy without an explicit user request.
The chat kill switch is operational, not authorization. `/metrics` is disabled
by default. Follow [the runbook](docs/runbooks/operations.md) for outages.

The repository-local `pnid-change` skill packages this validation workflow for
agent-assisted changes. Report actual checks and blockers, not an inferred score.
