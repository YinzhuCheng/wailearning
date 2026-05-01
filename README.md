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

See [docs/LLM_HOMEWORK_GUIDE.md](docs/LLM_HOMEWORK_GUIDE.md) for the current implementation details.

## Tech Stack

- Backend: FastAPI, SQLAlchemy, PostgreSQL, Pydantic v2
- Frontend: Vue 3, Vite, Element Plus, Pinia, ECharts
- Parent portal: separate Vue 3 + Vite application
- Testing: `pytest`, Playwright
- Deployment: Nginx, `gunicorn`, `uvicorn`, `systemd`

## Repository Layout

```text
app/             FastAPI backend, models, routers, grading worker, bootstrap logic
frontend/        Admin SPA and Playwright E2E tests
parent-portal/   Parent-facing SPA
scripts/         Deployment, bootstrap, password reset, and git helper scripts
docs/            Project documentation hub
tests/           Backend and behavior test suites
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
cd frontend
npm install
npm run dev
```

Default local frontend URL: `http://127.0.0.1:5173` or the Vite port shown in the terminal.

### Parent Portal

```bash
cd parent-portal
npm install
npm run dev
```

## Core Environment Variables

Key backend settings are defined in [`app/config.py`](app/config.py).

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

Admin bootstrap and demo seed behavior are documented in [docs/ADMIN_BOOTSTRAP.md](docs/ADMIN_BOOTSTRAP.md).

## Testing

Backend:

```bash
python -m pytest
python -m pytest tests/behavior -q
```

Frontend E2E:

```bash
cd frontend
npm install
npx playwright install chromium
npm run test:e2e
```

See [docs/DEVELOPMENT_AND_TESTING.md](docs/DEVELOPMENT_AND_TESTING.md) for the full local workflow, Windows notes, and current regression strategy.

## Documentation

The authoritative project documentation now lives under [`docs/`](docs/README.md).

- [Documentation Hub](docs/README.md)
- [System Overview](docs/SYSTEM_OVERVIEW.md)
- [LLM and Homework Guide](docs/LLM_HOMEWORK_GUIDE.md)
- [Development and Testing](docs/DEVELOPMENT_AND_TESTING.md)
- [Deployment and Operations](docs/DEPLOYMENT_AND_OPERATIONS.md)
- [Parent Portal](docs/PARENT_PORTAL.md)
- [Git Workflow](docs/GIT_WORKFLOW.md)
- [Admin Bootstrap and Demo Seed](docs/ADMIN_BOOTSTRAP.md)

## Production Notes

- Set `APP_ENV=production` and use a strong `SECRET_KEY`.
- Disable public registration unless you explicitly need student self-registration.
- Keep only one grading-worker leader in multi-instance deployments.
- Treat deployment as complete only after the backend, frontends, health checks, and logs all confirm the intended revision is live.

Deployment guidance is consolidated in [docs/DEPLOYMENT_AND_OPERATIONS.md](docs/DEPLOYMENT_AND_OPERATIONS.md).
