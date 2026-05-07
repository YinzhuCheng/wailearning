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

**Last commit:** `6a95aad`

**Last result:** `passed`

**Last run date:** `2026-05-07`

**Pass count:** `1`

**Run count:** `1`

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

**Last commit:** `6a95aad`

**Last result:** `passed`

**Last run date:** `2026-05-07`

**Pass count:** `1`

**Run count:** `1`

**Runs:**

| Date | Branch | Commit | Command | Result | Summary | Notes |
|------|--------|--------|---------|--------|---------|-------|
| 2026-05-07 | `cursor/discussion-avatar-chat-ui-921d` | `6a95aad` | `npm.cmd run build` | `passed` | Vite production build completed successfully. | Output included the known Vite CJS Node API deprecation warning and chunk-size warnings. Treat the warnings as follow-up optimization noise unless they change into build failures. |

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

**Pass count:** `1`

**Run count:** `1`

**Runs:**

| Date | Branch | Commit | Command | Result | Summary | Notes |
|------|--------|--------|---------|--------|---------|-------|
| 2026-05-07 | `cursor/discussion-avatar-chat-ui-921d` | `6a95aad` | `npx.cmd playwright test e2e-learning-notes-attendance-cover-tier20.spec.js --project=chromium` | `passed` | `20 passed (1.1m)` | Run used the admin Playwright managed webServer flow from `<repo>/apps/web/admin`. Output included existing backend Pydantic warnings and Vite CJS API deprecation text. |

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

## Known First-Version Limitations

1. This first ledger version starts with the verified runs around commit `6a95aad`; it intentionally does not backfill older branch history from memory.
2. The ledger is Markdown-first. If agents later need automated pass-rate reports, introduce a generated JSON/YAML companion or a script that parses these strict headings and tables.
3. A single target can hide command variants. When environment-specific command variants become important, add run rows with the actual command and explain whether they count toward the same target.
4. Passing a target here does not mean a future change can skip it. Use `Retest triggers` and touched-file analysis.
5. Browser E2E pass counts are especially environment-sensitive. Read `TEST_EXECUTION_PITFALLS.md` before interpreting a future Playwright failure as product regression.
