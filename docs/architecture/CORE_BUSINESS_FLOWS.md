# Core Business Flows (Implementation-Aligned)

## Purpose

This document traces **how features actually run** in this repository: HTTP entrypoints, domain helpers, persistence, background processing, and how state appears back in clients. It is written primarily for maintainers and LLM coding agents who need to avoid guessing from folder names alone.

When this document conflicts with marketing language or older notes elsewhere, **trust the cited code paths**.

If you change router signatures, queue semantics, or worker startup, update this file in the same change set.

---

## Conventions

- **Admin SPA**: `apps/web/admin/` — Vue 3 + Element Plus; API calls go through `apps/web/admin/src/api/` helpers (axios) and typically hit `/api/*` via Vite dev proxy (`apps/web/admin/vite.config.js`: `VITE_PROXY_TARGET` defaults to `http://127.0.0.1:8001`).
- **Parent SPA**: `apps/web/parent/` — separate build; dev server defaults to port **5174** (`apps/web/parent/vite.config.js`); same `/api` proxy pattern.
- **Backend**: FastAPI app assembled in `apps/backend/wailearning_backend/main.py`; route modules under `apps/backend/wailearning_backend/api/routers/`; Pydantic contracts in `apps/backend/wailearning_backend/api/schemas.py`.
- **Course access**: Most course-scoped routes call `ensure_course_access` / `ensure_course_access_http` in `apps/backend/wailearning_backend/domains/courses/access.py`. The `_http` variant maps `PermissionError` → **403** and `ValueError` → **404** for consistent API behavior.

---

## 1. Authentication and sessions

### Entry

- `POST /api/auth/login` — `apps/backend/wailearning_backend/api/routers/auth.py`
- JWT dependency — `apps/backend/wailearning_backend/core/auth.py` (`get_current_user`, `get_current_active_user`, optional JWT for E2E gates)

### Behavior (high level)

1. Client sends credentials; router validates user and returns a JWT (`ACCESS_TOKEN_EXPIRE_MINUTES` from settings).
2. Subsequent requests send `Authorization: Bearer <token>`.
3. Role checks use string values stored on `users.role` aligned with `UserRole` enum — `apps/backend/wailearning_backend/db/models.py` (`admin`, `class_teacher`, `teacher`, `student`).

### Related configuration

- `SECRET_KEY`, `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES` — `apps/backend/wailearning_backend/core/config.py`

### Pitfalls

- Forgot-password throttling and registration validation interact with `operation_logs` and optional public registration flags — see [CONFIGURATION_REFERENCE.md](CONFIGURATION_REFERENCE.md).

---

## 2. Course visibility and enrollment

### Entry (examples)

- Subject listing and mutations — `apps/backend/wailearning_backend/api/routers/subjects.py`
- Student elective catalog / enroll / drop — same router (endpoints gated by `UserRole.STUDENT`)
- Class-scoped administration — `apps/backend/wailearning_backend/api/routers/classes.py`, `students.py`, `users.py`

### Domain logic

- **Which courses a user sees** — `get_accessible_courses_query` and related helpers in `domains/courses/access.py`:
  - **Admin**: all subjects.
  - **Student**: subjects linked through `CourseEnrollment` after `prepare_student_course_context` reconciles roster vs account class when applicable.
  - **Teacher**: subjects where `Subject.teacher_id == user.id`.
  - **Class teacher**: union of subjects in `user.class_id` and subjects where the user is the assigned teacher.

### Student roster coupling

- `reconcile_student_users_and_roster` runs during app lifespan — `main.py` — and ties student login identities to `students` rows where `student_no == username` within the same class when those rows exist.

---

## 3. Homework: submission → queue → worker → UI

This is the highest-traffic “vertical slice” for the product.

### 3.1 Student submission (HTTP)

1. **Frontend**: student homework UI calls `POST /api/homeworks/{homework_id}/submission` with body validated by `HomeworkSubmissionCreate` — see `api/schemas.py`.
2. **Router**: `submit_homework` in `api/routers/homework.py`.
3. **Access**: `_ensure_homework_access` / `_resolve_student_for_user` ensure the caller is the roster-linked student for that homework’s class/course.
4. **Persistence**:
   - Upserts `HomeworkSubmission` summary row.
   - Inserts immutable `HomeworkAttempt` for each submission.
5. **Auto grade enqueue**: if `homework.auto_grading_enabled`, calls `queue_grading_task(db, attempt, "new_submission")` — defined in `apps/backend/wailearning_backend/llm_grading.py`.
6. **Summary refresh**: `refresh_submission_summary` updates denormalized fields on `HomeworkSubmission` used by list endpoints.
7. **Commit** and response serialized via `_serialize_submission`.

Code anchor for enqueue:

```1059:1061:apps/backend/wailearning_backend/api/routers/homework.py
    if homework.auto_grading_enabled:
        queue_grading_task(db, attempt, "new_submission")
```

### 3.2 Queue model (database-backed, not Redis)

- New rows in `HomeworkGradingTask` with `status="queued"` — created by `queue_grading_task` — `llm_grading.py`.
- Duplicate protection: if a queued/processing task already exists for the attempt, the existing task is reused and submission summary task fields are aligned.

### 3.3 Worker execution

- **Startup**: `main.py` lifespan calls `start_grading_worker()` when `ENABLE_LLM_GRADING_WORKER` and `LLM_GRADING_WORKER_LEADER` are true — only the leader process should drain in multi-worker `gunicorn`.
- **Implementation**: `llm_grading.py` — polling loop + thread pool for LLM HTTP calls; stale task reclamation controlled by `LLM_GRADING_TASK_STALE_SECONDS`.
- **Outcome**: writes `HomeworkScoreCandidate` rows, updates task status/error fields, records token usage through `domains/llm/quota.py`, and may emit notifications via `domains/homework/notifications.py`.

There is **no separate message broker** (no Redis/Celery) in this codebase; the queue is the `homework_grading_tasks` table.

### 3.4 Teacher / admin views

- Lists and batch actions — still `api/routers/homework.py` (e.g. submissions list, batch regrade).
- Regrade paths enqueue new tasks or reuse queue logic depending on operation — follow call sites of `queue_grading_task` and teacher-triggered helpers in the same module.

### 3.5 Parent portal read path

- Parent-facing aggregated homework/score routes live under `api/routers/parent.py` — they enforce parent-code verification and read student data indirectly; they do not bypass homework access rules for staff routes.

---

## 4. LLM configuration and quotas

### Admin / teacher configuration HTTP

- `api/routers/llm_settings.py` — presets, course LLM config, global quota policy, student overrides.
- Student-facing quota **read** endpoints avoid side effects that mutate course configuration (quota snapshots read from policy + usage tables).

### Domain

- Quota math and recording — `domains/llm/quota.py`, `domains/llm/token_quota.py`.
- Routing between endpoint presets — `domains/llm/routing.py`.

### Persistence (conceptual)

- Described in [../product/LLM_HOMEWORK_GUIDE.md](../product/LLM_HOMEWORK_GUIDE.md) — source of truth for table names and field responsibilities.

---

## 5. Materials and chapters

### HTTP

- Materials and placement — `api/routers/materials.py`
- Hierarchical chapters — `api/routers/material_chapters.py`

### Access

- Instructor checks often use `is_course_instructor` / `ensure_course_access_http` — `domains/courses/access.py`.

---

## 6. Notifications

### HTTP

- CRUD and read-state — `api/routers/notifications.py`
- Lightweight poll snapshot — `GET /api/notifications/sync-status` (same visibility as list query helpers in-router).

### Admin SPA behavior

- Header badge + polling + `BroadcastChannel` — documented in [../development/NOTIFICATION_HEADER_AND_REALTIME_SYNC.md](../development/NOTIFICATION_HEADER_AND_REALTIME_SYNC.md).

---

## 7. Course discussions (homework / materials threads)

### HTTP

- `api/routers/discussions.py` — prefix `/api/discussions`.
- Access uses `ensure_course_access_http` and `is_course_instructor` patterns consistent with other course features.

Discussion LLM jobs (if enabled for a course) are orchestrated through modules referenced from this router and `llm_discussion.py` — **待人工确认**: exact job lifecycle should be verified against `DiscussionLLMJob` usage when changing async discussion behavior.

---

## 8. Appearance presets (user themes)

### HTTP

- `api/routers/appearance.py` — prefix `/api/appearance`.

---

## 9. E2E and mock LLM (non-production only)

### Router registration

- `api/routers/e2e_dev.py` mounted under `/api/e2e` with a **dependency** that returns **404** unless `settings.expose_e2e_dev_api()` is true — see `main.py` comments.
- `expose_e2e_dev_api()` is **false** when `APP_ENV` is production or `E2E_DEV_SEED_ENABLED` is false — `core/config.py`.

### Typical automation flow

1. `POST /api/e2e/dev/reset-scenario` with `X-E2E-Seed-Token` seeds users/courses/homework for Playwright.
2. “Powerful” endpoints (mock LLM, forced grading pump) may require **dual gate**: seed token **plus** admin JWT when `E2E_DEV_REQUIRE_ADMIN_JWT=true` — default in `apps/web/admin/playwright.config.cjs` for managed subprocesses.

Details: [../development/DEVELOPMENT_AND_TESTING.md](../development/DEVELOPMENT_AND_TESTING.md) and [../development/TEST_EXECUTION_PITFALLS.md](../development/TEST_EXECUTION_PITFALLS.md).

---

## 10. Operational logging

### HTTP

- `api/routers/logs.py` — audit / operation logs for administrator views.

---

## Cross-links

- Deployment shape — [../operations/DEPLOYMENT_AND_OPERATIONS.md](../operations/DEPLOYMENT_AND_OPERATIONS.md)
- Full env reference — [CONFIGURATION_REFERENCE.md](CONFIGURATION_REFERENCE.md)
- Test layers and commands — [../development/DEVELOPMENT_AND_TESTING.md](../development/DEVELOPMENT_AND_TESTING.md)
