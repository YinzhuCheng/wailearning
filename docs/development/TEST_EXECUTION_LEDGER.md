# Test Execution Ledger

## Purpose

This ledger records concrete test executions that are useful for future incremental-test decisions.

It is intentionally more structured than a normal narrative run report. The first audience is an LLM coding agent that needs to answer, quickly and defensibly:

- which test target belongs to which category;
- which command is the canonical command for that target;
- which branch and commit last proved the target green;
- how many recorded runs passed;
- how many total recorded runs exist;
- what each individual run actually did;
- which code paths should trigger retesting.

The ledger does **not** replace `TEST_SUITE_MAP.md`, `TEST_EXECUTION_PITFALLS.md`, or one-off full-suite run reports. Use it as a durable execution index, not as proof that unrelated changes are safe.

## Maintenance Rules

1. **Record only observed executions.** Do not infer pass/fail history from memory, branch names, or the existence of a committed test file. If the command was not actually run and observed, do not add a run row.
2. **Record failures and blocked runs.** A green-only ledger lies. If a command fails, times out, is interrupted, skips unexpectedly, or is blocked by environment setup, add a run row and increment `Run count`. Increment `Pass count` only for `Result: passed`.
3. **Use repository-relative paths only.** Committed ledger content must not include user names, home directories, browser cache directories, database file paths, or other machine-identifying absolute paths. Use placeholders such as `<repo>`, `<repo>/apps/web/admin`, `<python-with-requirements>`, and `<local-browser-cache>`.
4. **Keep local privacy details out of git.** If a run needs machine-specific notes, write them to an ignored file under `.e2e-run/`, usually `.e2e-run/local-private-paths.md`.
5. **Treat PowerShell mojibake as display noise until proven otherwise.** Do not copy terminal-rendered Chinese text from PowerShell output into this file. Prefer ASCII summaries and code identifiers.
6. **Preserve the strict field labels.** Agents should be able to parse sections by `Test ID`, `Category`, `Canonical command`, `Pass count`, `Run count`, and `Runs`.
7. **Update this ledger in the same change set when verification is part of the work.** If a branch fixes a feature and runs target tests before commit, record the final relevant runs before pushing.
8. **Do not use this ledger to avoid all verification.** It helps choose a smaller starting set. It does not make stale test evidence valid after touched code or dependencies change.
9. **Prefer target-level entries over raw command spam.** A test target can have a canonical command and multiple observed commands. If a command variation proves the same invariant, record it under the existing target unless the setup or coverage is materially different.
10. **If a test target is renamed or split, do not silently edit history.** Add a note explaining the new target id, keep old run rows readable, and add a successor pointer.

## Counting Semantics

### `Run count`

Increment `Run count` for any command execution that was started with the intent to validate the target and produced an observable outcome. Observable outcomes include:

- `passed`;
- `failed`;
- `blocked` (for example, sandbox `spawn EPERM`, missing dependency, port collision, browser install missing);
- `timed out`;
- `interrupted`;
- `skipped` when the skip itself is relevant to the target.

Do **not** increment `Run count` for:

- dry-run planning;
- `--list` discovery commands;
- grep/static inspection;
- commands that were typed in notes but not executed.

### `Pass count`

Increment `Pass count` only when the target command completed successfully for the intended scope. Warnings do not prevent a pass, but they should be summarized in the run row when they are persistent or meaningful.

### `Last branch` and `Last commit`

`Last branch` and `Last commit` refer to the most recent recorded run row for the target, not necessarily the latest git commit in the repository. If a command is rerun after a later docs-only commit, update these fields only if that rerun happened.

### `Result` Values

Use one of:

- `passed`
- `failed`
- `blocked`
- `timed out`
- `interrupted`
- `skipped`

If a result needs more detail, keep the field normalized and put detail in `Summary` or `Notes`.

## Test Categories

Use these categories consistently unless a new category is necessary:

- `backend-pytest`: focused backend pytest modules, usually under `tests/backend/`.
- `behavior-pytest`: cross-feature or multi-actor pytest modules under `tests/behavior/`.
- `security-pytest`: authorization and abuse-edge pytest modules under `tests/security/`.
- `postgres-pytest`: PostgreSQL-only pytest modules under `tests/postgres/`.
- `frontend-build`: build/lint/typecheck commands for a frontend package.
- `admin-playwright`: Playwright tests for the admin SPA under `tests/e2e/web-admin/`.
- `parent-playwright`: Playwright tests for the parent portal if added.
- `static-check`: non-runtime checks such as `git diff --check`, compile-only checks, or script validation when they are intentionally part of the verification story.
- `full-suite`: broad full-regression runs that intentionally cover many categories.

## Retest Trigger Guidelines

Every target should list `Retest triggers`. These are not exhaustive, but they help future agents pick a narrow first suite.

Use concrete repository-relative paths and stable symbols. Good examples:

- `apps/backend/wailearning_backend/api/routers/learning_notes.py`
- `apps/backend/wailearning_backend/api/routers/attendance.py`
- `tests/e2e/web-admin/fixtures.cjs`
- `apps/web/admin/playwright.config.cjs`
- `apps/web/admin/src/views/LearningNotes.vue`
- `apps/web/admin/src/router/index.js`

Avoid vague triggers such as "frontend changed" unless the target is genuinely broad.

## Ledger Entries

### Test ID: `backend.learning_notes.api`

**Category:** `backend-pytest`

**Scope:** Focused backend API regressions for learning-note visibility, owner-only mutation, course-bound public notes, all-authenticated public notes without `subject_id`, note-owned copied outline/resources, note discussion metadata, and attendance date-only parsing used by the embedded attendance/calendar workflow.

**Canonical command:**

```powershell
.venv\Scripts\python.exe -m pytest tests\backend\learning_notes\test_learning_notes_api.py -q
```

**Working directory:** `<repo>`

**Relevant paths:**

- `tests/backend/learning_notes/test_learning_notes_api.py`
- `apps/backend/wailearning_backend/api/routers/learning_notes.py`
- `apps/backend/wailearning_backend/api/routers/attendance.py`
- `apps/backend/wailearning_backend/api/schemas.py`
- `apps/backend/wailearning_backend/db/models.py`
- `tests/scenarios/llm_scenario.py`

**Retest triggers:**

- Changes to learning-note CRUD, visibility, copy-from-course, chapter/resource mutation, or discussion routes.
- Changes to `payload.model_fields_set` handling or any schema where explicit `null` should differ from omitted fields.
- Changes to attendance create/list/stat endpoints or date parsing behavior.
- Changes to course access helpers used by learning-note public visibility.
- Changes to DB reset or schema bootstrap behavior that can affect focused backend tests.

**Last branch:** `cursor/discussion-avatar-chat-ui-921d`

**Last commit:** `this commit`

**Last result:** `passed`

**Last run date:** `2026-05-07`

**Pass count:** `2`

**Run count:** `2`

**Runs:**

| Date | Branch | Commit | Command | Result | Summary | Notes |
|------|--------|--------|---------|--------|---------|-------|
| 2026-05-07 | `cursor/discussion-avatar-chat-ui-921d` | `6a95aad` | `.venv\Scripts\python.exe -m pytest tests\backend\learning_notes\test_learning_notes_api.py -q` | `passed` | `11 passed, 68 warnings in 56.83s` | Warnings were existing dependency/framework deprecations and protected-namespace warnings; no assertion failures. |

### Test ID: `frontend.admin.build`

**Category:** `frontend-build`

**Scope:** Production build for the admin SPA package. This catches Vue/Vite import, syntax, bundling, and asset pipeline regressions before browser E2E is interpreted.

**Canonical command:**

```powershell
npm.cmd run build
```

**Working directory:** `<repo>/apps/web/admin`

**Relevant paths:**

- `apps/web/admin/package.json`
- `apps/web/admin/vite.config.js`
- `apps/web/admin/src/`
- `apps/web/admin/playwright.config.cjs`
- `tests/e2e/web-admin/`

**Retest triggers:**

- Changes under `apps/web/admin/src/`.
- Changes to admin frontend dependencies, package scripts, Vite config, or TypeScript/Vue build config.
- Changes to frontend route definitions, shared API clients, or components used by E2E targets.
- Changes that add or remove static assets consumed by the admin SPA.

**Last branch:** `cursor/discussion-avatar-chat-ui-921d`

**Last commit:** `this commit`

**Last result:** `passed`

**Last run date:** `2026-05-08`

**Pass count:** `3`

**Run count:** `3`

**Runs:**

| Date | Branch | Commit | Command | Result | Summary | Notes |
|------|--------|--------|---------|--------|---------|-------|
| 2026-05-07 | `cursor/discussion-avatar-chat-ui-921d` | `6a95aad` | `npm.cmd run build` | `passed` | Vite production build completed successfully. | Output included the known Vite CJS Node API deprecation warning and chunk-size warnings. Treat the warnings as follow-up optimization noise unless they change into build failures. |
| 2026-05-07 | `cursor/discussion-avatar-chat-ui-921d` | `this commit` | `npm.cmd run build` | `passed` | Vite production build completed successfully; `2378 modules transformed`, built in about 20 seconds. | Output again included the known Vite CJS Node API deprecation warning and chunk-size warnings for large bundles. No Vue, JS, CSS, or asset pipeline error was reported. |
| 2026-05-08 | `cursor/discussion-avatar-chat-ui-921d` | `this commit` | `npm.cmd run build` (after `npm.cmd install` in `apps/web/admin`) | `passed` | Admin SPA build succeeded after adjusting the homework table action column and button spacing in `apps/web/admin/src/views/Homework.vue`; the prior failure was an environment precondition issue because `vite` was missing until admin dependencies were installed. | Build was run from `apps/web/admin`. `npm install` added the local package dependencies needed for `vite build`. |

### Test ID: `admin.e2e.learning_notes_attendance_cover_tier20`

**Category:** `admin-playwright`

**Scope:** Targeted admin Playwright tier for newer learning-note, course-cover, and attendance/calendar surfaces. Covers learning-note private/public visibility, public unbound notes visible to authenticated users, course-bound public notes, copied course outline/material snapshots, copied-note editing with explicit `null`, discussion metadata, `page_size` validation, learning-notes UI tabs and default-private dialog, course-card cover visibility, `/teaching-calendar` redirect to embedded attendance, and course/date-scoped attendance filtering.

**Canonical command:**

```powershell
npx.cmd playwright test e2e-learning-notes-attendance-cover-tier20.spec.js --project=chromium
```

**Working directory:** `<repo>/apps/web/admin`

**Relevant paths:**

- `tests/e2e/web-admin/e2e-learning-notes-attendance-cover-tier20.spec.js`
- `tests/e2e/web-admin/fixtures.cjs`
- `tests/e2e/web-admin/future-advanced-coverage-helpers.cjs`
- `apps/web/admin/playwright.config.cjs`
- `apps/web/admin/src/views/LearningNotes.vue`
- `apps/web/admin/src/views/Attendance.vue`
- `apps/web/admin/src/views/MyCourses.vue`
- `apps/web/admin/src/views/StudentCourseHome.vue`
- `apps/web/admin/src/router/index.js`
- `apps/backend/wailearning_backend/api/routers/learning_notes.py`
- `apps/backend/wailearning_backend/api/routers/attendance.py`
- `apps/backend/wailearning_backend/api/routers/e2e_dev.py`

**Retest triggers:**

- Changes to learning notes API routes, schemas, visibility rules, copied chapters/resources, or note discussion behavior.
- Changes to attendance API routes, date parsing, course filtering, or teaching-calendar embedding.
- Changes to course cover upload/display semantics or course-card rendering.
- Changes to `LearningNotes.vue`, `Attendance.vue`, `MyCourses.vue`, `StudentCourseHome.vue`, or shared course-card components.
- Changes to admin SPA routing around `/teaching-calendar`, `/attendance`, `/learning-notes`, or course entry.
- Changes to Playwright global setup, E2E seed/reset helpers, seeded credentials, or API base helpers.

**Last branch:** `cursor/discussion-avatar-chat-ui-921d`

**Last commit:** `6a95aad`

**Last result:** `passed`

**Last run date:** `2026-05-07`

**Pass count:** `2`

**Run count:** `2`

**Runs:**

| Date | Branch | Commit | Command | Result | Summary | Notes |
|------|--------|--------|---------|--------|---------|-------|
| 2026-05-07 | `cursor/discussion-avatar-chat-ui-921d` | `6a95aad` | `npx.cmd playwright test e2e-learning-notes-attendance-cover-tier20.spec.js --project=chromium` | `passed` | `20 passed (1.1m)` | Run used the admin Playwright managed webServer flow from `<repo>/apps/web/admin`. Output included existing backend Pydantic warnings and Vite CJS API deprecation text. |

### Test ID: `admin.e2e.core_flows_smoke`

**Category:** `admin-playwright`

**Scope:** Core admin Playwright smoke for the managed FastAPI + Vite + Chromium path. Covers stable login selectors, invalid login behavior, admin landing, student required-course card and homework list, teacher materials and notifications routes, admin user grid, class-teacher home, and student course-home rendering.

**Canonical command:**

```powershell
npx.cmd playwright test e2e-core-flows-smoke.spec.js --project=chromium
```

**Working directory:** `<repo>/apps/web/admin`

**Relevant paths:**

- `tests/e2e/web-admin/e2e-core-flows-smoke.spec.js`
- `tests/e2e/web-admin/global-setup.cjs`
- `tests/e2e/web-admin/fixtures.cjs`
- `apps/web/admin/playwright.config.cjs`
- `apps/backend/wailearning_backend/api/routers/e2e_dev.py`
- `apps/backend/wailearning_backend/core/auth.py`
- `ops/scripts/dev/playwright_preflight.py`
- `ops/scripts/dev/run_validation_target.py`

**Retest triggers:**

- Changes to Playwright global setup, fixtures, seed/reset helpers, seeded credentials, or API base helpers.
- Changes to `apps/web/admin/playwright.config.cjs`, managed webServer startup, `E2E_PYTHON`, `E2E_DEV_SEED_TOKEN`, or port handling.
- Changes to login, auth token handling, staff/student route guards, or first-load navigation.
- Changes to `ops/scripts/dev/playwright_preflight.py` or runner behavior for `category: admin-playwright` targets.
- Any claim that local Playwright infrastructure has been repaired after environment blockers.

**Last branch:** `cursor/discussion-avatar-chat-ui-921d`

**Last commit:** `this commit`

**Last result:** `passed`

**Last run date:** `2026-05-08`

**Pass count:** `3`

**Run count:** `5`

**Runs:**

| Date | Branch | Commit | Command | Result | Summary | Notes |
|------|--------|--------|---------|--------|---------|-------|
| 2026-05-08 | `cursor/discussion-avatar-chat-ui-921d` | `3ec0dcd` | `npx.cmd playwright test e2e-core-flows-smoke.spec.js --project=chromium` | `blocked` | `Error: spawn EPERM` | Plain sandbox execution could not spawn the managed uvicorn, Vite, and Chromium child processes. The same command needs the approved/elevated execution path in this Windows environment. |
| 2026-05-08 | `cursor/discussion-avatar-chat-ui-921d` | `3ec0dcd` | `npx.cmd playwright test e2e-core-flows-smoke.spec.js --project=chromium` | `failed` | `E2E seed failed (500): Internal Server Error` | Managed uvicorn and Vite started, but `reset-scenario` failed while hashing seeded passwords because the Python 3.14 local `.venv` had `bcrypt==5.0.0`, which is incompatible with `passlib==1.7.4` for the long E2E seed passwords. Restoring `bcrypt==4.0.1` fixed this environment issue. |
| 2026-05-08 | `cursor/discussion-avatar-chat-ui-921d` | `3ec0dcd` | `npx.cmd playwright test e2e-core-flows-smoke.spec.js --project=chromium` | `passed` | `10 passed (51.5s)` | First successful run after populating `.venv` with Python-3.14-compatible backend wheels, restoring `bcrypt==4.0.1`, and deleting the half-initialized Playwright SQLite file from the failed seed attempt. |
| 2026-05-08 | `cursor/discussion-avatar-chat-ui-921d` | `3ec0dcd` | `npx.cmd playwright test e2e-core-flows-smoke.spec.js --project=chromium` | `passed` | `10 passed (46.1s)` | Repeated direct Playwright smoke run through the approved/elevated execution path. Output included the known Vite CJS Node API deprecation warning. |
| 2026-05-08 | `cursor/discussion-avatar-chat-ui-921d` | `3ec0dcd` | `.venv\Scripts\python.exe ops\scripts\dev\run_validation_target.py admin.e2e.core_flows_smoke --timeout-seconds 180` | `passed` | Runner preflight passed, then Playwright smoke reported `10 passed (49.1s)`. | This validated the new runner path: `run_validation_target.py` first ran `playwright_preflight.py --json`, then executed the Playwright target. Artifact paths were written under ignored `.agent-run/logs/` with private paths redacted. |

### Test ID: `static.repo_line_health`

**Category:** `static-check`

**Scope:** Repository-wide text-line health metrics for documentation, tests, primary source, and supporting categories. This is not a behavioral test; it is a tracked metric command that helps future agents notice repository evolution and avoid confusing generated/lockfile growth with application-code growth.

**Canonical command:**

```powershell
python ops\scripts\dev\repo_line_health.py
```

**Working directory:** `<repo>`

**Relevant paths:**

- `ops/scripts/dev/repo_line_health.py`
- `docs/development/DEVELOPMENT_AND_TESTING.md`
- `docs/reference/CODE_MAP_AND_ENTRYPOINTS.md`
- `docs/development/TEST_EXECUTION_LEDGER.md`

**Retest triggers:**

- Changes to `ops/scripts/dev/repo_line_health.py`.
- Changes to repository layout, especially app source roots, test roots, documentation roots, or generated/lockfile placement.
- Changes to `.gitignore` or tracking policy that may alter which files are counted by `git ls-files`.
- Any documentation or process change that uses line counts as a health indicator.

**Last branch:** `cursor/discussion-avatar-chat-ui-921d`

**Last commit:** `this commit`

**Last result:** `passed`

**Last run date:** `2026-05-07`

**Pass count:** `1`

**Run count:** `1`

**Runs:**

| Date | Branch | Commit | Command | Result | Summary | Notes |
|------|--------|--------|---------|--------|---------|-------|
| 2026-05-07 | `cursor/discussion-avatar-chat-ui-921d` | `this commit` | `.venv\Scripts\python.exe ops\scripts\dev\repo_line_health.py` | `passed` | Total tracked text lines: `100981`; health text lines excluding generated/lock files: `97244`; documentation: `12754`; test code: `29161`; primary source: `52260`; tracked text files: `343`. | Command was rerun after staging the new script/docs so `git ls-files` included the intended commit contents. `py_compile` also passed for `ops/scripts/dev/repo_line_health.py`. |
| 2026-05-08 | `cursor/discussion-avatar-chat-ui-921d` | `this commit` | `.venv\Scripts\python.exe ops\scripts\dev\repo_line_health.py` | `passed` | Total tracked text lines: `106756`; health text lines excluding generated/lock files: `103019`; documentation: `14327`; test code: `29601`; primary source: `52375`; tracked text files: `358`. | Command was rerun after updating the validation execution ledger and handoff document for Playwright preflight work. This is a metric target, not behavioral product validation. |

### Test ID: `backend.llm.attachment_formats`

**Category:** `backend-pytest`

**Scope:** Focused backend attachment extraction and classification tests for plain text, Office formats, zip nesting, and RAR fixture handling. The RAR cases exercise committed archives under `tests/fixtures/llm_rar/` and must execute when `unrar`, `unrar-free`, or a compatible libarchive-backed `tar` / `bsdtar` is available.

**Canonical command:**

```powershell
.venv\Scripts\python.exe -m pytest tests\backend\llm\test_llm_attachment_formats.py -q
```

**Working directory:** `<repo>`

**Relevant paths:**

- `tests/backend/llm/test_llm_attachment_formats.py`
- `tests/fixtures/llm_rar/`
- `apps/backend/wailearning_backend/domains/llm/attachments.py`
- `apps/backend/wailearning_backend/attachment_compliance.py`
- `apps/backend/wailearning_backend/llm_grading.py`

**Retest triggers:**

- Changes to attachment classification, extraction, archive walking, or RAR/zip safety checks.
- Changes to upload compliance for `.rar` or `.zip` files.
- Changes to committed RAR fixtures or fixture-generation assumptions.
- Changes to environment provisioning rules for `unrar`, `unrar-free`, `tar`, or `bsdtar`.

**Last branch:** `cursor/discussion-avatar-chat-ui-921d`

**Last commit:** `e7904f4`

**Last result:** `passed`

**Last run date:** `2026-05-07`

**Pass count:** `1`

**Run count:** `1`

**Runs:**

| Date | Branch | Commit | Command | Result | Summary | Notes |
|------|--------|--------|---------|--------|---------|-------|
| 2026-05-07 | `cursor/discussion-avatar-chat-ui-921d` | `e7904f4` | `.venv\Scripts\python.exe -m pytest tests\backend\llm\test_llm_attachment_formats.py -q` | `passed` | `7 passed, 13 warnings in 2.45s` | The host had no `unrar` / `unrar-free`; the RAR tests executed through the compatible `tar` fallback instead of skipping. Warnings were dependency deprecations from import/openpyxl paths. |

### Test ID: `postgres.pytest.package`

**Category:** `postgres-pytest`

**Scope:** PostgreSQL-only pytest package under `tests/postgres/`. This target proves dialect-specific schema, constraint, and transactional behavior that SQLite intentionally cannot cover.

**Canonical command:**

```powershell
$env:TEST_DATABASE_URL='postgresql+psycopg2://wailearning_test:wailearning_test@127.0.0.1:<local-port>/wailearning_pytest_all'
.venv\Scripts\python.exe -m pytest tests\postgres -q
```

**Working directory:** `<repo>`

**Relevant paths:**

- `tests/postgres/`
- `tests/conftest.py`
- `tests/db_reset.py`
- `ops/scripts/dev/provision_postgres_pytest.sh`
- `docs/development/DEVELOPMENT_AND_TESTING.md`
- `docs/development/TEST_EXECUTION_PITFALLS.md`

**Retest triggers:**

- Changes to database models, migrations/repair logic, quota schema, FK constraints, or raw SQL in tests.
- Changes to `tests/db_reset.py`, `tests/conftest.py`, or PostgreSQL provisioning docs/scripts.
- Claims of full-suite or zero-skip pytest validation.

**Last branch:** `cursor/discussion-avatar-chat-ui-921d`

**Last commit:** `4e765a9`

**Last result:** `passed`

**Last run date:** `2026-05-07`

**Pass count:** `1`

**Run count:** `3`

**Runs:**

| Date | Branch | Commit | Command | Result | Summary | Notes |
|------|--------|--------|---------|--------|---------|-------|
| 2026-05-07 | `cursor/discussion-avatar-chat-ui-921d` | `e7904f4` | Single PowerShell orchestrator: start local PostgreSQL binary, create role/db, set `TEST_DATABASE_URL`, run `.venv\Scripts\python.exe -m pytest tests\postgres -q` | `interrupted` | User intentionally interrupted the orchestrated run before a pytest result was observed. | Earlier setup confirmed a local PostgreSQL binary could initialize a throwaway data directory and direct `postgres.exe` could answer `SELECT version()` inside the same command lifecycle. Cross-command background process persistence was unreliable on this Windows sandbox, so the next run should use one orchestrator command/script. Local paths are recorded only in `.e2e-run/`. |
| 2026-05-07 | `cursor/discussion-avatar-chat-ui-921d` | `4e765a9` | Local-only PowerShell orchestrator under `.e2e-run/`: start local PostgreSQL binary using a reused data directory, create role/db, set `TEST_DATABASE_URL`, run `.venv\Scripts\python.exe -m pytest tests\postgres -q` | `blocked` | PostgreSQL exited before readiness while recovering the reused data directory. | Local stderr showed crash recovery followed by `could not signal for checkpoint: Operation not permitted`. This is a Windows local runtime/data-directory recovery issue, not a pytest product result. Real local paths and logs are recorded only under `.e2e-run/`. |
| 2026-05-07 | `cursor/discussion-avatar-chat-ui-921d` | `4e765a9` | Local-only PowerShell orchestrator under `.e2e-run/`: create a fresh throwaway PostgreSQL data directory, start local PostgreSQL binary, create role/db, set `TEST_DATABASE_URL`, run `.venv\Scripts\python.exe -m pytest tests\postgres -q` | `passed` | `42 passed, 59 warnings in 94.79s` | The fresh data-directory path avoided the previous crash-recovery checkpoint failure. `initdb` still printed restricted-token and locale/text-search warnings after pytest output, but PostgreSQL was usable and the pytest package completed green. |

### Test ID: `backend.courses.student_course_roster_behavior`

**Category:** `backend-pytest`

**Scope:** Focused backend course/roster regression file for student account to roster synchronization, required-course enrollment sync, homework submission access, teacher enrollment counts, duplicate student numbers, course removal blocks, sync-enrollments repair, and related class/course invariants.

**Canonical command:**

```powershell
.venv\Scripts\python.exe -m pytest tests\backend\courses\test_student_course_roster_behavior.py -q
```

**Working directory:** `<repo>`

**Relevant paths:**

- `tests/backend/courses/test_student_course_roster_behavior.py`
- `apps/backend/wailearning_backend/domains/courses/access.py`
- `apps/backend/wailearning_backend/domains/roster/reconciliation.py`
- `apps/backend/wailearning_backend/api/routers/auth.py`
- `apps/backend/wailearning_backend/api/routers/homework.py`
- `apps/backend/wailearning_backend/api/routers/subjects.py`

**Retest triggers:**

- Changes to `prepare_student_course_context`, `sync_student_course_enrollments`, `sync_course_enrollments`, or `sync_student_roster_from_user_accounts`.
- Changes to student login behavior, public registration, admin-created student users, or student account to roster synchronization.
- Changes to required-course class linking, course enrollment blocks, roster enroll/sync endpoints, or homework submission authorization.
- Any full PostgreSQL pytest run that reports failures in course/roster tests.

**Last branch:** `cursor/discussion-avatar-chat-ui-921d`

**Last commit:** `this commit`

**Last result:** `passed`

**Last run date:** `2026-05-07`

**Pass count:** `1`

**Run count:** `2`

**Runs:**

| Date | Branch | Commit | Command | Result | Summary | Notes |
|------|--------|--------|---------|--------|---------|-------|
| 2026-05-07 | `cursor/discussion-avatar-chat-ui-921d` | `4e765a9` | PostgreSQL-backed local orchestrator: `.venv\Scripts\python.exe -m pytest tests\backend\courses\test_student_course_roster_behavior.py -q` | `failed` | `3 failed, 11 passed, 57 warnings in 42.83s` | The failures were stale test expectations: three tests still expected student accounts with class ids but missing or mismatched roster rows to remain unable to see/submit required-course work. Current product behavior intentionally repairs a same-class roster row from the student account during login and then syncs required-course enrollment. |
| 2026-05-07 | `cursor/discussion-avatar-chat-ui-921d` | `this commit` | PostgreSQL-backed local orchestrator: `.venv\Scripts\python.exe -m pytest tests\backend\courses\test_student_course_roster_behavior.py -q` | `passed` | `14 passed, 58 warnings in 42.98s` | Tests now assert the current repair contract: same-class student accounts receive or reuse a `Student` roster row and required-course enrollment during login/context preparation. |

### Test ID: `full.pytest.postgres`

**Category:** `full-suite`

**Scope:** Full pytest tree under `tests/` with `TEST_DATABASE_URL` pointing at a throwaway PostgreSQL database. This is the production-aligned backend regression profile for eliminating PostgreSQL-only skips and exercising schema/dialect behavior alongside the default backend and behavior suites.

**Canonical command:**

```powershell
$env:TEST_DATABASE_URL='postgresql+psycopg2://wailearning_test:wailearning_test@127.0.0.1:<local-port>/wailearning_pytest_all'
.venv\Scripts\python.exe -m pytest tests -q
```

**Working directory:** `<repo>`

**Relevant paths:**

- `tests/`
- `tests/conftest.py`
- `tests/db_reset.py`
- `tests/postgres/`
- `docs/development/DEVELOPMENT_AND_TESTING.md`
- `docs/development/TEST_EXECUTION_PITFALLS.md`
- `docs/development/TEST_EXECUTION_LEDGER.md`

**Retest triggers:**

- Claims of full-suite, release-quality, or zero-skip backend validation.
- Changes to database models, schema repair, test reset behavior, PostgreSQL provisioning, LLM quota schema, roster/course sync, homework access, or attachment extraction.
- Any broad backend, behavior, security, or PostgreSQL test change.

**Last branch:** `cursor/discussion-avatar-chat-ui-921d`

**Last commit:** `this commit`

**Last result:** `passed`

**Last run date:** `2026-05-07`

**Pass count:** `1`

**Run count:** `2`

**Runs:**

| Date | Branch | Commit | Command | Result | Summary | Notes |
|------|--------|--------|---------|--------|---------|-------|
| 2026-05-07 | `cursor/discussion-avatar-chat-ui-921d` | `4e765a9` | PostgreSQL-backed local orchestrator: `.venv\Scripts\python.exe -m pytest tests -q` | `timed out` | Command timed out after 20 minutes with progress at about 94% and early `F` markers observed, but no final pytest summary. | Follow-up focused rerun identified the actionable failures in `tests/backend/courses/test_student_course_roster_behavior.py`. Local PostgreSQL logs also showed several expected negative-test constraint errors; those logs alone were not treated as pytest failures. |
| 2026-05-07 | `cursor/discussion-avatar-chat-ui-921d` | `this commit` | PostgreSQL-backed local orchestrator: `.venv\Scripts\python.exe -m pytest tests -q` | `passed` | `487 passed, 1107 warnings in 1285.11s (0:21:25)` | Fresh throwaway PostgreSQL data directory was created under the ignored artifact area. The run completed with zero skipped tests. Warnings were dependency/framework deprecations plus one SQLAlchemy delete-row warning in a concurrent discussion delete regression. |

### Test ID: `static.encoding_text_tools`

**Category:** `static-check`

**Scope:** Static and smoke validation for repository UTF-8 / mojibake-safety helpers. This target proves the helper scripts compile, the PowerShell session helper can execute in quiet mode, safe text display works for documentation, selected tracked files decode as UTF-8, and the current diff has no whitespace errors.

**Canonical command:**

```powershell
.venv\Scripts\python.exe -m py_compile ops\scripts\dev\safe_show_text.py ops\scripts\dev\safe_write_text.py ops\scripts\dev\check_text_encoding.py
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ops\scripts\windows\set-utf8-session.ps1 -Quiet
.venv\Scripts\python.exe ops\scripts\dev\safe_show_text.py docs\development\ENCODING_AND_MOJIBAKE_SAFETY.md --start-line 1 --end-line 12 --escape
'encoding helper smoke' | .venv\Scripts\python.exe ops\scripts\dev\safe_write_text.py .e2e-run\encoding-helper-smoke.txt --stdin --replace --mkdirs
.venv\Scripts\python.exe ops\scripts\dev\check_text_encoding.py ops\scripts\dev\safe_show_text.py ops\scripts\dev\safe_write_text.py ops\scripts\dev\check_text_encoding.py ops\scripts\windows\set-utf8-session.ps1 docs\development\ENCODING_AND_MOJIBAKE_SAFETY.md docs\development\DEVELOPMENT_AND_TESTING.md docs\development\TEST_EXECUTION_PITFALLS.md docs\development\TEST_EXECUTION_LEDGER.md
git diff --check
```

**Working directory:** `<repo>`

**Relevant paths:**

- `ops/scripts/windows/set-utf8-session.ps1`
- `ops/scripts/dev/safe_show_text.py`
- `ops/scripts/dev/safe_write_text.py`
- `ops/scripts/dev/check_text_encoding.py`
- `docs/development/ENCODING_AND_MOJIBAKE_SAFETY.md`
- `docs/development/DEVELOPMENT_AND_TESTING.md`
- `docs/development/TEST_EXECUTION_PITFALLS.md`
- `docs/development/TEST_EXECUTION_LEDGER.md`

**Retest triggers:**

- Changes to any UTF-8 / mojibake helper script under `ops/scripts/dev/` or `ops/scripts/windows/`.
- Changes to encoding-safety documentation, Windows notes, or pitfalls that cite these helpers.
- Changes to text-file classification or suspicious-marker rules in `check_text_encoding.py`.
- Any branch that deliberately repairs suspected mojibake in tracked files.

**Last branch:** `cursor/discussion-avatar-chat-ui-921d`

**Last commit:** `this commit`

**Last result:** `passed`

**Last run date:** `2026-05-07`

**Pass count:** `1`

**Run count:** `1`

**Runs:**

| Date | Branch | Commit | Command | Result | Summary | Notes |
|------|--------|--------|---------|--------|---------|-------|
| 2026-05-07 | `cursor/discussion-avatar-chat-ui-921d` | `this commit` | See canonical command block above. | `passed` | Python helpers compiled; PowerShell UTF-8 helper ran with `-Quiet`; `safe_show_text.py --escape` produced escaped output for the encoding doc; `safe_write_text.py` wrote an ignored `.e2e-run` smoke file; selected files reported `scanned=8 decode_errors=0 suspicious=0`; `git diff --check` passed. | The audit intentionally scanned the newly added helpers and edited docs, not the whole repository. Whole-repo suspicious-marker scans may report historical hotspots and should be interpreted through `ENCODING_AND_MOJIBAKE_SAFETY.md`. |

### Test ID: `static.validation_selector`

**Category:** `static-check`

**Scope:** Static and smoke validation for the first-version diff-based validation target selector. This target proves the selector script compiles, the machine-readable registry is valid JSON, representative path-based recommendations work, the selector can read target-level history from this ledger, and the runners can write ignored structured local history, pytest JUnit result summaries, and profile-level summaries.

The selector is advisory. It does not run pytest, Playwright, PostgreSQL, or frontend build commands by itself, and it does not edit this ledger. It emits a conservative recommendation that an agent must still review against the actual task, changed code, and environment constraints.

**Canonical command:**

```powershell
.venv\Scripts\python.exe -m py_compile ops\scripts\dev\select_validation_targets.py ops\scripts\dev\run_validation_target.py ops\scripts\dev\run_validation_profile.py ops\scripts\dev\validation_history.py tests\backend\manual\test_validation_selector.py
.venv\Scripts\python.exe ops\scripts\dev\select_validation_targets.py --paths apps\backend\wailearning_backend\api\routers\learning_notes.py
.venv\Scripts\python.exe ops\scripts\dev\select_validation_targets.py --paths ops\scripts\dev\select_validation_targets.py tests\TEST_SELECTION_TARGETS.json --json
.venv\Scripts\python.exe ops\scripts\dev\select_validation_targets.py --worktree --json
python -m unittest tests.backend.manual.test_validation_selector -v
python ops\scripts\dev\run_validation_target.py static.validation_selector --dry-run
```

**Working directory:** `<repo>`

**Relevant paths:**

- `ops/scripts/dev/select_validation_targets.py`
- `ops/scripts/dev/run_validation_target.py`
- `ops/scripts/dev/run_validation_profile.py`
- `ops/scripts/dev/validation_history.py`
- `tests/TEST_SELECTION_TARGETS.json`
- `tests/backend/manual/test_validation_selector.py`
- `docs/development/DEVELOPMENT_AND_TESTING.md`
- `docs/development/TEST_SUITE_MAP.md`
- `docs/development/TEST_EXECUTION_LEDGER.md`

**Retest triggers:**

- Changes to the selector script.
- Changes to the machine-readable target registry.
- Changes to the ledger heading or strict field format parsed by the selector.
- Changes to validation-profile documentation or target-selection policy.
- Changes to path matching semantics, fallback rules, or risk-level ordering.
- Changes to structured local history schema, signature calculation, or runner history writing.
- Changes to validation profile policy, risk filtering, or review-target execution defaults.

**Last branch:** `cursor/discussion-avatar-chat-ui-921d`

**Last commit:** `this commit`

**Last result:** `passed`

**Last run date:** `2026-05-08`

**Pass count:** `6`

**Run count:** `6`

**Runs:**

| Date | Branch | Commit | Command | Result | Summary | Notes |
|------|--------|--------|---------|--------|---------|-------|
| 2026-05-08 | `cursor/discussion-avatar-chat-ui-921d` | `this commit` | See canonical command block above. | `passed` | Selector compiled; learning-notes API path recommended `backend.learning_notes.api` and `admin.e2e.learning_notes_attendance_cover_tier20`; selector self/registry paths recommended `static.validation_selector`; `--worktree --json` included untracked selector/registry files; ledger fields were included in Markdown/JSON output for targets that already have ledger IDs. | Initial smoke found three selector-rule issues before this passing row: broad backend fallback fired even when a precise target already matched; Python `fnmatch` pattern `**/*.py` did not match a root-level backend `.py` path; plain `git diff` did not include untracked new files, so `--worktree` now merges `git ls-files --others --exclude-standard` unless `--no-include-untracked` is supplied. A separate line-health check before staging also did not count new files because `repo_line_health.py` intentionally uses `git ls-files`; rerun line health after staging when this distinction matters. |
| 2026-05-08 | `cursor/discussion-avatar-chat-ui-921d` | `this commit` | `python -m py_compile ops\scripts\dev\select_validation_targets.py ops\scripts\dev\run_validation_target.py tests\backend\manual\test_validation_selector.py`; `python -m json.tool tests\TEST_SELECTION_TARGETS.json`; `python -m unittest tests.backend.manual.test_validation_selector -v`; `python ops\scripts\dev\run_validation_target.py static.validation_selector --dry-run` | `passed` | Selector, runner, and selector tests compiled; target registry parsed as valid JSON; `8` standard-library selector/runner tests passed; runner dry-run wrote a redacted local `run.json` and `ledger-snippet.md`. | Current local interpreter lacked `pytest`, so the new selector tests are standard-library `unittest` cases that remain pytest-collectable when pytest is available. A direct `python -m pytest tests\backend\manual\test_validation_selector.py -q` attempt was blocked by missing pytest and was not counted as this target's passing command. Runner dry-run artifacts live under ignored `.agent-run/logs/` and are not committed. |
| 2026-05-08 | `cursor/discussion-avatar-chat-ui-921d` | `this commit` | `python ops\scripts\dev\run_validation_target.py static.validation_selector --timeout-seconds 120` | `passed` | Runner executed all three `static.validation_selector` commands: selector/runner compile passed, selector JSON smoke passed, nested runner dry-run smoke passed. | The runner used the current interpreter because `<repo>/.venv/Scripts/python.exe` was absent in this worktree, and recorded that fallback in ignored local artifacts. The generated `run.json` used `<repo>` and `<python>` placeholders instead of private absolute paths. |
| 2026-05-08 | `cursor/discussion-avatar-chat-ui-921d` | `this commit` | `python -m py_compile ops\scripts\dev\validation_history.py ops\scripts\dev\select_validation_targets.py ops\scripts\dev\run_validation_target.py ops\scripts\dev\run_validation_profile.py tests\backend\manual\test_validation_selector.py`; `python -m json.tool tests\TEST_SELECTION_TARGETS.json`; `python -m unittest tests.backend.manual.test_validation_selector -v` | `passed` | Structured local validation history helper, selector, target runner, profile runner, and selector tests compiled; target registry parsed as valid JSON; `15` standard-library selector/runner/history/profile tests passed. | This run covered JSONL history writing, selector use of matching structured history as fresh evidence, stale classification when the structured history changed-path signature differs from the selector input, pytest JUnit XML argument injection, parsing testcase-level JUnit results, redaction of absolute testcase file paths from JUnit XML, static profile dry-runs, and selector-recommended profile skipping review-required targets by default. Ignored JSONL/XML/profile files under `.agent-run/` are local evidence only and are not committed. |
| 2026-05-08 | `cursor/discussion-avatar-chat-ui-921d` | `this commit` | `python -m py_compile ops\scripts\dev\validation_history.py ops\scripts\dev\select_validation_targets.py ops\scripts\dev\run_validation_target.py ops\scripts\dev\run_validation_profile.py tests\backend\manual\test_validation_selector.py`; `python -m json.tool tests\TEST_SELECTION_TARGETS.json`; `python -m unittest tests.backend.manual.test_validation_selector -v`; `python ops\scripts\dev\run_validation_target.py static.validation_selector --timeout-seconds 120`; `python ops\scripts\dev\run_validation_profile.py static --dry-run --timeout-seconds 120`; `python ops\scripts\dev\select_validation_targets.py --worktree --json`; `git diff --check` | `passed` | Final handoff validation passed after adding the committed validation automation handoff document; `15` unittest cases passed; static target runner passed; static profile dry-run passed; worktree selector returned `non_full_validation.status=acceptable` and `unmatched_paths=[]`; diff whitespace check passed. | Current worktree still had no repository `.venv`, so runner smoke used the current Python interpreter and recorded the fallback in ignored artifacts. Worktree selector considered the new handoff document and validation tooling files and recommended only static targets. |
| 2026-05-08 | `cursor/discussion-avatar-chat-ui-921d` | `this commit` | `.venv\Scripts\python.exe -m py_compile ops\scripts\dev\run_validation_target.py tests\backend\manual\test_validation_selector.py`; `.venv\Scripts\python.exe -m unittest tests.backend.manual.test_validation_selector -v`; `.venv\Scripts\python.exe ops\scripts\dev\run_validation_target.py static.validation_selector --timeout-seconds 120`; `.venv\Scripts\python.exe ops\scripts\dev\select_validation_targets.py --worktree --json`; `git diff --check` | `passed` | Runner and selector tests passed after adding Playwright preflight integration, `spawn EPERM` environment classification, UTF-8 JSON stdout, and focused unittest coverage; `17` unittest cases passed; static target runner passed; selector reported `non_full_validation.status=acceptable` and no unmatched paths; diff whitespace check passed. | The same session separately validated `admin.e2e.core_flows_smoke` through both direct Playwright and `run_validation_target.py`; see that target's ledger entry for the environment blocker and final green runs. |
## Known First-Version Limitations

1. This first ledger version starts with the verified runs around commit `6a95aad`; it intentionally does not backfill older branch history from memory.
2. The ledger is Markdown-first. If agents later need automated pass-rate reports, introduce a generated JSON/YAML companion or a script that parses these strict headings and tables.
3. A single target can hide command variants. When environment-specific command variants become important, add run rows with the actual command and explain whether they count toward the same target.
4. Passing a target here does not mean a future change can skip it. Use `Retest triggers` and touched-file analysis.
5. Browser E2E pass counts are especially environment-sensitive. Read `TEST_EXECUTION_PITFALLS.md` before interpreting a future Playwright failure as product regression.
