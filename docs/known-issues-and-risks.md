# Known issues, risks, and “待人工确认” backlog

This document lists **implementation-backed hazards** and **open questions**. It is **not** a duplicate of all pitfalls in [`development/TEST_EXECUTION_PITFALLS.md`](development/TEST_EXECUTION_PITFALLS.md); that file remains the deep execution encyclopedia. Entries here prioritize **ownership ambiguity** and **agent traps**.

---

## 1. Queue / worker architecture assumptions

| Issue | Detail |
|-------|--------|
| No Celery/Redis grading queue | LLM grading uses SQL rows (`homework_grading_tasks`) + in-process worker (`llm_grading.py`). Agents searching for `celery` or `redis` queue config will find none by design. |

See [`architecture/ASYNC_TASKS_AND_WORKERS.md`](architecture/ASYNC_TASKS_AND_WORKERS.md).

---

## 2. Documentation vs package naming drift

| Issue | Detail |
|-------|--------|
| Legacy npm identifiers | Admin `package.json` may still show historical package names (`courseeval-admin`) while README branding is CourseEval — cosmetic unless publishing packages. |
| External bookmarks to removed `tools/testing/` | Narrative docs may still **mention** the old path when explaining migrations; actionable code/config must not reference it. Canonical utility location: `tests/devtools/audit_test_redundancy.py`. See [architecture/REPOSITORY_RESTRUCTURE_REPORT_2026-05.md](architecture/REPOSITORY_RESTRUCTURE_REPORT_2026-05.md). |

---

## 3. pytest / SQLite harness hazards (observed agent environment)

### 3.1 Persistent SQLite file under `.pytest_tmp/test.sqlite`

**Mechanism:** `tests/conftest.py` sets `DATABASE_URL` to a **repo-local file** when Postgres URL not forced.

**Risk:** Interrupted runs or partially applied DDL can leave the file in a state where later tests fail with missing tables or FK errors until the file is deleted.

**Mitigation documented:** run `python ops/scripts/dev/pytest_sqlite_guard.py`
first, stop any active pytest process it reports, then delete
`<repo-root>/.pytest_tmp/test.sqlite` when bizarre `no such table` errors
appear after supposedly resetting schema. The guardrail is read-only; it does
not kill processes or delete the file.

### 3.2 `ensure_schema_updates()` vs empty/partial metadata — mitigated (2026-05)

**Historical symptom:** `pytest` occasionally failed at `ensure_schema_updates()` with `sqlite3.OperationalError: no such table: course_llm_configs` immediately after `tests.db_reset.reset_test_database_schema()`.

**Root cause:** `reset_test_database_schema()` invoked `Base.metadata.create_all()` before guaranteed ORM mapper registration when test modules imported only `db.database` + `main` without pulling `db.models`.

**Fix:** `tests/db_reset.py` now imports `apps.backend.courseeval_backend.db.models` at the beginning of `reset_test_database_schema()`.

**Residual risks:** corrupted `.pytest_tmp/test.sqlite` files or concurrent pytest processes sharing that path — still require deletion / isolation when suspected.

---

## 4. Demo seed security posture

`INIT_DEFAULT_DATA=true` creates predictable accounts (`teacher`, `teacher_pro`, `stu*`) — **never** enable on production internet-facing installs without rotation policy. Documented in [`operations/ADMIN_BOOTSTRAP.md`](operations/ADMIN_BOOTSTRAP.md).

---

## 5. CI definition location

Reference pipeline YAML lives under [`ops/ci/`](../ops/ci/) (e.g. `pr-pipeline.yml`). A lightweight GitHub Actions workflow now exists at [`.github/workflows/lightweight-validation.yml`](../.github/workflows/lightweight-validation.yml), but it is not a full validation matrix. It covers selector/tooling checks, quick backend `pytest`, and frontend builds. PostgreSQL-backed pytest, RAR-dependent attachment coverage, and Playwright E2E remain local/manual or future cloud-profile work unless a later workflow adds those environments.

---

## 6. Dual enrollment logic

Required courses auto-sync enrollments via `sync_course_enrollments`; electives rely on explicit enrollment rows + optional blocks. Partial demo enrollments for electives are intentional — see demo seed docstrings in `domains/seed/demo.py`.

---

## 7. Effective homework score vs latest attempt body

UI and APIs may show **latest attempt content** while numeric grade reflects **eligible attempt maximum** — easy to mis-diagnose as “wrong score”. See `effective_score_display_zh` and product docs.

---

## 8. Suggested human follow-ups

| Item | Why |
|------|-----|
| Alembic or formal migrations | Current `ensure_schema_updates` pattern works but requires discipline |
| API reference generator | OpenAPI `/docs` exists but no checked-in static export |
| Permission matrix spreadsheet |_roles × routes_ changes frequently |

---

## 9. How to add new entries

Use this template in PR descriptions before promoting to this file:

```text
Title:
Evidence (file/log line):
Impact:
Workaround:
Owner / 待人工确认:
```
