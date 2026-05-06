# Code map and entrypoints

**Purpose:** File-level orientation for agents — **what exists and where**, aligned to the **current tree** (not aspirational architecture).

**Naming:** Product branding uses **BIMSA-CLASS**; legacy strings (`dd-class`, `wailearning`) may appear in ops paths — treat as historical unless migrating.

---

## 1. Repository top level

| Path | Role |
|------|------|
| [`README.md`](../../README.md) | Human + agent entry; quick start; links to `docs/README.md` |
| [`AGENTS.md`](../../AGENTS.md) | Agent handbook (dense pointers) |
| [`requirements.txt`](../../requirements.txt) | Backend Python deps |
| [`pytest.ini`](../../pytest.ini) | `testpaths = tests` |
| [`conftest.py`](../../conftest.py) | Repo-root pytest hooks (Windows temp dir hardening) |
| [`tests/conftest.py`](../../tests/conftest.py) | **Critical:** sets `DATABASE_URL`, disables demo seed during pytest, worker defaults |
| [`ops/`](../../ops/) | nginx, systemd, CI YAML (`ops/ci/*.yml`), deploy shell scripts |
| [`tests/devtools/`](../../tests/devtools/) | Test-tree maintenance scripts (not collected by pytest); start at [`tests/devtools/README.md`](../../tests/devtools/README.md) |
| [`apps/backend/wailearning_backend/`](../../apps/backend/wailearning_backend/) | Canonical FastAPI package |
| [`apps/web/admin/`](../../apps/web/admin/) | Admin SPA + Playwright |
| [`apps/web/parent/`](../../apps/web/parent/) | Parent SPA |

---

## 2. Backend entrypoints

| File | Responsibility |
|------|------------------|
| [`main.py`](../../apps/backend/wailearning_backend/main.py) | FastAPI app; middleware; **router includes**; `/health`; Bing wallpaper helper `/api/bing-background`; lifespan startup |
| [`core/config.py`](../../apps/backend/wailearning_backend/core/config.py) | `pydantic-settings` `Settings`; env parsing; production validators (`expose_e2e_dev_api`) |
| [`core/auth.py`](../../apps/backend/wailearning_backend/core/auth.py) | Password hashing, JWT creation/decoding |
| [`core/permissions.py`](../../apps/backend/wailearning_backend/core/permissions.py) | Role booleans (`is_admin`, `is_teacher`, …) — coarse helpers |
| [`bootstrap.py`](../../apps/backend/wailearning_backend/bootstrap.py) | `ensure_schema_updates()` compatibility DDL; demo LLM preset seed; homework backfills |
| [`db/database.py`](../../apps/backend/wailearning_backend/db/database.py) | `engine`, `SessionLocal`, `Base` declarative |
| [`db/models.py`](../../apps/backend/wailearning_backend/db/models.py) | SQLAlchemy ORM models (large) |
| [`api/schemas.py`](../../apps/backend/wailearning_backend/api/schemas.py) | Pydantic request/response models |
| [`api/routers/*.py`](../../apps/backend/wailearning_backend/api/routers/) | HTTP routers (see §3) |
| [`llm_grading.py`](../../apps/backend/wailearning_backend/llm_grading.py) | Grading orchestration, **in-process worker manager**, effective score aggregation |
| [`llm_discussion.py`](../../apps/backend/wailearning_backend/llm_discussion.py) | Course discussion assistant context assembly |
| [`attachments.py`](../../apps/backend/wailearning_backend/attachments.py) | Upload directory prep; attachment reference checks |
| [`domains/courses/access.py`](../../apps/backend/wailearning_backend/domains/courses/access.py) | Course visibility queries, enrollment sync, `ensure_course_access_http` |
| [`domains/seed/demo.py`](../../apps/backend/wailearning_backend/domains/seed/demo.py) | `seed_demo_course_bundle` — demo teachers/students/courses/homework |
| [`services/logging.py`](../../apps/backend/wailearning_backend/services/logging.py) | `LogService` — persists login and actions to `operation_logs` |

---

## 3. HTTP routers (actual includes in `main.py`)

Routers live under `apps/backend/wailearning_backend/api/routers/`.

| Module | Typical prefix / notes |
|--------|-------------------------|
| `auth.router` | `/api/auth/*` — login, tokens |
| `classes.router` | Class CRUD |
| `students.router` | Student roster + user linkage |
| `scores.router` | Score entries |
| `attendance.router` | Attendance |
| `appearance.router` | User theme / appearance styles |
| `dashboard.router` | Dashboard aggregates |
| `subjects.router` | **Courses** (ORM `Subject`) |
| `users.router` | Staff/student user admin |
| `semesters.router` | Semester catalog |
| `logs.router` | Operation log queries |
| `points.router` | Points |
| `settings.router` | System settings (imported as `system_settings`) |
| `llm_settings.router` | Global LLM presets + quotas |
| `files.router` | Authenticated uploads/downloads |
| `homework.router` | Homework CRUD, submissions, grading tasks, appeals |
| `discussions.router` | Course discussions |
| `material_chapters.router` | Material hierarchy |
| `materials.router` | Materials CRUD |
| `notifications.router` | Notifications + read state |
| `parent.router` | Parent-code authenticated routes |
| `e2e_dev.router` | `/api/e2e/dev/*` — **gated** by `expose_e2e_dev_api()` |

**Exact path strings:** grep `@router.*prefix` inside each file — OpenAPI `/docs` is authoritative for live enumeration.

---

## 4. Frontend — admin SPA

| Path | Role |
|------|------|
| [`apps/web/admin/package.json`](../../apps/web/admin/package.json) | Scripts: `dev`, `build`, `test:e2e` (Playwright) |
| [`apps/web/admin/vite.config.js`](../../apps/web/admin/vite.config.js) | Dev server + proxy |
| [`apps/web/admin/playwright.config.cjs`](../../apps/web/admin/playwright.config.cjs) | E2E ports (`E2E_API_PORT`, `E2E_UI_PORT`) |
| [`apps/web/admin/src/main.js`](../../apps/web/admin/src/main.js) | Vue bootstrap |
| [`apps/web/admin/src/router/index.js`](../../apps/web/admin/src/router/index.js) | Routes + `meta.requiresAdmin` style gates (UI only) |
| [`apps/web/admin/src/api/index.js`](../../apps/web/admin/src/api/index.js) | Axios client, interceptors, validation error formatting |
| [`apps/web/admin/src/stores/user.js`](../../apps/web/admin/src/stores/user.js) | Pinia user session |
| [`apps/web/admin/src/views/TeachingCalendarPage.vue`](../../apps/web/admin/src/views/TeachingCalendarPage.vue) | **教学日历** route (`/teaching-calendar`): wraps `TeachingCalendar.vue` for subject teachers (requires `selected_course`) and `ClassSemesterCalendar.vue` for class teachers; replaced aggregate `Dashboard.vue` (removed). |
| [`apps/web/admin/src/views/*.vue`](../../apps/web/admin/src/views/) | Pages |
| [`apps/web/admin/src/components/*.vue`](../../apps/web/admin/src/components/) | Shared UI (e.g. `MarkdownEditorPanel.vue`, `RichMarkdownDisplay.vue`) |

---

## 5. Frontend — parent SPA

| Path | Role |
|------|------|
| [`apps/web/parent/package.json`](../../apps/web/parent/package.json) | Scripts analogous to admin |
| [`apps/web/parent/src/`](../../apps/web/parent/src/) | Routes + views for parent-code flows |

Detail: [`product/PARENT_PORTAL.md`](../product/PARENT_PORTAL.md).

---

## 6. Tests

| Path | Role |
|------|------|
| [`tests/backend/`](../../tests/backend/) | Primary FastAPI integration/unit clusters |
| [`tests/behavior/`](../../tests/behavior/) | Cross-cutting behavior specs |
| [`tests/e2e/web-admin/`](../../tests/e2e/web-admin/) | Playwright specs (invoked from admin package) |
| [`tests/postgres/`](../../tests/postgres/) | PG-specific tests (conditional skip) |
| [`tests/db_reset.py`](../../tests/db_reset.py) | `reset_test_database_schema()` — `drop_all` + `create_all` |

---

## 7. Deployment / automation

| Path | Role |
|------|------|
| [`ops/ci/pr-pipeline.yml`](../../ops/ci/pr-pipeline.yml) | Reference CI: `python3 -m pytest -q` |
| [`ops/systemd/ddclass-backend.service`](../../ops/systemd/ddclass-backend.service) | systemd unit template |
| [`ops/nginx/wailearning.xyz.conf`](../../ops/nginx/wailearning.xyz.conf) | Example nginx |
| [`ops/scripts/deploy_backend.sh`](../../ops/scripts/deploy_backend.sh) | Deploy helper |

---

## 8. Generated / local artifact dirs (not source)

See [`architecture/REPOSITORY_STRUCTURE.md`](../architecture/REPOSITORY_STRUCTURE.md). Common false positives: `uploads/`, `.pytest_tmp/`, `test-results/`, `dist/`.

---

## 9. Deliberately absent (do not grep forever)

- **No Redis/Celery queue** in-repo for LLM grading — queue is SQL (`homework_grading_tasks`).
- **No `.github/workflows/`** in this snapshot — CI may live entirely in external DevOps (`ops/ci/`).
