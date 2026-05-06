# Agent playbook — safe edits, tracing, and verification

**Audience:** LLM coding agents and maintainers who need procedural discipline, not only folder listings.

**Companion docs:** [`AGENTS.md`](../AGENTS.md) (repo root), [`docs/README.md`](README.md) (hub), [`docs/reference/CODE_MAP_AND_ENTRYPOINTS.md`](reference/CODE_MAP_AND_ENTRYPOINTS.md).

---

## 1. How to read this repository (order matters)

1. **Boundary:** [`architecture/REPOSITORY_STRUCTURE.md`](architecture/REPOSITORY_STRUCTURE.md) — distinguishes git-tracked source from runtime dirs (`uploads/`, `.pytest_tmp/`, etc.).
2. **Capabilities:** [`architecture/SYSTEM_OVERVIEW.md`](architecture/SYSTEM_OVERVIEW.md) — roles and route families (not every endpoint).
3. **Slices:** [`architecture/CORE_BUSINESS_FLOWS.md`](architecture/CORE_BUSINESS_FLOWS.md) — homework + LLM + notifications vertical traces with code anchors.
4. **Config:** [`architecture/CONFIGURATION_REFERENCE.md`](architecture/CONFIGURATION_REFERENCE.md) — every `Settings` field and major `VITE_*` vars.
5. **Tests:** [`development/DEVELOPMENT_AND_TESTING.md`](development/DEVELOPMENT_AND_TESTING.md) + [`development/TEST_EXECUTION_PITFALLS.md`](development/TEST_EXECUTION_PITFALLS.md).

Skipping step 1 causes agents to “fix” generated artifacts or propose forbidden package layouts.

---

## 2. Standard workflow for a feature touch

### 2.1 Locate the slice

| If the task mentions… | Start reading… |
|----------------------|----------------|
| HTTP shape / validation | `apps/backend/wailearning_backend/api/schemas.py` + relevant `api/routers/*.py` |
| Who can call an API | Router dependency (`get_current_user`) + `domains/courses/access.py` + `core/permissions.py` |
| Persistence | `db/models.py` + `bootstrap.py` (`ensure_schema_updates` if new columns) |
| Homework scoring display | `llm_grading.py` (`resolve_effective_submission_score`, `refresh_submission_summary`) + `api/routers/homework.py` serializers |
| LLM vendor calls | `domains/llm/` + `llm_grading.py` task processor |
| Admin UI | `apps/web/admin/src/views/*.vue` + `apps/web/admin/src/api/index.js` |
| Parent UI | `apps/web/parent/src/` |

### 2.2 Trace forward from UI click (homework example)

1. Vue view calls API helper in `apps/web/admin/src/api/index.js` (axios instance `baseURL` = `/api` or `VITE_API_BASE_URL`).
2. FastAPI router under `apps/backend/wailearning_backend/api/routers/homework.py`.
3. Dependencies: DB session + current user; `ensure_course_access_http` or equivalent when course-scoped.
4. Services / domains: homework domain modules under `domains/homework/` (when logic extracted from router).
5. Tables: `homeworks`, `homework_submissions`, `homework_attempts`, `homework_score_candidates`, `homework_grading_tasks` — see [`reference/DATA_MODEL_ESSENTIALS.md`](reference/DATA_MODEL_ESSENTIALS.md).
6. Async: new attempt may enqueue `HomeworkGradingTask`; worker thread drains queue — [`architecture/ASYNC_TASKS_AND_WORKERS.md`](architecture/ASYNC_TASKS_AND_WORKERS.md).

### 2.3 Trace backward from DB symptom

1. Identify ORM model (`db/models.py`).
2. Find writes in routers/domains (grep model class name).
3. Check bootstrap defaults / demo seed (`domains/seed/demo.py`, `INIT_DEFAULT_DATA`).
4. Check tests mirroring feature (`tests/backend/**`).

---

## 3. Backend bootstrap ordering (do not reorder blindly)

**Source:** `apps/backend/wailearning_backend/main.py` `lifespan`.

Approximate sequence:

1. `Base.metadata.create_all(bind=engine)`
2. `ensure_schema_updates()` — additive migrations / compatibility DDL (`bootstrap.py`)
3. Normalization passes (`normalize_teacher_class_assignments`, semester catalog, subject-semester links)
4. `backfill_homework_grading_data(db)`
5. `reconcile_student_users_and_roster(db)`
6. Optional `seed_demo_course_bundle(db)` when `INIT_DEFAULT_DATA=true`, then roster reconcile again
7. After yield startup: optional `start_grading_worker()` when `ENABLE_LLM_GRADING_WORKER` and `LLM_GRADING_WORKER_LEADER`

**Agent implication:** schema repair functions must tolerate empty databases **and** legacy partially migrated databases. New helpers appended to `ensure_schema_updates()` should stay idempotent.

---

## 4. Testing playbook

### 4.1 Commands (verify locally after edits)

| Scope | Command |
|-------|---------|
| Single file | `python3 -m pytest path/to/test_file.py -q` |
| Backend subset | `python3 -m pytest tests/backend -q` |
| CI parity | `python3 -m pytest -q` (see [`ops/ci/pr-pipeline.yml`](../ops/ci/pr-pipeline.yml)) |

**Interpreter:** Linux/macOS automation often lacks `python` on PATH; prefer **`python3`** (CI uses `python3` explicitly).

### 4.2 Environment variables tests rely on

**Source:** `tests/conftest.py` (loaded automatically).

- Sets `DATABASE_URL` to `TEST_DATABASE_URL` **or** auto-selected Postgres when `WAILEARNING_AUTO_PG_TESTS` matches **or** fallback SQLite file `<repo>/.pytest_tmp/test.sqlite`.
- Forces `INIT_DEFAULT_DATA=false` during tests.
- Disables LLM worker by default (`TEST_ENABLE_LLM_GRADING_WORKER` overrides).

### 4.3 Playwright admin E2E

```bash
cd apps/web/admin
npm install
npm run test:e2e
```

Contract: [`development/FULL_PLAYWRIGHT_E2E_RUNBOOK.md`](development/FULL_PLAYWRIGHT_E2E_RUNBOOK.md).

---

## 5. Documentation maintenance triggers

Update docs **in the same change set** when you:

| Change type | Docs |
|-------------|------|
| New/changed env var | `architecture/CONFIGURATION_REFERENCE.md`, possibly root `README.md` quick start |
| Router prefix / major flow | `architecture/SYSTEM_OVERVIEW.md`, `architecture/CORE_BUSINESS_FLOWS.md` |
| Demo seed behavior | `operations/ADMIN_BOOTSTRAP.md`, `product/LLM_HOMEWORK_GUIDE.md` demo sections |
| Test harness / pitfalls | `development/DEVELOPMENT_AND_TESTING.md`, `development/TEST_EXECUTION_PITFALLS.md` |
| Known regressions / unclear ownership | `known-issues-and-risks.md` |

---

## 6. When to stop and ask for human decision

Document as **“待人工确认”** in [`known-issues-and-risks.md`](known-issues-and-risks.md) when:

- Two implementations coexist and call sites disagree which is primary.
- External vendor behavior or deployment secrets are required to validate.
- Legal/compliance implications (PII logging, retention).

Agents must not invent certainty.

---

## 7. Anti-patterns (repeat offenders)

1. **Adding “shortcut” imports** that bypass `apps.backend.wailearning_backend` namespace.
2. **Changing demo seed** without updating `tests/backend/e2e_dev/test_demo_course_seed.py` expectations.
3. **Editing only admin UI** for permission-sensitive actions — backend must reject unauthorized API calls.
4. **Assuming Redis/Celery** — LLM grading uses DB-backed tasks + in-process worker (`llm_grading.py`).
5. **Running destructive grep-replace** on Chinese copy without encoding hygiene (Windows).

---

## 8. Related operational docs

- Deploy layout: [`operations/DEPLOYMENT_AND_OPERATIONS.md`](operations/DEPLOYMENT_AND_OPERATIONS.md)
- Bootstrap / admin seed: [`operations/ADMIN_BOOTSTRAP.md`](operations/ADMIN_BOOTSTRAP.md)
- Symptom index: [`architecture/TROUBLESHOOTING.md`](architecture/TROUBLESHOOTING.md)
