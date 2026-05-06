# BIMSA-CLASS

BIMSA-CLASS is a multi-role school and classroom management platform: FastAPI backend, Vue 3 admin SPA, separate parent portal SPA, PostgreSQL in production, LLM-assisted homework grading via an **in-process worker** that drains a **database-backed** task queue (no Redis/Celery broker in this codebase).

## Who this is for

- **Deployers / ops**: production layout under `ops/`, nginx + systemd — start at [`docs/operations/DEPLOYMENT_AND_OPERATIONS.md`](docs/operations/DEPLOYMENT_AND_OPERATIONS.md).
- **Backend / frontend developers**: explicit Python package root `apps.backend.wailearning_backend`, Vue apps under `apps/web/` — start at [`docs/architecture/MAINTAINER_AGENT_GUIDE.md`](docs/architecture/MAINTAINER_AGENT_GUIDE.md).
- **LLM coding agents and automation**: treat [`docs/README.md`](docs/README.md) as the documentation hub; follow the “read before work” list below.

## Read before work

This repository expects contributors, including LLM coding agents, to read task-relevant documentation before changing code. The file tree alone is not the source of truth.

**Minimum rule**

- Before changing repository structure or file placement, read [`docs/architecture/REPOSITORY_STRUCTURE.md`](docs/architecture/REPOSITORY_STRUCTURE.md).
- Before changing backend or product behavior, read [`docs/architecture/SYSTEM_OVERVIEW.md`](docs/architecture/SYSTEM_OVERVIEW.md), [`docs/architecture/CORE_BUSINESS_FLOWS.md`](docs/architecture/CORE_BUSINESS_FLOWS.md), and any feature-specific doc such as [`docs/product/LLM_HOMEWORK_GUIDE.md`](docs/product/LLM_HOMEWORK_GUIDE.md).
- Before running tests or diagnosing failures, read [`docs/development/DEVELOPMENT_AND_TESTING.md`](docs/development/DEVELOPMENT_AND_TESTING.md) and [`docs/development/TEST_EXECUTION_PITFALLS.md`](docs/development/TEST_EXECUTION_PITFALLS.md).
- Before editing multilingual files from Windows + PowerShell, read [`docs/development/ENCODING_AND_MOJIBAKE_SAFETY.md`](docs/development/ENCODING_AND_MOJIBAKE_SAFETY.md).
- When assessing structural risk or full-suite follow-ups inferred from tests, see [`docs/architecture/TEST_INFERRED_RISKS_AND_FOLLOWUPS.md`](docs/architecture/TEST_INFERRED_RISKS_AND_FOLLOWUPS.md).
- Before deployment or service changes, read [`docs/operations/DEPLOYMENT_AND_OPERATIONS.md`](docs/operations/DEPLOYMENT_AND_OPERATIONS.md) and [`docs/operations/ADMIN_BOOTSTRAP.md`](docs/operations/ADMIN_BOOTSTRAP.md).
- Before touching parent-facing flows, read [`docs/product/PARENT_PORTAL.md`](docs/product/PARENT_PORTAL.md).

**Practical expectation**

- If you skip the relevant docs, you are likely to misread compatibility layers, confuse local artifacts for source layout, or waste time on known Windows/PowerShell test traps.
- If you discover a new behavior constraint, environment pitfall, or operational rule while working, update the corresponding document in the same change set.

## Highlights

- Multi-role access for admins, class teachers, subject teachers, students, and parent-code users (parents do not use staff JWT accounts — see parent portal doc).
- Class, student, user, and roster management with reconciliation between user accounts and student roster rows.
- Required and elective course flows, enrollment repair, batch class moves, and enrollment blocking.
- Homework lifecycle with multiple attempts, late-submission rules, score candidates, teacher review, regrade, and student appeals.
- Course material chapters, notifications (with header badge + sync API), attendance, semesters, scores, score-composition appeals, and points.
- Parent portal served as a separate SPA (typically under `/parent/` behind nginx — see deployment doc).
- API-first backend with `pytest` and Playwright E2E coverage (`tests/e2e/web-admin/`).

## LLM-assisted homework grading

The LLM subsystem is core product functionality, not an optional demo.

- Admins manage reusable endpoint presets under `/api/llm-settings`.
- Teachers configure LLM behavior per course (prompts, endpoint order, token boundaries).
- Admins manage global quota policy (timezone, caps, concurrency).
- Async grading uses table-backed `HomeworkGradingTask` rows; the worker runs in-process — see [`docs/product/LLM_HOMEWORK_GUIDE.md`](docs/product/LLM_HOMEWORK_GUIDE.md) and [`docs/architecture/CORE_BUSINESS_FLOWS.md`](docs/architecture/CORE_BUSINESS_FLOWS.md).

## Tech stack

- Backend: FastAPI, SQLAlchemy, PostgreSQL (production reference), Pydantic v2
- Frontend: Vue 3, Vite, Element Plus, Pinia, ECharts
- Parent portal: Vue 3 + Vite (separate app)
- Testing: `pytest`, Playwright (Chromium for admin E2E)
- Deployment: Nginx, `gunicorn`, `uvicorn`, `systemd` (see `ops/`)

## Repository layout

```text
apps/backend/wailearning_backend/   Canonical FastAPI backend package
apps/web/admin/                     Admin SPA and Playwright config
apps/web/parent/                    Parent-facing SPA
docs/                               Documentation hub (start at docs/README.md)
ops/                                CI, nginx, systemd, deployment scripts
tests/                              Backend, behavior, and browser E2E suites
tools/                              Repository maintenance helpers
```

Repository-boundary rules:

- The repository root should contain only repository-level entry files and configuration such as `README.md`, `LICENSE`, `requirements.txt`, `pytest.ini`, and the root `conftest.py`.
- Windows convenience launchers live under `ops/scripts/windows/` instead of being scattered across the root or app folders.
- The backend import namespace is intentionally explicit: `apps.backend.wailearning_backend`. Do not reintroduce a root compatibility package or a second shorter alias.
- Local runtime artifacts such as `frontend/`, `.pytest_tmp/`, `.e2e-run/`, `test-results/`, and `uploads/` are not part of the source layout even if they appear on a developer machine.

See [`docs/architecture/REPOSITORY_STRUCTURE.md`](docs/architecture/REPOSITORY_STRUCTURE.md).

## Quick start

Paths below assume a POSIX shell from the **repository root** (`cd` to this repo first). On Windows, use `ops\scripts\windows\*.bat` where noted.

### Backend

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m uvicorn apps.backend.wailearning_backend.main:app --host 127.0.0.1 --port 8001 --reload
```

Windows convenience launcher:

```bat
ops\scripts\windows\start-backend.bat
```

- Swagger UI: `http://127.0.0.1:8001/docs`
- ReDoc: `http://127.0.0.1:8001/redoc`

Default `DATABASE_URL` in `core/config.py` uses placeholder credentials — override for any shared environment (see [`docs/architecture/CONFIGURATION_REFERENCE.md`](docs/architecture/CONFIGURATION_REFERENCE.md)).

### Admin frontend

```bash
cd apps/web/admin
npm install
npm run dev
```

Windows convenience launcher:

```bat
ops\scripts\windows\start-admin-frontend.bat
```

Default local URL: `http://127.0.0.1:3000` unless `VITE_DEV_PORT` overrides. API proxy target defaults to `http://127.0.0.1:8001` (`VITE_PROXY_TARGET`).

### Parent portal

```bash
cd apps/web/parent
npm install
npm run dev
```

Windows convenience launcher:

```bat
ops\scripts\windows\start-parent-frontend.bat
```

Default local URL: `http://127.0.0.1:5174` unless `VITE_DEV_PORT` overrides.

## Configuration

Authoritative field list and semantics: [`docs/architecture/CONFIGURATION_REFERENCE.md`](docs/architecture/CONFIGURATION_REFERENCE.md) (generated from [`apps/backend/wailearning_backend/core/config.py`](apps/backend/wailearning_backend/core/config.py)).

Commonly touched variables:

| Area | Variables |
|------|-----------|
| Core | `DATABASE_URL`, `SECRET_KEY`, `APP_ENV`, `REQUIRE_STRONG_SECRETS` |
| Bootstrap | `INIT_ADMIN_*`, `INIT_DEFAULT_DATA`, `ALLOW_PUBLIC_REGISTRATION`, `PUBLIC_REGISTRATION_VALIDATE_CLASS_EXISTS` |
| HTTP safety | `BACKEND_CORS_ORIGINS`, `TRUSTED_HOSTS` |
| LLM worker | `ENABLE_LLM_GRADING_WORKER`, `LLM_GRADING_WORKER_LEADER`, `LLM_GRADING_WORKER_POLL_SECONDS`, `LLM_GRADING_TASK_STALE_SECONDS`, `DEFAULT_LLM_API_KEY` |
| Links in notifications | `FRONTEND_ADMIN_BASE_URL` |
| Auth UX hardening | `FORGOT_PASSWORD_USERNAME_COOLDOWN_SECONDS`, `FORGOT_PASSWORD_MAX_REQUESTS_PER_IP_PER_HOUR` |
| E2E only | `E2E_DEV_SEED_ENABLED`, `E2E_DEV_SEED_TOKEN`, `E2E_DEV_REQUIRE_ADMIN_JWT`, `E2E_DEV_ADMIN_USERNAME`, `E2E_DEV_ADMIN_PASSWORD` |

Admin bootstrap and demo seed behavior: [`docs/operations/ADMIN_BOOTSTRAP.md`](docs/operations/ADMIN_BOOTSTRAP.md).

## Testing

Backend:

```bash
python -m pytest
python -m pytest tests/behavior -q
```

Frontend E2E (from admin app):

```bash
cd apps/web/admin
npm install
npx playwright install chromium
npm run test:e2e
```

Managed Playwright defaults use API port **8012** and UI port **3012** — see `apps/web/admin/playwright.config.cjs`. Read [`docs/development/TEST_EXECUTION_PITFALLS.md`](docs/development/TEST_EXECUTION_PITFALLS.md) before treating failures as regressions.

PostgreSQL-aligned validation (production-like DB semantics): see [`docs/development/DEVELOPMENT_AND_TESTING.md`](docs/development/DEVELOPMENT_AND_TESTING.md) and [`docs/development/FULL_PLAYWRIGHT_E2E_RUNBOOK.md`](docs/development/FULL_PLAYWRIGHT_E2E_RUNBOOK.md).

The **`future-advanced-coverage*.spec.js`** files under `tests/e2e/web-admin/` are normal runnable specs; indexing lives in [`docs/development/TEST_SUITE_MAP.md`](docs/development/TEST_SUITE_MAP.md).

## Documentation hub

All detailed documentation: [`docs/README.md`](docs/README.md).

**New / central architecture entries**

- [`docs/architecture/CORE_BUSINESS_FLOWS.md`](docs/architecture/CORE_BUSINESS_FLOWS.md) — submission → queue → worker → UI
- [`docs/architecture/CONFIGURATION_REFERENCE.md`](docs/architecture/CONFIGURATION_REFERENCE.md) — env vars and Vite dev variables
- [`docs/architecture/MAINTAINER_AGENT_GUIDE.md`](docs/architecture/MAINTAINER_AGENT_GUIDE.md) — grep keywords and risky modules
- [`docs/architecture/TROUBLESHOOTING.md`](docs/architecture/TROUBLESHOOTING.md) — symptom-first index

**Existing entry points**

- [`docs/architecture/REPOSITORY_STRUCTURE.md`](docs/architecture/REPOSITORY_STRUCTURE.md)
- [`docs/architecture/SYSTEM_OVERVIEW.md`](docs/architecture/SYSTEM_OVERVIEW.md)
- [`docs/product/LLM_HOMEWORK_GUIDE.md`](docs/product/LLM_HOMEWORK_GUIDE.md)
- [`docs/development/DEVELOPMENT_AND_TESTING.md`](docs/development/DEVELOPMENT_AND_TESTING.md)
- [`docs/operations/DEPLOYMENT_AND_OPERATIONS.md`](docs/operations/DEPLOYMENT_AND_OPERATIONS.md)

## Limitations and honesty

- **Async grading** uses SQL queue rows + in-process worker threads; scaling limits differ from a dedicated worker fleet — see LLM guide.
- **SQLite** (used in some tests / default Playwright DB) is not fully equivalent to PostgreSQL for concurrency and timestamp edge cases.
- **E2E dev API** (`/api/e2e/*`) must never be enabled in production; defense in depth returns 404 when `expose_e2e_dev_api()` is false.
- **Subject vs “course”**: persistence model uses `Subject`; UI copy often says “course”. Code and migrations use `Subject` — grep both when debugging enrollments.

## Production notes

- Set `APP_ENV=production` and use a strong `SECRET_KEY` (and non-placeholder `DATABASE_URL`).
- Disable public registration unless you explicitly need student self-registration.
- Keep only one grading-worker leader in multi-instance deployments (`LLM_GRADING_WORKER_LEADER`).
- Complete deployment only after backend, frontends, health checks, and logs confirm the intended revision.

See [`docs/operations/DEPLOYMENT_AND_OPERATIONS.md`](docs/operations/DEPLOYMENT_AND_OPERATIONS.md).

## License and attribution

This project is open source under the Apache License 2.0. Copyright 2024 DD-CLASS. See [`LICENSE`](LICENSE).

Original author and initial contributor: `joyapple`

Subsequent contributors: `HaihuaXie`, `YinzhuCheng`

Third-party components include FastAPI, Vue.js, Element Plus, SQLAlchemy, PostgreSQL, and ECharts, each under its own license.

Bug reports and discussions: [GitHub Issues](https://github.com/joyapple/DD-CLASS/issues).
