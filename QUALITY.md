# Quality gates

These checks cover the Next.js frontend, the Python backend, and Python
development scripts. Run commands below from the repository root.
Application setup and browser QA are documented in [QUICK_START.md](QUICK_START.md).

## Install once per checkout

Use Node.js 24 and Python 3.12.
ESLint requires Node 20.19+, 22.13+, or 24+; older application-compatible Node
versions cannot run the quality tools.

```bash
python3 -m venv backend/venv
backend/venv/bin/python -m pip install -r requirements-dev.txt
npm --prefix frontend ci
backend/venv/bin/python -m pre_commit install
```

The first hook run downloads isolated, pinned Python hook environments.
Frontend hooks use the tools installed by `npm ci`, not globally installed
versions. Development requirements include the runtime requirements plus quality tools.
On Windows, replace `backend/venv/bin/python` with
`backend\venv\Scripts\python.exe`.

The frontend pins the tools' transitive `minimatch` dependency to 11.0.4 because
versions below 11.0.1 are affected by
[GHSA-g3hv-75wg-m249](https://github.com/advisories/GHSA-g3hv-75wg-m249).
The current upstream ranges still request version 10. Remove the override once
both ESLint and its TypeScript parser require a patched version themselves.
Recheck frontend file discovery and the complexity gate when updating it.

## Check everything

```bash
backend/venv/bin/python -m pre_commit run --all-files
```

The same checked-in hooks run on pull requests and pushes to `main` in
`.github/workflows/quality.yml`. After installation, commits run them on the
staged files; a frontend change checks the entire frontend for consistency.
Checks do not modify files. Fix any failures, stage the fixes, and commit again.

| Gate | Scope | Policy |
| --- | --- | --- |
| Prettier | Frontend TS/TSX, JS, CSS, JSON, and supported text/config files | Single quotes, semicolons, 100-column wrapping |
| Ruff format | Backend and Python development scripts | Double quotes, four-space indentation, 100-column wrapping |
| ESLint `complexity` | All first-party frontend JS/TS, including components, configs, and browser tests | At most 15 paths per function |
| Ruff `C901` | All first-party Python, including API routes and QA scripts | McCabe complexity at most 15 per function |
| Large files | Every tracked/staged file, including images and lockfiles | Reject files over 1 MiB (1024 KiB), including modifications to existing files |

Generated output, dependency directories, and frontend static artwork are not
reformatted. Artwork is still checked for size; existing assets fit the limit.
ESLint checks complexity, unreachable/dead code, unused symbols, accidental `any`,
debugger statements, and equality safety. Ruff additionally checks imports,
unused Python symbols, naming, and common correctness issues.
The tools count language constructs differently; both limits are enforced,
without per-file exceptions. Split functions by responsibility when a limit is
exceeded instead of increasing the limit or suppressing the check.

## Fix formatting

```bash
npm --prefix frontend run format
backend/venv/bin/python -m ruff format backend scripts
```

Review and stage the formatter output before committing. Generated files such
as `package-lock.json` and `next-env.d.ts` should be changed only by their
owning tools, not hand-formatted.

Individual read-only checks are also available:

```bash
npm --prefix frontend run format:check
npm --prefix frontend run check:complexity
backend/venv/bin/python -m ruff format --check backend scripts
backend/venv/bin/python -m ruff check backend scripts
```

For oversized files, optimize the asset or put large datasets/model artifacts in
external artifact storage. Do not commit user uploads, dependency directories,
or generated build output. Any future size-policy change needs a concrete
justification in review, not a blanket exclusion.

Quality gates do not replace application tests. Run the type check, launcher
regressions, and browser tests from the quick start after changing behavior.

## Repository-wide checks

`make check` also runs strict mypy/TypeScript, Knip (unused frontend files,
exports and dependencies), deptry (unused/undeclared API dependencies), jscpd
(Python/TypeScript duplication, at most 5%, minimum clone 12 lines/100 tokens),
and `scripts/check_repo.py` (documentation links/command targets, issue-linked
debt comments, file sizes, and dependency drift across all Python lock profiles).
The OpenAPI snapshot must exactly match FastAPI's generated contract.
Tests are excluded from duplication analysis because independent explicit test
assertions and fixtures are not production reuse opportunities.

Use `make test` for enforced coverage: 85% backend branch/line coverage and 90%
frontend helper/health-handler coverage (85% branches). The React pages are
covered separately by Playwright, not included in the unit coverage claim.
Reports, timings, traces, build metrics, and bundle analysis are retained in CI.
`make analyze` generates Next.js bundle reports for dependency-weight inspection.
