# Contributing

Follow [AGENTS.md](AGENTS.md) for setup and validation commands and
[QUALITY.md](QUALITY.md) for enforced gates. Keep each change focused and include
tests for actual behavior. AI-assisted changes follow exactly the same review,
privacy, and validation rules as other changes.

## Naming and tests

Python modules/functions/variables use snake_case, classes use PascalCase,
and module constants use UPPER_CASE. TypeScript functions/variables use camelCase,
React components/types use PascalCase, and module constants use UPPER_CASE.
Preserve API snake_case keys at wire boundaries. Ruff enforces Python naming;
reviewers enforce TypeScript naming in addition to ESLint's static checks.

Use Python `test_*.py`, frontend `*.test.ts`, and browser `*.spec.ts` naming.
Keep each test's storage isolated. Do not call real providers, rely on test order,
or add arbitrary sleeps. Playwright retries once in CI to identify flakes;
`failOnFlakyTests` still fails the job. A retry is not a successful fix.
CI also runs `make test-stability`, repeating pytest-style Python tests three
times with randomized ordering and retaining a separate JUnit report. Legacy
unittest cases still run once. Every repetition must pass; there is no
retry-to-green or blanket quarantine.

## Dependencies

Production API imports are declared in `backend/requirements-deploy.in`.
Development tooling is in `requirements-dev.in`. Optional historical ML inputs
are in `backend/requirements-ml.in` and `backend/requirements-minimal.in`; they
are not API requirements and should be installed in separate environments.

Run `make lock` with the pinned uv version to regenerate all hash-locked
requirements. Resolution is ordered so shared packages agree across profiles.
`make check` rejects version drift and npm manifest/lock mismatches.
Use npm install for frontend changes and include its lockfile.

**Minimum release age: seven days.** Wait at least seven days after publication
before merging ordinary dependency updates. Renovate encodes the same delay and
groups related updates; security emergencies may be expedited only with an
explicit review explaining the risk and validation. Do not use force or legacy
peer-dependency bypasses to install an incompatible tree.

The frontend PostCSS override stays within version 8 and patches the vulnerable
copy bundled by Next.js 15. Remove it only once the framework requires a patched
version itself, then rerun lint, build, browser QA, and npm audit.

## Technical debt and issues

Debt comments must link an existing issue with an owner, impact, and resolution
criteria: `TODO(https://github.com/alanaziyasir/pnid-app/issues/123)`.
The source scanner rejects unlinked TODO/FIXME comments. File a real issue only
when authorized; no synthetic tickets merely to satisfy a check.

## Feature flags

Feature flags follow a documented lifecycle: define `ENABLE_*` (backend
`config.py`) or `NEXT_PUBLIC_ENABLE_*` (frontend code) switches, document them
in the matching `.env.example`, and wire them into application code. `make check`
fails a flag that is defined but undocumented, documented but undefined, or
referenced only by tests and scripts. When a flag's rollout is complete, remove
both the switch and its `.env.example` entry in the same change; the gate then
keeps dead switches out of the tree automatically.


Issue taxonomy is checked into [.github/labels.json](.github/labels.json):
priority P0–P3, type bug/feature/chore, and area frontend/backend/infra.
An owner can run the manual **Sync issue labels** workflow once to apply it.
Templates collect concrete reproduction/acceptance criteria without secrets.

## Review and releases

Fill out the [PR template](.github/pull_request_template.md). Include tests run,
observable behavior, API contract changes, rollout/rollback notes, and known
limitations. Never paste real diagrams, prompts, credentials, or private logs.

Release Please proposes a version/changelog PR from conventional commits
(`feat:`, `fix:`, `chore:`). Merging its approved release PR creates a GitHub
release with generated notes. It does not deploy either application. A repository
owner must allow GitHub Actions to create pull requests before this can run.
