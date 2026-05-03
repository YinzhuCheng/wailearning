# BIMSA-CLASS

BIMSA-CLASS is a school and classroom management platform built with FastAPI, Vue 3, PostgreSQL, and a separate parent portal. It combines day-to-day academic administration with course-level LLM-assisted homework grading, async grading queues, quota controls, and attachment-aware submission processing.

## Read Before Work

This repository expects contributors, including LLM coding agents, to read the relevant documentation before making changes. Do not treat the file tree alone as the source of truth.

Minimum rule:

- before changing repository structure or file placement, read [docs/architecture/REPOSITORY_STRUCTURE.md](docs/architecture/REPOSITORY_STRUCTURE.md)
- before changing backend or product behavior, read [docs/architecture/SYSTEM_OVERVIEW.md](docs/architecture/SYSTEM_OVERVIEW.md) and any feature-specific product document such as [docs/product/LLM_HOMEWORK_GUIDE.md](docs/product/LLM_HOMEWORK_GUIDE.md)
- before running tests or diagnosing failures, read [docs/development/DEVELOPMENT_AND_TESTING.md](docs/development/DEVELOPMENT_AND_TESTING.md) and [docs/development/TEST_EXECUTION_PITFALLS.md](docs/development/TEST_EXECUTION_PITFALLS.md)
- before editing multilingual files from Windows + PowerShell, read [docs/development/ENCODING_AND_MOJIBAKE_SAFETY.md](docs/development/ENCODING_AND_MOJIBAKE_SAFETY.md)
- when assessing structural risk or full-suite follow-ups inferred from tests, see [docs/architecture/TEST_INFERRED_RISKS_AND_FOLLOWUPS.md](docs/architecture/TEST_INFERRED_RISKS_AND_FOLLOWUPS.md)
- before deployment or service changes, read [docs/operations/DEPLOYMENT_AND_OPERATIONS.md](docs/operations/DEPLOYMENT_AND_OPERATIONS.md) and [docs/operations/ADMIN_BOOTSTRAP.md](docs/operations/ADMIN_BOOTSTRAP.md)
- before touching parent-facing flows, read [docs/product/PARENT_PORTAL.md](docs/product/PARENT_PORTAL.md)

Practical expectation:

- if you skip the relevant docs, you are likely to misread compatibility layers, confuse local artifacts for source layout, or waste time on known Windows/PowerShell test traps
- if you discover a new behavior constraint, environment pitfall, or operational rule while working, update the corresponding document in the same change set

## Highlights

- Multi-role access for admins, class teachers, subject teachers, students, and parent-code users.
- Class, student, user, and roster management with reconciliation between user accounts and student roster rows.
- Required and elective course flows, including self-enrollment, roster enrollment, batch class moves, and enrollment repair.
- Homework lifecycle with multiple attempts, late-submission rules, score candidates, teacher review, regrade, and student appeals.
- Course material chapters, notifications, attendance, semester management, scores, score-composition appeals, and a points system.
- Parent portal served as a separate SPA under `/parent/`.
- API-first backend with local `pytest` and browser-level Playwright E2E coverage.

## LLM-Assisted Homework Grading

The LLM subsystem is one of the core product features, not an add-on.

- Admins manage reusable endpoint presets under `/api/llm-settings`.
- Presets track validation state, vision capability, retry settings, and timeouts.
- Teachers configure LLM behavior per course, including enablement, prompts, endpoint order, timezone-aware quota boundaries, and token estimation limits.
- Homework can opt into async auto-grading while still allowing teacher override and regrade.
- Submissions support text and attachment flows, including images, PDFs, notebooks, archives, and extracted text payloads.
- The grading worker is database-backed, can reclaim stale tasks, and records token usage per student and per course.
- Failure handling includes quota enforcement, endpoint failover, retry logic, manual regrade, and observable task states.

See [docs/product/LLM_HOMEWORK_GUIDE.md](docs/product/LLM_HOMEWORK_GUIDE.md) for the current implementation details.

## Tech Stack

- Backend: FastAPI, SQLAlchemy, PostgreSQL, Pydantic v2
- Frontend: Vue 3, Vite, Element Plus, Pinia, ECharts
- Parent portal: separate Vue 3 + Vite application
- Testing: `pytest`, Playwright
- Deployment: Nginx, `gunicorn`, `uvicorn`, `systemd`

## Repository Layout

```text
apps/backend/wailearning_backend/   Canonical FastAPI backend package
apps/web/admin/                     Admin SPA and Playwright config
apps/web/parent/                    Parent-facing SPA
docs/                               Documentation hub organized by topic
ops/                                CI, nginx, systemd, and deployment scripts
tests/                              Backend, behavior, and browser E2E suites
tools/                              Repository maintenance and audit helpers
```

Repository-boundary rules:

- The repository root should contain only repository-level entry files and configuration such as `README.md`, `LICENSE`, `requirements.txt`, `pytest.ini`, and the root `conftest.py`.
- Windows convenience launchers live under `ops/scripts/windows/` instead of being scattered across the root or app folders.
- The backend import namespace is intentionally explicit: `apps.backend.wailearning_backend`. Do not reintroduce a root compatibility package or a second shorter alias.
- Local runtime artifacts such as `frontend/`, `.pytest_tmp/`, `.e2e-run/`, `test-results/`, and `uploads/` are not part of the source layout even if they appear on a developer machine.

See [docs/architecture/REPOSITORY_STRUCTURE.md](docs/architecture/REPOSITORY_STRUCTURE.md) for the detailed structure contract and migration rationale.

## Quick Start

### Backend

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn apps.backend.wailearning_backend.main:app --host 127.0.0.1 --port 8001 --reload
```

Windows convenience launcher:

```bat
ops\scripts\windows\start-backend.bat
```

Backend docs:

- Swagger UI: `http://127.0.0.1:8001/docs`
- ReDoc: `http://127.0.0.1:8001/redoc`

### Admin Frontend

```bash
cd apps/web/admin
npm install
npm run dev
```

Windows convenience launcher:

```bat
ops\scripts\windows\start-admin-frontend.bat
```

Default local frontend URL: `http://127.0.0.1:3000` unless `VITE_DEV_PORT` overrides it.

### Parent Portal

```bash
cd apps/web/parent
npm install
npm run dev
```

Windows convenience launcher:

```bat
ops\scripts\windows\start-parent-frontend.bat
```

Default local parent-portal URL: `http://127.0.0.1:5174` unless `VITE_DEV_PORT` overrides it.

## Core Environment Variables

Key backend settings are defined in [`apps/backend/wailearning_backend/core/config.py`](apps/backend/wailearning_backend/core/config.py).

- `DATABASE_URL`
- `SECRET_KEY`
- `APP_ENV`
- `INIT_ADMIN_USERNAME`
- `INIT_ADMIN_PASSWORD`
- `INIT_ADMIN_REAL_NAME`
- `INIT_DEFAULT_DATA`
- `ALLOW_PUBLIC_REGISTRATION`
- `BACKEND_CORS_ORIGINS`
- `TRUSTED_HOSTS`
- `ENABLE_LLM_GRADING_WORKER`
- `LLM_GRADING_WORKER_LEADER`
- `LLM_GRADING_WORKER_POLL_SECONDS`
- `LLM_GRADING_TASK_STALE_SECONDS`
- `DEFAULT_LLM_API_KEY`
- `REQUIRE_STRONG_SECRETS`
- `E2E_DEV_SEED_ENABLED`
- `E2E_DEV_SEED_TOKEN`

Admin bootstrap and demo seed behavior are documented in [docs/operations/ADMIN_BOOTSTRAP.md](docs/operations/ADMIN_BOOTSTRAP.md).

## Testing

Backend:

```bash
python -m pytest
python -m pytest tests/behavior -q
```

### PostgreSQL-Aligned UI/E2E Validation

PostgreSQL is the production database for this project. For serious UI/UX audits,
browser E2E validation, schema-sensitive backend changes, concurrency-sensitive
flows, or any result that will be used as a production-aligned signal, use a
dedicated throwaway PostgreSQL database instead of treating SQLite as the
reference environment.

Use a database name and user that are clearly reserved for local automation, for
example `wailearning_uiux_audit` or `wailearning_e2e_test`. Never point
`DATABASE_URL` or `TEST_DATABASE_URL` at a production database, a shared staging
database with real users, or any database whose contents must be preserved.

Recommended local pattern:

```powershell
# Example only. Create the database through your local PostgreSQL tooling first.
$env:DATABASE_URL = 'postgresql://USER:PASSWORD@127.0.0.1:5432/wailearning_uiux_audit'
$env:E2E_DEV_SEED_ENABLED = 'true'
$env:E2E_DEV_SEED_TOKEN = 'test-playwright-seed'
$env:INIT_DEFAULT_DATA = 'false'
$env:SECRET_KEY = 'local-uiux-test-secret-key-minimum-32-chars'
$env:ENABLE_LLM_GRADING_WORKER = 'false'
python -m uvicorn apps.backend.wailearning_backend.main:app --host 127.0.0.1 --port 8001
```

Then point the admin frontend at that backend:

```powershell
cd apps/web/admin
$env:VITE_PROXY_TARGET = 'http://127.0.0.1:8001'
npm.cmd run dev
```

Seed browser-test data through the guarded E2E reset endpoint, using the same
token supplied to the backend:

```powershell
Invoke-WebRequest `
  -Method POST `
  -Uri 'http://127.0.0.1:8001/api/e2e/dev/reset-scenario' `
  -Headers @{ 'X-E2E-Seed-Token' = 'test-playwright-seed' } `
  -UseBasicParsing
```

The admin Playwright config currently has a fast default that provisions a
SQLite database for ordinary local E2E runs. That path is useful for quick
feedback and for compatibility with machines that do not have PostgreSQL
running, but it is not the production-aligned reference for database behavior.
When validating UI/UX behavior that depends on real persistence semantics, run
against an explicitly started PostgreSQL backend and set:

```powershell
$env:PLAYWRIGHT_USE_EXTERNAL_SERVERS = '1'
$env:E2E_API_URL = 'http://127.0.0.1:8001'
$env:PLAYWRIGHT_BASE_URL = 'http://127.0.0.1:3000'
$env:E2E_DEV_SEED_TOKEN = 'test-playwright-seed'
npx.cmd playwright test
```

For backend pytest runs that should exercise PostgreSQL-only guards, set
`TEST_DATABASE_URL` to a separate throwaway PostgreSQL database before running
`python -m pytest`. The test reset helpers may drop and recreate schema in that
database, so do not reuse a database that contains data you care about.

Frontend E2E:

```bash
cd apps/web/admin
npm install
npx playwright install chromium
npm run test:e2e
```

Read [docs/development/TEST_EXECUTION_PITFALLS.md](docs/development/TEST_EXECUTION_PITFALLS.md) before assuming test failures are product regressions, especially on Windows + PowerShell or when running Playwright.

The historical "backlog" Playwright pair, `tests/e2e/web-admin/future-advanced-coverage*.spec.js`, is now implemented as normal runnable coverage in this branch. The old `E2E_ENABLE_BACKLOG_SPECS` gate survives only as a historical note for older branches; see [docs/development/E2E_BACKLOG_SCENARIOS.md](docs/development/E2E_BACKLOG_SCENARIOS.md).

See [docs/development/DEVELOPMENT_AND_TESTING.md](docs/development/DEVELOPMENT_AND_TESTING.md) for the full local workflow, Windows notes, reading order, and current regression strategy. For encoding-safe editing policy and the current mojibake audit record, also read [docs/development/ENCODING_AND_MOJIBAKE_SAFETY.md](docs/development/ENCODING_AND_MOJIBAKE_SAFETY.md).

## Documentation

The authoritative project documentation now lives under [`docs/`](docs/README.md).

- [Documentation Hub](docs/README.md)
- [Repository Structure](docs/architecture/REPOSITORY_STRUCTURE.md)
- [System Overview](docs/architecture/SYSTEM_OVERVIEW.md)
- [Backend Package Structure](docs/architecture/BACKEND_PACKAGE_STRUCTURE.md)
- [Structure Audit And Migration Plan](docs/architecture/STRUCTURE_AUDIT_AND_MIGRATION_PLAN.md)
- [LLM and Homework Guide](docs/product/LLM_HOMEWORK_GUIDE.md)
- [Development and Testing](docs/development/DEVELOPMENT_AND_TESTING.md)
- [Encoding And Mojibake Safety](docs/development/ENCODING_AND_MOJIBAKE_SAFETY.md)
- [Test Suite Map](docs/development/TEST_SUITE_MAP.md)
- [Deployment and Operations](docs/operations/DEPLOYMENT_AND_OPERATIONS.md)
- [Parent Portal](docs/product/PARENT_PORTAL.md)
- [Git Workflow](docs/development/GIT_WORKFLOW.md)
- [Admin Bootstrap and Demo Seed](docs/operations/ADMIN_BOOTSTRAP.md)

## Production Notes

- Set `APP_ENV=production` and use a strong `SECRET_KEY`.
- Disable public registration unless you explicitly need student self-registration.
- Keep only one grading-worker leader in multi-instance deployments.
- Treat deployment as complete only after the backend, frontends, health checks, and logs all confirm the intended revision is live.

Deployment guidance is consolidated in [docs/operations/DEPLOYMENT_AND_OPERATIONS.md](docs/operations/DEPLOYMENT_AND_OPERATIONS.md).

## License and Attribution

This project is open source under the Apache License 2.0. Copyright 2024 DD-CLASS. You may use, modify, and distribute this repository in compliance with the terms in [LICENSE](LICENSE). The software is provided on an "AS IS" basis, without warranties or conditions of any kind.

Original author and initial contributor: `joyapple`

Subsequent contributors: `HaihuaXie`, `YinzhuCheng`

This repository depends on third-party open source components, including FastAPI, Vue.js, Element Plus, SQLAlchemy, PostgreSQL, and ECharts, each under its own license.

For bug reports, feature requests, or contribution discussions, use [GitHub Issues](https://github.com/joyapple/DD-CLASS/issues).
