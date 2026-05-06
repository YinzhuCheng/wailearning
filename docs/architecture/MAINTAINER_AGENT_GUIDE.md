# Maintainer and Agent Guide

## Purpose

Fast orientation for humans and LLM agents editing this repository: **where to change behavior**, **what to grep**, and **what breaks easily**. This is not a substitute for reading feature-specific docs (LLM, parent portal, notifications); it prevents blind edits.

---

## First reads (minimum)

1. [REPOSITORY_STRUCTURE.md](REPOSITORY_STRUCTURE.md) — what is source vs artifact.
2. [SYSTEM_OVERVIEW.md](SYSTEM_OVERVIEW.md) — capabilities and route families.
3. [CORE_BUSINESS_FLOWS.md](CORE_BUSINESS_FLOWS.md) — vertical slices with code anchors.
4. Task-specific: [../product/LLM_HOMEWORK_GUIDE.md](../product/LLM_HOMEWORK_GUIDE.md), [../development/TEST_EXECUTION_PITFALLS.md](../development/TEST_EXECUTION_PITFALLS.md).

---

## Repository map (by concern)

| Concern | Primary locations |
|---------|-------------------|
| HTTP API contracts | `apps/backend/wailearning_backend/api/schemas.py`, `api/routers/*.py` |
| Auth / JWT | `core/auth.py`, `api/routers/auth.py` |
| Permissions / course access | `domains/courses/access.py`, `core/permissions.py` |
| Homework lifecycle | `api/routers/homework.py`, `domains/homework/` |
| LLM grading + queue | `llm_grading.py`, `domains/llm/` |
| DB models | `db/models.py`, `db/database.py` |
| Startup / bootstrap | `main.py`, `bootstrap.py` |
| Admin SPA | `apps/web/admin/src/` (views, `api/index.js`, Pinia stores) |
| Parent SPA | `apps/web/parent/src/` |
| Playwright E2E | `tests/e2e/web-admin/`, `apps/web/admin/playwright.config.cjs` |
| Backend tests | `tests/backend/`, `tests/behavior/` |

---

## High-risk edit zones

1. **`llm_grading.py`** — Large orchestration surface: quota, retries, attachment extraction, task lifecycle. Errors surface as flaky grading, stuck tasks, or token accounting drift.
2. **`domains/courses/access.py`** — Central authorization for course visibility; changing filters affects every enrollment and teacher view.
3. **`bootstrap.py` / `main.py` lifespan** — Ordering matters: schema repair before seeds, roster reconciliation after demo data.
4. **`api/routers/e2e_dev.py`** — Security-sensitive; dual-gate auth for powerful endpoints; never assume production mounts (still 404 when `expose_e2e_dev_api()` is false).
5. **SQLite vs PostgreSQL** — Tests and Playwright often use SQLite with different edge semantics; concurrency tests may be PostgreSQL-only.

---

## grep-friendly keywords

Use these when locating behavior:

- Course access: `ensure_course_access`, `ensure_course_access_http`, `get_accessible_courses_query`
- Teacher checks: `is_teacher`, `is_course_instructor`, `UserRole.CLASS_TEACHER`
- Grading queue: `queue_grading_task`, `HomeworkGradingTask`, `process_next_grading_task`
- Quota: `precheck_quota`, `reserve_quota_tokens`, `get_student_quota_usage_snapshot`
- Notifications sync: `sync-status`, `syncStatus`, `notificationSync`
- E2E seed: `reset-scenario`, `E2E_DEV_SEED`, `expose_e2e_dev_api`

---

## Testing expectations

- **pytest**: run from repo root; database selection documented in [../development/DEVELOPMENT_AND_TESTING.md](../development/DEVELOPMENT_AND_TESTING.md).
- **Playwright**: prefer `cd apps/web/admin && npm run test:e2e`; env contract in `playwright.config.cjs`. Failures often environmental — see [../development/TEST_EXECUTION_PITFALLS.md](../development/TEST_EXECUTION_PITFALLS.md).

---

## Documentation maintenance rule

If you change:

- a **default port**, env var, or startup gate → update [CONFIGURATION_REFERENCE.md](CONFIGURATION_REFERENCE.md) and the root [README.md](../../README.md) quick start if user-visible.
- a **route prefix** or major flow → update [SYSTEM_OVERVIEW.md](SYSTEM_OVERVIEW.md) and [CORE_BUSINESS_FLOWS.md](CORE_BUSINESS_FLOWS.md).
- **E2E harness** behavior → update [../development/DEVELOPMENT_AND_TESTING.md](../development/DEVELOPMENT_AND_TESTING.md) and pitfalls.

---

## Historical / naming honesty

- Package directory historically referenced as “wailearning” / “dd-class” in ops paths — deployment docs preserve server paths; code namespace is `apps.backend.wailearning_backend`.
- “Subject” in models often corresponds to user-facing “course” in UI copy — when debugging enrollment, grep both `Subject` and route `/api/subjects`.
