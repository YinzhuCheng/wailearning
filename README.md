# BIMSA-CLASS

BIMSA-CLASS is a school and classroom management platform built with FastAPI, Vue 3, PostgreSQL, and a separate parent portal. It combines day-to-day academic administration with course-level LLM-assisted homework grading, async grading queues, quota controls, and attachment-aware submission processing.

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
apps/backend/app/   FastAPI backend package
apps/web/admin/     Admin SPA and Playwright config
apps/web/parent/    Parent-facing SPA
docs/               Documentation hub organized by topic
ops/                CI, nginx, systemd, and deployment scripts
tests/              Backend, behavior, and browser E2E suites
```

## Quick Start

### Backend

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
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

Default local frontend URL: `http://127.0.0.1:5173` or the Vite port shown in the terminal.

### Parent Portal

```bash
cd apps/web/parent
npm install
npm run dev
```

## Core Environment Variables

Key backend settings are defined in [`apps/backend/app/config.py`](apps/backend/app/config.py).

- `DATABASE_URL`
- `SECRET_KEY`
- `APP_ENV`
- `INIT_ADMIN_USERNAME`
- `INIT_ADMIN_PASSWORD`
- `INIT_DEFAULT_DATA`
- `ALLOW_PUBLIC_REGISTRATION`
- `ENABLE_LLM_GRADING_WORKER`
- `LLM_GRADING_WORKER_LEADER`
- `LLM_GRADING_TASK_STALE_SECONDS`
- `E2E_DEV_SEED_ENABLED`
- `E2E_DEV_SEED_TOKEN`

Admin bootstrap and demo seed behavior are documented in [docs/operations/ADMIN_BOOTSTRAP.md](docs/operations/ADMIN_BOOTSTRAP.md).

## Testing

Backend:

```bash
python -m pytest
python -m pytest tests/behavior -q
```

Frontend E2E:

```bash
cd apps/web/admin
npm install
npx playwright install chromium
npm run test:e2e
```

See [docs/development/DEVELOPMENT_AND_TESTING.md](docs/development/DEVELOPMENT_AND_TESTING.md) for the full local workflow, Windows notes, and current regression strategy.

## Documentation

The authoritative project documentation now lives under [`docs/`](docs/README.md).

- [Documentation Hub](docs/README.md)
- [System Overview](docs/architecture/SYSTEM_OVERVIEW.md)
- [LLM and Homework Guide](docs/product/LLM_HOMEWORK_GUIDE.md)
- [Development and Testing](docs/development/DEVELOPMENT_AND_TESTING.md)
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
