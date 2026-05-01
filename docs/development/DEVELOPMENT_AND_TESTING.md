# Development and Testing

## Local Development Setup

### Backend

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
```

### Admin frontend

```bash
cd apps/web/admin
npm install
npm run dev
```

### Parent portal

```bash
cd apps/web/parent
npm install
npm run dev
```

## Key Development Settings

Defined in [`../../apps/backend/app/config.py`](../../apps/backend/app/config.py):

- `APP_ENV`
- `DEBUG`
- `DATABASE_URL`
- `SECRET_KEY`
- `ALLOW_PUBLIC_REGISTRATION`
- `INIT_DEFAULT_DATA`
- `E2E_DEV_SEED_ENABLED`
- `E2E_DEV_SEED_TOKEN`
- `ENABLE_LLM_GRADING_WORKER`
- `LLM_GRADING_WORKER_LEADER`

## Test Layers

### Backend `pytest`

Use backend tests for API logic, permission checks, grading behavior, and state-convergence rules.

```bash
python -m pytest
python -m pytest tests/behavior -q
```

Important directories:

- `tests/`
- `tests/behavior/`

### Frontend Playwright E2E

Use browser tests for login flows, stale-tab behavior, deep links, and UI-to-backend convergence.

```bash
cd apps/web/admin
npx playwright install chromium
npm run test:e2e
```

Key files:

- `apps/web/admin/playwright.config.cjs`
- `tests/e2e/web-admin/`
- `docs/development/TEST_EXECUTION_PITFALLS.md`

## E2E Seed and Environment

The repository includes an E2E-only reset API used by browser tests.

- Route family: `/api/e2e/...`
- Guarded by `E2E_DEV_SEED_ENABLED` and `E2E_DEV_SEED_TOKEN`
- Never enable this in production

Playwright scenarios commonly use:

- `POST /api/e2e/dev/reset-scenario`
- a local API URL,
- a local frontend base URL,
- a local Playwright browser cache path on Windows.

## Windows Notes

This repository is actively used on Windows, so path and encoding discipline matters.

- Prefer running `pytest` from the repository root.
- Prefer the repository virtual environment instead of a global Python.
- Keep documentation and scripted edits ASCII-first when possible.
- Avoid shell-side bulk rewriting of Chinese strings.
- For Playwright, explicitly set `PLAYWRIGHT_BROWSERS_PATH` when using a local browser cache.

Example command pattern for targeted Playwright runs:

```powershell
$env:PLAYWRIGHT_BROWSERS_PATH='C:\Users\<user>\AppData\Local\ms-playwright'
$env:E2E_API_URL='http://127.0.0.1:8012'
$env:PLAYWRIGHT_BASE_URL='http://127.0.0.1:3012'
$env:E2E_DEV_SEED_TOKEN='test-playwright-seed'
npm run test:e2e
```

## Current High-Value Regression Areas

These are the areas most worth testing when behavior changes:

- startup-time idempotency and backfill behavior,
- roster and class-move synchronization,
- required versus elective enrollment rules,
- homework submission history and max-submission limits,
- LLM routing, quota, retry, and regrade recovery,
- notification read-state convergence,
- grade and homework appeal deduplication,
- deep-link recovery when local course context is stale or missing.

## Complex Regression Coverage Added In This Repository

Recent behavior coverage includes scenarios such as:

- score-appeal reopen after resolve or reject,
- concurrent duplicate appeal submission settling to one pending row,
- targeted-student notification privacy,
- subject-scoped mark-all-read behavior,
- concurrent notification read-state convergence,
- batch class flip-flop preserving one required enrollment,
- batch import retry idempotency,
- quota exhaustion followed by recovery,
- disable-then-reenable LLM grading flows.

## Practical Testing Rules

- Assert authoritative business state before asserting visual transitions.
- Prefer stable identifiers and API-level validation over UI copy.
- Run the narrow failing test first, then the relevant suite, then the broader suite.
- Separate product bugs from environment mistakes such as working-directory or temp-path issues.
- If running on Windows + PowerShell, review `TEST_EXECUTION_PITFALLS.md` before assuming Playwright or pytest failures are product regressions.

## After Documentation Updates

For documentation-only work, full test runs are not always necessary. For changes that also touch behavior, prefer:

```bash
python -m pytest tests/behavior -q
```

and then any targeted Playwright spec that covers the affected workflow.
