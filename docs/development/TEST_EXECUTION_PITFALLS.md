# Test Execution Pitfalls

## Purpose

This document records pitfalls encountered while executing the repository test suites on Windows + PowerShell during the repository-structure refactor completed on May 1, 2026. The focus here is the tester environment, test runner behavior, and execution workflow friction, not product-code bugs.

Later passes (same overall repository layout) added Linux / CI / cloud-agent notes and Playwright selector pitfalls discovered while fixing false failures. Those additions are additive: they do not replace the Windows-focused guidance above.

This file is meant to save future test operators from rediscovering the same issues.

For the repository-wide policy on Unicode-safe editing and for the current mojibake hotspot audit, also read:

- [ENCODING_AND_MOJIBAKE_SAFETY.md](ENCODING_AND_MOJIBAKE_SAFETY.md)

## Read This Before Running Tests

If you are about to run tests, especially as an LLM coding agent on Windows + PowerShell, check these first:

1. Use the repository `.venv`, not a global Python.
2. Treat `npm.ps1` as suspect; prefer `npm.cmd` or `npx.cmd` when PowerShell policy is restrictive.
3. Assume stale backend or frontend processes may still own your intended ports.
4. Do not trust "a port responds" as proof that the correct app is serving.
5. For Playwright, prefer isolated ports and explicit external-server startup when a run matters.
6. If pytest fails before test bodies execute, inspect temp-path behavior before blaming product code.
7. Do not copy Chinese text from PowerShell output back into tracked files.
8. On Linux or in CI, if Playwright starts the API via `webServer`, confirm the command uses the repository `.venv` interpreter (or `E2E_PYTHON`), not a bare `python3` without project dependencies (see Pitfall 11).

If you skip this checklist, you may spend time debugging the shell, temp directories, old background processes, or port collisions instead of the repository itself.

## Scope of the Recorded Session

- Host shell: Windows PowerShell
- Repository root: `C:\Users\bloom\wailearning-e2e-boundary-dynamic-complex-d8c7`
- Python runtime: repository `.venv`
- Frontend package runner: `npm.cmd` / `npx.cmd`
- Browser cache path: `C:\Users\bloom\AppData\Local\ms-playwright`
- Tested after repository structure migration into:
  - `apps/backend/wailearning_backend/`
  - `apps/web/admin/`
  - `apps/web/parent/`
  - `ops/`
  - `tests/e2e/web-admin/`

### Additional session (Linux / cloud agent, May 2026)

This session used Linux bash, the repository `.venv` for pytest, system-packaged Node/npm where needed, and Playwright driven from `apps/web/admin` (`npm run test:e2e`). Pitfalls 11–16 below come from that pass. They complement, rather than contradict, the Windows-focused items.

## Pitfall 1: PowerShell output can display mojibake

### Symptom

Chinese output shown in the terminal may render as mojibake even when the underlying file content is correct.

### Why it matters

- Terminal copy-paste is not trustworthy for Chinese strings.
- Batch files, YAML comments, and legacy script files are especially easy to corrupt if edited by copying text from PowerShell output.

### Safe handling strategy

- Do not copy Chinese text from terminal output back into repository files.
- Prefer patch-based file edits over terminal-mediated rewrite flows.
- When touching files that may already contain Chinese text, treat the file content on disk as authoritative, not the shell rendering.
- If a file appears garbled in the shell, inspect it through a safer path before editing.

## Pitfall 2: `npm` PowerShell shim may be blocked by execution policy

### Symptom

Running `npm run ...` directly from PowerShell can fail with script-execution-policy errors because `npm.ps1` is blocked.

### What worked

Use `npm.cmd` or `npx.cmd` explicitly.

Example:

```powershell
& 'C:\Program Files\nodejs\npm.cmd' run test:e2e
& 'C:\Program Files\nodejs\npx.cmd' playwright test --list
```

### Recommendation

Any automation intended for Windows PowerShell should prefer `.cmd` entrypoints when invoking Node package tools.

## Pitfall 3: sandboxed Node child-process spawning can fail with `EPERM`

### Symptom

Playwright and Vite failed inside the default sandbox with errors such as:

- `spawn EPERM`
- Vite/esbuild startup failure
- Playwright worker fork failure

### Where it happened

- Playwright internal worker processes
- Playwright `webServer` startup mode
- Vite config loading via esbuild

### Operational conclusion

This was an execution-environment limitation, not a repository-code regression.

### What worked

The browser suite had to be run outside the default sandbox on isolated ports, with the backend and frontend started explicitly first.

### Recommendation

If Playwright fails immediately with process-spawn `EPERM`, treat it as an environment problem first, not as an application problem.

## Pitfall 4: Playwright `webServer` auto-start was too fragile for this environment

### Symptom

Even after the repository structure was fixed, Playwright startup remained unreliable when it was allowed to manage backend/frontend servers itself.

### Root causes observed

- sandbox restrictions on subprocess creation
- stale ports responding from older processes
- frontend dev server returning misleading non-application responses

### What worked

Introduce a mode where Playwright does not start `webServer` itself and instead reuses pre-started external servers.

Operationally this required:

- isolated API/UI ports
- explicit health checks
- explicit `E2E_API_URL`
- explicit `PLAYWRIGHT_BASE_URL`
- explicit `PLAYWRIGHT_USE_EXTERNAL_SERVERS=1`

### Recommendation

For long or important Windows E2E runs, prefer:

1. start backend explicitly
2. start Vite explicitly
3. verify API `200`
4. verify UI root returns a real `200`, not just "a port is open"
5. run Playwright against those servers

## Pitfall 5: a `404` from the UI port is not a valid readiness signal

### Symptom

At one point the UI port returned `404`, which looked like "the server is reachable", but the actual SPA was not serving correctly for the intended test session.

### Why this is dangerous

- A stale process or wrong server can occupy the target port.
- The browser tests may then time out on missing controls rather than failing at startup.
- This can waste significant debugging time because the failure presents as missing DOM state instead of incorrect environment boot.

### Recommendation

Treat a UI dev server as healthy only if the root page returns `200` and renders the expected app shell.

Do not accept "some HTTP response exists" as sufficient readiness.

## Pitfall 6: old listening processes can silently poison later test runs

### Symptom

Ports previously used by older frontend or backend processes may remain occupied, causing later runs to hit stale services instead of the newly started test stack.

### Consequences

- false-positive readiness checks
- wrong database backing the test run
- UI selectors timing out because the browser is looking at an old page

### What worked

- use isolated ports for each serious rerun
- explicitly verify both API and UI against the intended process
- avoid reusing 3012/8012 blindly if earlier test attempts may have left residue

## Pitfall 7: pytest temporary-directory behavior on Windows can fail before business assertions run

### Symptom

Backend tests initially failed in pytest temp-directory setup/cleanup with `PermissionError` and directory-numbering failures unrelated to application logic.

Observed failure shapes included:

- cleanup of basetemp failing
- temp root under `%TEMP%` inaccessible
- numbered temp dir creation failing on Windows
- pytest helper symlink behavior not behaving well in this environment

### Important distinction

These were test-runner infrastructure failures, not backend logic failures.

### What was needed

Repository-level pytest bootstrapping had to force a safer Windows temp-root strategy and soften problematic Windows temp-dir behavior for this environment.

### Recommendation

When backend tests fail before test bodies run, inspect pytest temp-path behavior first before blaming the product code.

## Pitfall 8: background process survival differs between direct execution and detached PowerShell sessions

### Symptom

A backend command that stayed alive when run interactively did not necessarily stay alive when launched as a hidden detached process from a separate automation step.

### Consequence

Health checks could fail even though the exact same command was valid.

### What worked

Using a single controlling script that:

- starts the backend,
- starts the frontend,
- waits for health,
- runs the browser tests,
- then tears everything down

was much more reliable than trying to launch background services in one step and test them in later independent shell calls.

## Pitfall 9: migrated test files may lose implicit Node module resolution

### Symptom

After moving E2E specs from `frontend/e2e/` to `tests/e2e/web-admin/`, Node module resolution for `@playwright/test` no longer worked automatically for the moved files.

### Why it happened

The specs were no longer physically under the frontend package tree, so relative module lookup assumptions changed.

### What worked

The Playwright config had to set up module resolution explicitly from the admin frontend package context.

### Recommendation

Whenever tests are moved outside the owning package root, re-check module resolution immediately with `playwright test --list` before attempting the full suite.

## Pitfall 10: `git` index updates may need elevated execution in this environment

### Symptom

Some `git` operations failed with:

- inability to create `.git/index.lock`

### Practical effect

Normal local staging may fail even though file changes are correct on disk.

### Recommendation

If `git add` or related index-writing commands fail with index-lock permission errors in this environment, treat that as an execution-permission problem rather than a repository-integrity problem.

## Pitfall 11: Playwright `webServer` on Linux uses `python3` without project packages

### Symptom

Playwright fails immediately when starting the API, with stderr similar to:

- `No module named uvicorn`

### Why it happens

The Playwright config may spawn the backend with the system `python3`. That interpreter often does not have `requirements.txt` installed, while the repository expects a local virtual environment.

### What worked

- Point the API command at `.venv/bin/python` when that path exists, or set `E2E_PYTHON` to an interpreter that has backend dependencies installed.

### Relationship to other guidance

This is the same operational idea as checklist item 1 ("use the repository `.venv`"), but it applies specifically to **who** starts uvicorn when tests use managed `webServer`.

## Pitfall 12: Element Plus default locale vs Chinese button labels in tests

### Symptom

A test waits for `getByRole('button', { name: '确定' })` or `关闭`, but Playwright reports strict-mode violations or timeouts. The dialog may show **OK** / **Cancel**, or the header close button may expose a different accessible name (for example **关闭此对话框**).

### Why it matters

Without registering a Chinese locale for Element Plus, `ElMessageBox.confirm` and similar components follow English defaults even when surrounding UI copy is Chinese.

### Safe handling strategy

- Register Element Plus `zh-cn` (or match tests to the actual accessible names rendered in your locale), or use narrow selectors (for example `name: '关闭', exact: true` vs the header close button).

## Pitfall 13: Playwright strict mode and duplicate text matches

### Symptom

`expect(locator).toBeVisible()` fails with **strict mode violation**: one locator resolved to **two or more** elements (for example the same homework title in the page subtitle and in a table cell).

### Recommendation

Prefer `.first()` only when intentionally accepting ambiguity, or better:

- role-based locators (`getByRole('cell', { name: ... })`),
- scoped locators (table body vs header),
- or `data-testid` hooks.

## Pitfall 14: `textarea:first()` on the homework submit page is often the wrong control

### Symptom

Submission-related E2E polls the API forever: attempt count stays `0`, or POST `/api/homeworks/{id}/submission` never fires as expected.

### Why it happens

The homework submit view renders **CourseDiscussionPanel** (with its own textarea) **above** the homework submission form. `page.locator('textarea').first()` fills the discussion draft, not `homework-submit-content`.

### Recommendation

Target the homework body field explicitly, for example `getByTestId('homework-submit-content')`, for any flow that must submit homework rather than post a discussion reply.

## Pitfall 15: client `page_size` larger than the API allows

### Symptom

The materials UI shows an empty table even though seeded data exists, or E2E cannot find a known material title.

### Why it happens

List endpoints validate `page_size` with an upper bound (for example `le=100`). A client request with `page_size=200` may return **422**; the UI may not surface the validation error clearly.

### Recommendation

Keep client requests aligned with FastAPI/Pydantic limits. When debugging empty lists, inspect network responses for 422 before assuming seed or routing bugs.

## Pitfall 16: duplicate `course_enrollments` rows during startup reconciliation (often seen with SQLite)

### Symptom

Backend crashes during application lifespan or pytest/E2E startup with:

- `sqlite3.IntegrityError: UNIQUE constraint failed: course_enrollments.subject_id, course_enrollments.student_id`

### Interpretation

Multiple reconciliation paths can attempt to insert the same enrollment for the same student and course. SQLite may surface the race more readily during startup batches.

### What worked in practice

Defensive idempotency at insert time (for example nested transactions / savepoints and treating duplicate key as "already enrolled") so startup reconciliation does not abort the whole process.

### Recommendation

When this appears, treat it first as **reconciliation idempotency**, not as corrupted business data, until proven otherwise.

## Remaining unease after advanced E2E and behavior passes (May 2026)

These are not documented as solved product defects; they are **risk surfaces** that stayed uncomfortable while authoring higher-difficulty tests:

- **Notification mark-all-read vs UI**: server semantics can be correct while the UI remains temporarily ambiguous under concurrency; treating API responses as authoritative remains mandatory.
- **SQLite concurrency**: even after idempotent inserts, **lost updates** remain possible for counters updated via ORM read-modify-write; concurrent increment paths may need SQL-level atomic updates.
- **Router-driven redirects**: admin accounts skip student-facing navigation assumptions; tests must mirror **actual role routing**, not an idealized “open any path” model.
- **`expect.poll` footguns**: returning `undefined`/`null` can prevent predicate satisfaction until timeout; ensure the predicate returns a definite boolean or use assertions inside the callback carefully.

## Pitfall 17: admin SPA router redirects hide student routes until course context exists

### Symptom

Playwright navigates to `/points-display`, `/homework`, `/notifications`, etc., but lands elsewhere or never reaches the expected shell controls until timeouts.

### Why it happens

The admin SPA `router.beforeEach` redirects **admin users** away from many paths students use, and **students** may be forced through `/courses` until `selectedCourse` / enrollment context is resolved.

### Recommendation

For student flows that depend on a seeded course, call the same **`enterSeededRequiredCourse`** helper used by other specs **before** asserting pages that assume teaching/student course context.

## Pitfall 18: Playwright strict mode with multiple tables (`getByRole('table')`)

### Symptom

`expect(page.getByRole('table')).toBeVisible()` fails with strict-mode violations or resolves the wrong table (layout chrome vs-data tables).

### Recommendation

Scope locators: `page.locator('.ranking-card').getByRole('table').first()` (or another stable ancestor), rather than the page-global role query.

## Pitfall 19: student course-catalog enrollment flags (`is_enrolled`, not legacy JSON guesses)

### Symptom

Assertions like `row.enrolled` always fail even though the UI shows enrollment; API responses look “wrong”.

### Why it happens

The student catalog schema exposes **`is_enrolled`** (see `StudentCourseCatalogItem`). Older informal field names are misleading.

### Recommendation

Assert **`is_enrolled`** / documented schema fields, not ad hoc property names copied from other payloads.

## Pitfall 20: user updates use `PUT`, not `PATCH`

### Symptom

E2E sends `PATCH /api/users/{id}` expecting `{ is_active: false }`; nothing changes and downstream bearer validation assertions fail.

### Recommendation

Match the backend route family (`PUT /api/users/{id}` for updates in this repository) when scripting admin changes.

## Pitfall 21: `POST /api/notifications/mark-all-read` takes `subject_id` as a query parameter

### Symptom

Posting JSON `{ subject_id: ... }` to `mark-all-read` silently behaves like “no filter” or fails validation expectations.

### Recommendation

Mirror the SPA client: **`POST /api/notifications/mark-all-read?subject_id=<id>`** (FastAPI `Optional[int]` query params).

## Pitfall 22: clicking disabled “mark all read” can stall `Promise.all`

### Symptom

An E2E runs until the **suite timeout** with no obvious failure until you notice Playwright waiting forever on a click.

### Why it happens

The notifications UI disables “全部标为已读” when `unreadCount === 0`. Putting `click()` inside `Promise.all` alongside API racing calls may block indefinitely.

### Recommendation

Prefer API-only storms for concurrency scenarios, or guard clicks with enabled checks; do not parallelize unconditional UI clicks with uncertain disabled state.

## Pitfall 23: homework submission success copy varies (`作业已提交` vs “已保存”)

### Symptom

Assertions waiting only for `/已保存/` miss Element Plus success toasts.

### Recommendation

Allow multiple known success patterns consistent with `HomeworkSubmission.vue` (`作业已提交`, etc.).

## Pitfall 24: SQLite `UNIQUE` on first-create paths vs lost updates on counters

### Symptom A — inserts

Concurrent first-time inserts into uniqueness-constrained rows (examples encountered while extending coverage: `homework_submissions`, `student_points`) surface **`IntegrityError`** under parallel requests.

### What helps

Treat duplicate-key as “already exists”, rollback, reload the row, and continue; homework submission creation paths adopted this pattern during stress testing.

### Symptom B — updates

Concurrent “read balance → add → write” increments lose totals even without duplicate inserts.

### What helps

Prefer **single-statement SQL increments** (`UPDATE ... SET total_points = total_points + :delta`) for hot counters instead of ORM read-modify-write in parallel threads.

## Pitfall 25: helper `fetch` / `fetchRaw` double-prefixes the API base URL

### Symptom

`TypeError: Failed to parse URL` or URLs like `http://127.0.0.1:8012http://127.0.0.1:8012/api/...`.

### Why it happens

A helper already prefixes `apiBase()`, but the test passes a **full absolute URL** as the path argument.

### How to avoid (test side)

- Pass **path-only** strings to shared helpers (`/api/...`), **or**
- Teach the helper to treat `http://` / `https://` prefixes as already-absolute and skip concatenation.

## Pitfall 26: `fetchRaw`-style helpers and JSON bodies — avoid double encoding

### Symptom

Backend `500` / `AttributeError` (for example attendance batch) because the route receives a **string** where it expects a parsed object.

### Why it happens

The test passes `JSON.stringify(body)` while the helper also sets `Content-Type: application/json` and may stringify again, or the server assumes `dict` and calls `.get` on a string.

### How to avoid (test side)

- Pass a **plain object** as the body and let one layer perform `JSON.stringify`.
- If you must send raw bytes, match what the backend route declares (form vs JSON).

## Pitfall 27: asserting fields that the API response model does not expose

### Symptom

`expect.poll` never succeeds: the test checks `homework_title` (or similar) on a payload that only includes **`HomeworkSubmissionHistoryResponse`** fields (`summary`, `attempts`), not the parent homework row.

### How to avoid (test side)

- Before writing polls, confirm field names against **`apps/backend/wailearning_backend/api/schemas.py`** or a sample `GET` in Swagger/OpenAPI.
- For “title updated” convergence, prefer **`GET /api/homeworks/{id}`** (or the list endpoint) for the homework record, not the submission history response.

## Pitfall 28: Pydantic validation limits are easy to violate in scripted payloads

### Symptom

`422` on appeals, LLM course settings, or other endpoints when the test uses too-short strings or token counts below `ge=...`.

### Examples encountered

- Appeal `reason_text` minimum length (validators strip and enforce a floor).
- `max_input_tokens` / `max_output_tokens` on course LLM config have **minimums** (for example 1000) — values chosen only to “stress” the worker may be **invalid for the schema**.

### How to avoid (test side)

- Read the schema / router for **`Field(ge=...)`** and custom validators before choosing edge values.
- Separate “invalid on purpose” cases (expect 422) from “happy path” cases.

## Pitfall 29: UI title vs API title — heading selectors may not match the DOM

### Symptom

API polls green, but `getByRole('heading', { name })` times out on the homework submit page.

### How to avoid (test side)

- After authoritative API state is correct, **`reload`** the page and assert **`body` text** or a broader title locator (`h1`, `h2`, `.page-title`) with `filter({ hasText })`, not only `heading` role, unless you verified the component’s a11y tree.

## Pitfall 30: password-change + token invalidation tests must capture the old token first

### Symptom

The test obtains a **new** token after the UI already changed the password, then expects `401` — receives `200` because the new token is valid.

### How to avoid (test side)

- Call `obtainAccessToken(...)` **before** any UI action that changes credentials.
- After UI submit, **poll** `GET /api/auth/me` with the **old** token until `401` (or a short wait for commit), because UI “success” can race the DB update.

## Pitfall 31: attachment download tests must respect how the server authorizes URLs

### Symptom

`404` or `403` when `GET`ting a file right after `POST /api/files/upload`: the bytes exist on disk but **no row** references the URL yet (name-based download resolves candidates via DB paths like homework, materials, notifications, **and** user avatar).

### How to avoid (test side)

- For “download works” coverage, either **link** the file the way production does (homework submission, material, **or** `POST /api/auth/me/avatar`), **or** assert the documented behavior for orphan uploads.
- When building a path for `fetch`, handle **relative** `attachment_url` values (`/api/files/...`) — do not assume `new URL(fileUrl)` without a base when the server returns a path-only URL.

## Pitfall 32: Element Plus `ElMessageBox.confirm` title is not always the dialog’s accessible name

### Symptom

Playwright waits forever on `getByRole('dialog', { name: /删除课程/ })` or the confirm button inside it, while the UI visibly shows the delete confirmation.

### Why it matters

MessageBox markup and locale wiring do not guarantee that the **title string** is exposed as the dialog’s **accessible name** in every Element Plus version or configuration.

### How to avoid (test side)

- Prefer targeting the overlay that contains the primary action, for example `page.getByRole('dialog').filter({ has: page.getByRole('button', { name: /^(确定|OK)$/ }) })`, then click **确定/OK** inside that dialog (same pattern as advanced coverage specs).

## Pitfall 33: Student “我的课程” page shows the same course title twice (catalog table vs course cards)

### Symptom

`page.locator('tr').filter({ hasText: courseName })` or `row.getByRole('button').first()` clicks **刷新目录** or hits the wrong row; API polls never reach the expected enroll/drop state.

### Why it happens

`MyCourses.vue` renders the **elective catalog** in a table and also lists **active courses** as cards below. The same `name` can appear in both regions; the first `tr` match or the first button in a row may not be **选课/退选**.

### How to avoid (test side)

- Scope locators to the catalog card only, e.g. `.elective-catalog-card` + `.el-table__body tbody tr`, then click **`getByRole('button', { name: '选课' })`** or **`'退选'`** explicitly — never `row.getByRole('button').first()`.

## Pitfall 34: `click({ force: true })` on a disabled Element Plus button is a silent no-op

### Symptom

Dual-tab elective enroll/drop tests time out on `expect.poll` even though the test “clicked” 退选/选课.

### Why it happens

In `MyCourses.vue`, **退选** stays `:disabled` until local `courses` includes the elective (`isElectiveEnrollment`). Catalog `is_enrolled` can be true while the button is still disabled for a short window. **`force: true` does not enable a disabled control.**

### How to avoid (test side)

- **`await expect(button).toBeEnabled({ timeout: … })`** before `click()` (without `force`), or assert API-side state first and reload the page if you intentionally need a cold DOM.

## Pitfall 35: `waitForResponse` registered after `click()` misses a fast 200

### Symptom

`TimeoutError` waiting for `POST …/roster-enroll` even though the UI closed the dialog and enrollment succeeded.

### Why it happens

The response can complete before Playwright attaches the listener.

### How to avoid (test side)

- Start **`page.waitForResponse(...)`** and **`click()`** in the same **`Promise.all([...])`**, or use **`expect.poll`** on API state instead of relying on a single network event.

## Pitfall 36: Over-broad `getByRole('button', { name: /密码/ })` matches the wrong control

### Symptom

Password-change / token-invalidation specs never call `POST /api/auth/change-password` or behave randomly.

### Why it happens

Section headers and other controls can match a loose `/密码/` regex; the real submit control on `PersonalSettings.vue` is **`更新密码`**.

### How to avoid (test side)

- Prefer **exact** button labels from the Vue template (`更新密码`) or `data-testid` if one is added later.

## Pitfall 37: Vite `webServer` + repeated `goto('/login')` — navigation interrupted or `net::ERR_ABORTED`

### Symptom

`page.goto('/login')` throws **interrupted by another navigation** or **`net::ERR_ABORTED`**, or `page.evaluate` fails with **Execution context was destroyed**, often after a long E2E run or when the dev server reloads.

### How to avoid (test side)

- Use **`waitUntil: 'domcontentloaded'`** (not only `load`) for login hops, **retry** `goto` on the errors above, and treat **`goto` + `localStorage.clear`** as best-effort if the page navigates mid-call.
- Before starting a new Playwright process, ensure **no stray `node`/`vite`/`chrome`** holds `E2E_UI_PORT` / `E2E_API_PORT` when `reuseExistingServer` is false — otherwise `webServer` fails to bind and the suite misleads you into “app” failures.

## Pitfall 38: Admin delete-course UI assertion races the subjects table refresh

### Symptom

`DELETE /api/subjects/{id}` returns **200**, but `getByTestId('subjects-delete-{id}')` still exists for tens of seconds — `toHaveCount(0)` times out.

### Why it happens

The list row is driven by client state; **`loadCourses()`** (or equivalent) may lag behind the successful API delete, especially under Vite dev + SQLite E2E load.

### How to avoid (test side)

- After a successful delete response, **`expect.poll` on `GET /api/subjects`** until the id disappears, then **`page.goto('/subjects')`** (or wait for an explicit table reload) before asserting row-level UI.

## Pitfall 39: `page_size` upper bounds differ by route — do not assume `le=100` everywhere

### Symptom

A test expects **`422`** for `page_size=200` on **`/api/students`**, but receives **200** — because that list allows **`le=1000`**.

### Why it matters

Copy-pasting “`page_size=200` means 422” from homework/materials/notifications tests will create **false failures** on routes with different `Query(..., le=...)`.

### How to avoid (test side)

- Read the **`Query(..., le=)`** on the FastAPI handler (or grep `page_size` in `apps/backend/wailearning_backend/api/routers/`) before picking an out-of-range value. Prefer **`page_size = max_allowed + 1`** per route family.

## Pitfall 40: `force: true` on Element Plus table row checkboxes can skip selection state

### Symptom

`page.waitForResponse` for `POST .../roster-enroll` times out (up to 120s) on `Subjects.vue` “从花名册进课” even though the dialog and row are visible.

### Why it happens

`btn-roster-enroll-submit` stays **disabled** until `rosterEnrollSelection` is non-empty selection from `el-table` **selection-change**. A forced click on the row checkbox can fail to run the same code path as a normal user click, so no row is selected, the primary button remains disabled, and a second **`click({ force: true })` on the disabled button** is a no-op—no network request, endless wait for response.

### How to avoid (test side)

- Click the table selection checkbox **without** `force: true` (or use the table’s public selection API if you add one in the app for tests only).
- **`await expect(getByTestId('btn-roster-enroll-submit')).toBeEnabled()`** before pairing `waitForResponse` with submit.
- If you need `force` on the submit click, do not use it on the checkbox first; re-read Pitfall 34 for disabled-control semantics.

## Proven Command Patterns

### Backend full suite

```powershell
& '.\.venv\Scripts\python.exe' -m pytest tests -rs -q
```

### Playwright test discovery

```powershell
$env:PLAYWRIGHT_BROWSERS_PATH='C:\Users\<user>\AppData\Local\ms-playwright'
& 'C:\Program Files\nodejs\npx.cmd' playwright test --list
```

### Windows-safe Node package invocation

```powershell
& 'C:\Program Files\nodejs\npm.cmd' run test:e2e
& 'C:\Program Files\nodejs\npx.cmd' playwright test
```

## Recommended Execution Order for Future Full Validation

1. Confirm no stale backend/frontend processes are occupying the intended ports.
2. Use the repository `.venv` explicitly for backend commands **and** for any Playwright-managed API process when using `webServer` (see Pitfall 11).
3. Run backend `pytest` first, because it is cheaper and exposes import/path regressions quickly.
4. For Playwright on Windows, prefer isolated ports and explicit external-server startup.
5. Require UI root `200` before starting browser tests.
6. If Playwright fails with `EPERM`, retry outside the restricted sandbox before concluding the suite is broken.
7. If a single concurrency scenario fails after a long mostly-green run, rerun that one case in isolation before treating it as a deterministic regression.
8. On Linux/CI, if the browser suite fails to boot the API, verify `uvicorn` runs under the project venv before assuming application regressions.

## Incremental Field Notes: PostgreSQL-Aligned UI/UX Audit on Windows

This subsection records a later UI/UX audit setup pass where the operator needed
real browser screenshots against a PostgreSQL-backed backend, not the default
SQLite-backed Playwright webServer path. These notes are intentionally additive:
they do not replace the earlier Playwright or PostgreSQL guidance above.

### Goal

The audit goal was to inspect the admin SPA through Playwright screenshots while
using a production-aligned PostgreSQL database. SQLite was acceptable only for
quick local smoke and was explicitly rejected as the main evidence source for
UI/E2E behavior that depends on real persistence semantics.

### What worked

The reliable approach in a restricted Windows automation environment was:

1. Use an ignored artifact directory such as `<repo>/.e2e-run/postgres-runtime/`.
2. Download an official EDB PostgreSQL Windows x64 binary zip into that ignored
   directory. The pass used PostgreSQL `16.13`.
3. Extract the archive locally and use the bundled `initdb.exe`,
   `postgres.exe`, `psql.exe`, and `pg_isready.exe` from
   `<artifact-dir>/pgsql/bin/`.
4. Initialize a local throwaway cluster in an ignored data directory, for
   example `<artifact-dir>/data-clean`, with local trust auth.
5. Run PostgreSQL on a non-production loopback port, for example
   `127.0.0.1:15432`.
6. Create a clearly disposable database such as `wailearning_uiux_audit`.
7. Start the backend with:
   - `DATABASE_URL=postgresql://postgres@127.0.0.1:15432/wailearning_uiux_audit`
   - `E2E_DEV_SEED_ENABLED=true`
   - `E2E_DEV_SEED_TOKEN=<test token>`
   - `INIT_DEFAULT_DATA=false`
   - `ENABLE_LLM_GRADING_WORKER=false`
   - a local-only `SECRET_KEY`
8. Seed data through `POST /api/e2e/dev/reset-scenario` with the same
   `X-E2E-Seed-Token`.
9. Start Vite from `apps/web/admin` with
   `VITE_PROXY_TARGET=http://127.0.0.1:<api-port>`.
10. Use Playwright screenshots and DOM snapshots against the Vite URL.

### Pitfall A: local machine may have no PostgreSQL service, Docker, psql, or winget

The pass first checked for:

- a running PostgreSQL service,
- `psql.exe` / `postgres.exe` / `pg_ctl.exe`,
- Docker,
- `winget`,
- `DATABASE_URL` / `TEST_DATABASE_URL`.

None were available in that environment. Do not assume a Windows machine already
has a database runtime just because the repository is PostgreSQL-first.

### Pitfall B: Chocolatey can exist but still be unusable for PostgreSQL install

Chocolatey was installed, but `choco install postgresql` failed because the shell
did not have administrator access to Chocolatey system directories and could not
write `lib-bad` or clear package lock state.

Avoid treating "Chocolatey exists" as equivalent to "the agent can install a
system PostgreSQL service." If Chocolatey needs admin rights, prefer a
user-directory binary archive when the task only needs a temporary local
database.

### Pitfall C: `pg_ctl` can fail on restricted Windows tokens

`initdb.exe` completed the cluster initialization but emitted Windows restricted
token errors at the end. `pg_ctl.exe start` also failed with restricted token
errors. The cluster files were still usable.

What worked was direct `postgres.exe -D <data-dir> -h 127.0.0.1 -p <port>` rather
than `pg_ctl.exe`, provided the process was launched in a context that could keep
it alive for the audit.

### Pitfall D: PostgreSQL writes normal LOG output to stderr

When wrapping `postgres.exe` with PowerShell, normal PostgreSQL startup lines can
arrive on stderr. If a wrapper script sets `$ErrorActionPreference = 'Stop'`,
PowerShell may treat a harmless startup LOG line as a native command error and
exit before PostgreSQL finishes starting.

For wrapper scripts around `postgres.exe`, either avoid `Stop` for native stderr
or redirect/handle stderr deliberately.

### Pitfall E: background process lifetime can differ by launcher

Several background launch attempts returned a process id but did not leave a
listening PostgreSQL server for the next command. Direct foreground startup
proved PostgreSQL itself was valid, but hidden `Start-Process`, `cmd /c`, and
PowerShell job patterns were unreliable in that sandboxed automation context.

When cross-command background processes are unreliable, use one orchestrator
process that starts PostgreSQL, backend, frontend, and Playwright inside the same
lifetime. In this pass, a local ignored Node script performed that orchestration.

### Pitfall F: Node child process spawn may be blocked in the default sandbox

The orchestrator initially failed with `spawn EPERM`, matching the broader
Playwright webServer `EPERM` pitfall. The fix was to run the orchestrator outside
the restricted sandbox/with the necessary execution approval. This is an
environment restriction, not evidence that PostgreSQL, Vite, or the app is
broken.

### Pitfall G: Vite must be started from the admin app directory

Starting Vite with the Vite binary path while the current working directory was
the repository root produced a root URL that returned `404`. The fix was to set
the frontend process working directory to `<repo>/apps/web/admin` before running
Vite.

This matters for custom audit scripts and external-server Playwright flows:
`node <repo>/apps/web/admin/node_modules/vite/bin/vite.js` is not sufficient by
itself if the working directory is wrong.

### Pitfall H: repeated role login can hang if the previous session is still active

A screenshot script that logs in as admin and then navigates to `/login` to log
in as teacher/student can hang or redirect unexpectedly if the app immediately
redirects an already-authenticated user away from `/login`.

The robust helper should clear `localStorage` and `sessionStorage` before each
fresh role login, then navigate to `/login` and submit credentials.

### Pitfall I: PostgreSQL recovery after forced audit timeouts can add startup delay

Several interrupted experiments left the throwaway cluster needing crash
recovery. `pg_isready` reported `rejecting connections` before eventually
accepting connections. For clean audit runs, either shut PostgreSQL down
gracefully or reinitialize a new throwaway data directory such as
`data-clean`.

### Pitfall J: DOM snapshots and screenshots can disagree during page startup

A UI audit can produce a JSON snapshot showing that page text, buttons, and
routes exist while the paired screenshot is still blank or partially painted.
This usually means the screenshot was taken before the stable visual container
was visible, not that the JSON snapshot is wrong.

For login and other app-shell entry pages, do not rely on `page.goto(...)`
alone. Add stable page-level test IDs in product code and wait for the visible
panel before capture. Example pattern:

```javascript
await page.goto('/login', { waitUntil: 'domcontentloaded' })
await page.getByTestId('login-panel').waitFor({ state: 'visible', timeout: 30000 })
await page.waitForTimeout(300)
await capture(page, 'login')
```

The exact script path should be documented as `<repo>/...` or
`<artifact-dir>/...` in committed docs. If the machine-specific path matters for
a handoff, put it in an ignored local note instead.

### Artifact hygiene

Keep all of the following out of tracked source:

- downloaded PostgreSQL zips,
- extracted PostgreSQL binaries,
- local data directories,
- audit launch scripts,
- screenshots,
- runtime logs,
- seeded scenario JSON files.

Use ignored directories such as `.e2e-run/`. If a temporary spec is created under
`tests/e2e/...` for experimentation, delete it before committing unless it is a
deliberate maintained test.

### Privacy hygiene

Do not paste user-specific absolute paths into committed documentation. Use
placeholders such as:

- `<repo>`
- `<user-home>`
- `<artifact-dir>`
- `<api-port>`
- `<ui-port>`

Local handoff files can contain machine-specific paths when the next operator on
the same machine needs them, but committed docs should stay portable.

## Frontend Build And Playwright Invocation Directory Pitfalls

This subsection records command-invocation mistakes encountered while adding a
focused UI outline guard. The product code was not the root cause; the failures
came from running the right tools from the wrong directory or outside the test
configuration boundary.

### Pitfall: root-level `npm.cmd run build` can fail with missing `package.json`

Symptom:

```text
npm error enoent Could not read package.json
npm error path <repo>/package.json
```

Cause:

The admin frontend package lives under:

```text
<repo>/apps/web/admin
```

The repository root is not the frontend package root and does not own the
admin SPA `package.json`.

Fix:

Run the build from the frontend app directory:

```text
cd <repo>/apps/web/admin
npm.cmd run build
```

Interpretation:

Do not treat this failure as a dependency install failure or a Vite failure.
It is a working-directory failure. Re-run from the frontend package before
changing code, reinstalling packages, or editing build configuration.

### Pitfall: Playwright project names disappear when running from the spec directory

Symptom:

```text
Error: Project(s) "chromium" not found. Available projects: ""
```

Cause:

The Playwright config for the admin SPA is in:

```text
<repo>/apps/web/admin/playwright.config.cjs
```

Running `npx.cmd playwright test ... --project=chromium` from
`<repo>/tests/e2e/web-admin` can fail to load that config. Without the config,
the CLI does not know about the `chromium` project.

Fix:

Run maintained admin Playwright specs from:

```text
<repo>/apps/web/admin
```

Use the configured test file name relative to the configured `testDir`, for
example:

```text
npx.cmd playwright test ui-homework-history-outline-regression.spec.js --project=chromium
```

Interpretation:

This is not evidence that Chromium is missing. It means the command did not
load the project configuration.

### Pitfall: path arguments outside configured `testDir` may report "No tests found"

Symptom:

```text
Error: No tests found.
Make sure that arguments are regular expressions matching test files.
```

Cause:

The admin Playwright config sets:

```text
testDir: ../../../tests/e2e/web-admin
```

Passing a path outside that directory, such as an ignored local script under
`<artifact-dir>`, does not necessarily behave like a one-off arbitrary spec
runner. The config still scopes discovery around its `testDir`.

Fix:

For maintained tests, keep the spec under `<repo>/tests/e2e/web-admin` and run
it by filename from `<repo>/apps/web/admin`.

For local screenshot experiments, either:

- temporarily add screenshot capture to a maintained spec and remove it before
  commit; or
- create an ignored local Node script that imports Playwright directly and also
  recreates any module-resolution setup the Playwright config normally provides.

Interpretation:

Do not expand `testDir` just to run a local screenshot helper. Keep ignored
artifacts ignored and keep maintained test discovery narrow.

### Pitfall: local Node screenshot scripts may not inherit Playwright config module resolution

Symptom:

```text
Error: Cannot find module '@playwright/test'
Require stack:
- <repo>/tests/e2e/web-admin/fixtures.cjs
- <artifact-dir>/...
```

Cause:

The admin Playwright config prepends the frontend `node_modules` directory to
`NODE_PATH` and calls `Module._initPaths()` before running tests. A direct local
Node script does not inherit that setup unless it recreates it.

Fix:

For local-only scripts, add the equivalent setup before importing E2E helpers:

```javascript
const Module = require('module')
const adminNodeModules = '<repo>/apps/web/admin/node_modules'
process.env.NODE_PATH = [adminNodeModules, process.env.NODE_PATH].filter(Boolean).join(path.delimiter)
Module._initPaths()
```

Use placeholder paths in committed docs. Put real absolute paths only in ignored
local notes.

Interpretation:

This failure does not mean `@playwright/test` is missing from the frontend app.
It means the direct script skipped the configuration bootstrap that normally
makes the package visible to shared E2E helpers.

## What This Document Does Not Claim

It does not claim SQLite and PostgreSQL accept the same SQL text for every ad hoc query embedded in tests.

### Pitfall 41: Playwright `read ECONNRESET` / `TypeError: fetch failed` with default E2E ports

Symptom:

```text
TypeError: fetch failed
[cause]: Error: read ECONNRESET
```

Context:

Admin Playwright defaults commonly bind the backend to `http://127.0.0.1:8012` and the SPA to
`http://127.0.0.1:3012`. Mock LLM traffic stays on-loopback under paths such as
`/api/e2e/dev/mock-llm/<profile>/v1/`. This is **not** an external provider outage.

Cause:

Two or more Playwright CLI processes (or stray `uvicorn` / `vite` processes) can race the same
fixed ports. The browser then hits a half-dead server, a wrong process, or a torn-down connection,
which surfaces as `ECONNRESET` rather than a clear HTTP error.

Fix:

- Run narrow E2E greps **serially** (one `npx playwright test ...` at a time).
- Before blaming product code, check for duplicate listeners on `8012` / `3012` (or whatever
  `E2E_API_PORT` / `PLAYWRIGHT_BASE_URL` you configured).
- When you must parallelize automation, assign **distinct** backend and frontend ports per job and
  isolate databases.

Interpretation:

This failure pattern is usually harness contention, not Codex rate limits and not remote LLM API
instability.

### Pitfall 42: PostgreSQL `IN (...)` lists reject a trailing comma

Symptom:

```text
psycopg2.errors.SyntaxError: syntax error at or near ")"
```

Cause:

In PostgreSQL, `WHERE column_name IN ('a', 'b',)` is invalid because of the trailing comma after the last literal. Some editors or copy-paste patterns introduce that comma when extending a list of legacy column names.

Fix:

Remove the trailing comma after the final element in the `IN` list (or use a tuple/array constructor that your dialect documents).

### Pitfall 43: `Session.merge()` is not always a safe “upsert” in tests

Symptom:

```text
sqlalchemy.exc.IntegrityError: UniqueViolation ... llm_student_token_overrides_student_id_key
```

Context:

A test tries to model “update the per-student override twice” by calling `Session.merge(LLMStudentTokenOverride(...))` twice in the same session.

Cause:

`merge()` resolves identity using SQLAlchemy’s merge algorithm and the current session state. For rows keyed by a **natural unique column** (`student_id`) without a stable primary-key object already loaded, a second `merge()` can still emit an **INSERT** that collides with the first row, especially when the session’s identity map does not contain the persisted instance the test author assumed.

Fix:

- Prefer **`query(...).one()` then mutate attributes** and `commit()`, or
- Call the **application service** (`apply_student_daily_token_overrides` / HTTP API) that already encodes upsert semantics, or
- Use **`db.execute(update(...))`** with an explicit `WHERE student_id = :sid` in low-level constraint tests.

Interpretation:

This is usually a **test harness bug**, not evidence that the database unique constraint is wrong.

### Pitfall 44: Playwright CLI `-q` / unknown option failures in CI

Symptom:

```text
error: unknown option '-q'
```

Context:

Some automation snippets suggest `npx playwright test ... -q` for quieter logs.

Cause:

The installed `@playwright/test` major version may **not** support the `-q` flag on the `playwright test` CLI entrypoint.

Fix:

- Remove `-q` and rely on Playwright’s default reporter, or
- Use supported reporter flags for your installed version (see upstream Playwright release notes for `<REPO_ROOT>/apps/web/admin/node_modules/@playwright/test`).

### Pitfall 45: Many pytest “skips” are environment gates (PostgreSQL dialect), not optional quality

Symptom:

```text
43 skipped
```

Context:

- **`tests/postgres/*`** and **`test_r3`** in `test_regression_llm_quota_behavior.py` require a **PostgreSQL** engine (`information_schema`, transactional semantics).

Cause:

Default `tests/conftest.py` uses **SQLite** unless `TEST_DATABASE_URL` is set (or **`WAILEARNING_AUTO_PG_TESTS=1`** auto-pick is enabled — see [DEVELOPMENT_AND_TESTING.md](DEVELOPMENT_AND_TESTING.md)).

Fix:

1. Install **`unrar`** or **`unrar-free`** so `tests/backend/llm/test_llm_attachment_formats.py` can execute the RAR walks (same tooling the product uses in `domains/llm/attachments.py`). The **`rar`** compressor is **not** required at pytest runtime anymore because regression archives live under **`tests/fixtures/llm_rar/`** (generated offline by maintainers).
2. Run **`bash ops/scripts/dev/provision_postgres_pytest.sh`** (creates `wailearning_pytest_all` + role `wailearning_test`; needs `sudo -u postgres` when the cluster exists).
3. Either `export TEST_DATABASE_URL='postgresql+psycopg2://wailearning_test:wailearning_test@127.0.0.1:5432/wailearning_pytest_all'`, or set **`WAILEARNING_AUTO_PG_TESTS=1`** so `tests/conftest.py` probes that URL and switches `DATABASE_URL` before importing the app.
4. Ensure PostgreSQL is **listening** (`pg_ctlcluster <ver> main start` or your distro equivalent). The provision script fails loudly when `sudo -u postgres` cannot connect.

Interpretation:

**SQLite-only green** is fast but **incomplete** for schema-sensitive merges; CI should aim for **432 passed, 0 skipped** with the recipe above (same collection count as SQLite; Postgres executes the previously skipped modules). Older notes that cite **417** or **45 skips tied to `rar`** describe pre-fixture layouts and should not be used when triaging current branches.

### Pitfall 46: disposable Linux / cloud-agent runners may lack `pytest` until `requirements.txt` is installed

### Symptom

Running the backend suite from `<REPO_ROOT>` fails before any test body executes:

```text
/usr/bin/python3: No module named pytest
```

Or the shell reports that `pytest` is not found when invoked as a bare executable.

### Context

Cursor cloud agents, minimal CI images, and fresh clones often do **not** ship with the repository `.venv` pre-created. The canonical developer workflow assumes `pip install -r requirements.txt` (or an equivalent venv step) before `python -m pytest`.

### Fix

At `<REPO_ROOT>`:

```bash
python3 -m pip install -r requirements.txt
python3 -m pytest tests/ -q
```

Prefer a dedicated `.venv` when the environment allows (see [DEVELOPMENT_AND_TESTING.md](DEVELOPMENT_AND_TESTING.md) Local Development Setup); the important invariant is that the **same interpreter** that runs pytest has project dependencies installed.

### Interpretation

This is **runner bootstrap debt**, not a failing test or a broken import path in `apps.backend.wailearning_backend`. Do not edit `tests/conftest.py` or `pytest.ini` to “fix” a missing `pytest` package on the system interpreter.

### Pitfall 47: `GET /api/homework` is not the student homework list — the plural router is `/api/homeworks`

### Symptom

A hazard or E2E test expects **HTTP 422** (or a JSON list) from:

```text
GET /api/homework?page=1&page_size=200
```

but receives **404** or an HTML error page, so pagination validation never runs.

### Context

`apps/backend/wailearning_backend/api/routers/homework.py` registers `APIRouter(prefix="/api/homeworks", ...)`. There is no first-class list route at `/api/homework` in this branch.

### Fix

Use **`/api/homeworks`** for list queries. Re-run `rg "APIRouter\\(prefix=" apps/backend/wailearning_backend/api/routers/homework.py` before freezing URL literals in new tests.

### Interpretation

This is a **test contract bug** (wrong path), not evidence that FastAPI removed validation for oversized `page_size`.

### Pitfall 48: `npm: command not found` blocks Playwright E2E even when pytest is green

### Symptom

```text
npm: command not found
```

when attempting:

```bash
cd <REPO_ROOT>/apps/web/admin
npx playwright test e2e-agent-hazard-tier-2-15.spec.js
```

### Context

Cloud CI images optimized for Python may omit Node.js entirely. The repository’s Playwright specs live under `<REPO_ROOT>/tests/e2e/web-admin/` but execute via **`apps/web/admin/playwright.config.cjs`**, which requires **`npm ci`** / **`npm install`** inside **`apps/web/admin`** before **`npx playwright`** exists.

### Fix

**Preferred (portable):** Install a supported **Node.js + npm** from your OS or from **https://nodejs.org** (LTS), then:

```bash
cd <REPO_ROOT>/apps/web/admin
npm ci
npx playwright install chromium
```

**Debian/Ubuntu without `nvm` / upstream tarball:** Use distribution packages when the image is Python-first and blocks custom installers:

```bash
sudo apt-get update
sudo apt-get install -y nodejs npm
cd <REPO_ROOT>/apps/web/admin
npm ci
npx playwright install chromium
```

On Ubuntu **24.04** this commonly provides **Node 18.x** and **npm 9.x**, which satisfies the admin `package.json` lockfile in this repository. If `npm ci` fails with an engine mismatch, upgrade Node via NodeSource or official binaries — document the failure in CI logs rather than pinning unsupported ranges in `package.json` without maintainer review.

**Playwright backend process:** `playwright.config.cjs` defaults `E2E_PYTHON` to `<REPO_ROOT>/.venv/bin/python` when that path exists; otherwise **`python3`**. If **`uvicorn` is missing** from the system `python3`, either create `.venv` + `pip install -r requirements.txt` or set **`E2E_PYTHON=/path/to/python-with-deps`** explicitly (observed working: **`E2E_PYTHON=/usr/bin/python3`** after `pip install -r requirements.txt` on the same machine).

### Interpretation

**pytest-only CI** can stay green while **Playwright never runs** — track Node availability separately from Python bootstrap (**Pitfall 46**). **`npm: command not found`** is resolved by **any** compliant Node toolchain, including **`apt-get install nodejs npm`** on Debian-derived agents.

### Pitfall 49: Student sidebar label rename broke brittle Playwright text assertions

### Symptom

Playwright fails with strict-mode or timeout when locating sidebar links:

```text
getByRole('link', { name: '我的课程' })
```

### Context

The admin SPA (`apps/web/admin/src/views/Layout.vue`) grouped student navigation under **`课程学习`** and renamed the first child from **我的课程** to **选课与进度** (route `/courses` unchanged). Older specs that hard-coded the previous visible string will not find the control.

### Fix

Prefer **`page.goto('/courses')`**, **`enterSeededRequiredCourse`** from `tests/e2e/web-admin/fixtures.cjs`, or role selectors anchored on `.elective-catalog-card`. If you must click the sidebar, match **`选课与进度`** or use stable **`data-testid`** hooks if added later.

### Interpretation

This is usually a **test harness expectation drift**, not a routing regression — verify with `router.beforeEach` guards and direct navigation before rewriting product copy back to the old label.

### Pitfall 50: Notification header badge E2E — disabled course card clicks, hover-only dropdowns, badge/API races

### Symptom

Playwright scenarios around **`data-testid="header-notification-badge"`** time out on **`进入课程|查看课程`** with **`element is not enabled`**, or assertions fail when relying on **duplicate** avatar-dropdown notification entries (removed in favor of **sidebar `课程通知`** — update specs accordingly), or the badge digit **lags** `GET /api/notifications/sync-status` by one poll.

### Context

- **`enterSeededRequiredCourse`** (`tests/e2e/web-admin/fixtures.cjs`) clicks the course-card primary button. After a student visits **`/courses`**, the UI may keep that button **disabled** until client enrollment reconciliation catches up — **re-clicking the card is unsafe** for routing-edge specs.
- Element Plus **`hover()`** on **`header-user-menu`** remains timing-sensitive; prefer **`click()`** on triggers when a dropdown must open. Notification routing assertions should use **sidebar** **`getByRole('menuitem', { name: /课程通知/ })`** (student menu) rather than a removed duplicate dropdown row.
- **`Layout.vue`** updates **`headerUnreadCount`** from **`pollNotificationSync`** (route watcher + focus handler). Parallel **`fetch`** writes from the test can advance **`sync-status`** **before** the next **`pollNotificationSync`** completes — **`expect.poll`** pairing badge text with **`sync-status`** avoids flaky strict equality.

### Fix

- For **“return from `/courses` with fresh unread”** scenarios, **`page.goto('/course-home')`** after **`window.dispatchEvent(new Event('focus'))`** rather than calling **`enterSeededRequiredCourse`** twice.
- To verify navigation to **`/notifications`**, use the **sidebar** notification item (see **`e2e-notification-header-sync-tier.spec.js`** case **09**) instead of avatar-dropdown-only flows.
- After multi-step API mutations (two **`POST /api/notifications`**, **`POST .../read`**), use **`expect.poll`** until **`badge digit === sync.unread_count`**.

### Interpretation

These failures showed up while authoring **`tests/e2e/web-admin/e2e-notification-header-sync-tier.spec.js`** on a Linux agent with **`npm`** installed via **`apt-get install nodejs npm`** (see **Pitfall 48**). They are **harness timing / selector** issues unless **`sync-status`** itself diverges from list totals — in that case prefer **`tests/behavior/test_notification_sync_api_edge_behavior.py`** to isolate HTTP contracts first.

### Pitfall 51: Teacher dashboard default course may not be the seeded required course

### Symptom

Playwright asserts **`badge digit === sync-status(...?subject_id=<course_required_id>)`** after **`page.goto('/dashboard')`** but the badge stays **0** or matches a **different** subject.

### Context

**`ensureSelectedCourse`** picks **`rankTeachingCourses`** order (semester + id), not necessarily **`E2E必修课_<suffix>`**. **`notificationSyncParams`** uses **`selectedCourse.id`**, so the layout polls **`sync-status`** for whatever course is selected — which may **not** be `course_required_id` from the seed JSON.

### Fix

Before comparing UI to API for **`course_required_id`**, open **`header-course-switch`** with **`click()`** and select the **`.course-option`** row whose **heading text** matches the seeded required course name.

### Interpretation

Documented while authoring **`tests/e2e/web-admin/e2e-notification-sync-deep-tier.spec.js`** case **02**.

### Pitfall 52: Full Playwright suite + persistent SQLite — `students.parent_code` UNIQUE collisions on `reset-scenario`

### Symptom

Backend log:

```text
sqlite3.IntegrityError: UNIQUE constraint failed: students.parent_code
```

Playwright / `fixtures.cjs`:

```text
E2E seed failed (500): Internal Server Error
```

Follow-on failures: timeouts on `page.goto`, missing table rows, logins that succeed but show empty shells — **not obviously “notification UI broke”**.

### Context

- Admin Playwright uses a **file-backed SQLite** URL (see `apps/web/admin/playwright.config.cjs`; Unix placeholder pattern like `/tmp/playwright_e2e_<port>.sqlite`).
- **`POST /api/e2e/dev/reset-scenario`** runs in many specs’ **`beforeEach`** hooks.
- `Student.parent_code` is **`unique=True`** in `apps/backend/wailearning_backend/db/models.py`.
- If seed assigns **`parent_code`** from a **small** derived space (historically a short prefix of `suffix`), repeated inserts into the **same** SQLite file across a long full-suite run increase collision probability (“birthday paradox” vs leftover rows).

Short targeted runs often pass because the DB file is young or resets are fewer.

### Fix

- **Product / seed fix (preferred):** derive **`parent_code`** from the **full** unique run suffix (or another high-entropy string), not an aggressively truncated token. The E2E seed handler in `apps/backend/wailearning_backend/api/routers/e2e_dev.py` uses **`P{suffix.upper()}`** where **`suffix`** is **`uuid.uuid4().hex[:10]`**, keeping the code space large enough for persistent SQLite full-suite runs.
- **Operator mitigation (diagnostic only):** delete the Playwright SQLite file at `<E2E_SQLITE>` or change **`E2E_API_PORT`** so a fresh file is used — confirms collision vs logic regression; **do not** rely on this instead of seed entropy in CI.

### Interpretation

See also **§ Key pitfall A** in [FULL_PLAYWRIGHT_E2E_RUNBOOK.md](FULL_PLAYWRIGHT_E2E_RUNBOOK.md).

### Pitfall 53: Avatar oversized PNG body hits format validation before the 2 MB guard

### Symptom

`tests/backend/user_profile/test_profile_and_avatar.py::test_avatar_oversized_rejected_and_orphan_not_left_on_disk` expects HTTP **400** with **`Avatar image must be 2 MB or smaller`** (English substring **`2 MB`**). Instead the API returns generic attachment validation text such as **`图片文件无法通过校验…`** when the uploaded bytes are not a valid PNG image.

### Context

`/api/auth/me/avatar` ultimately calls **`save_attachment`**, which runs **`assert_attachment_format_compliant`** before persisting. A synthetic **`huge.png`** payload of **`0xFF` repeated bytes** fails PNG validation **before** `upload_my_avatar` can compare **`size > MAX_AVATAR_BYTES`**.

### Fix

In **`apps/backend/wailearning_backend/api/routers/auth.py`**, read the **`UploadFile`** bytes first and reject **`len(content) > MAX_AVATAR_BYTES`** immediately. Pass bytes into **`save_attachment(..., preloaded=content)`** so oversized rejects happen **without** writing to disk and **without** entering format validation for oversize junk payloads.

### Interpretation

This is a **route-ordering** regression guard: size limits for avatars must precede generic attachment sniffing when the upload route shares **`save_attachment`**.

### Pitfall 54: Markdown discussion collapsed preview flattened newlines (tier-3 **`...`** ellipsis specs broke)

### Symptom

Playwright **`e2e-discussion-cover-llm-tier3.spec.js`** expects **`discussion-row__text`** to contain **`...`** when more than three logical lines exist. Instead the UI showed all lines separated by spaces with **no** ellipsis.

### Context

**`collapsedBodyPreview`** in **`CourseDiscussionPanel.vue`** treated non-plain bodies by replacing **`\n`** with spaces before applying only a **240-character** cap. That bypassed **`previewText()` / `lineSegmentsFromBody()`**, which implement the intended **three logical-line** preview model (including counting **`![](...)`** and **`<img>`** as lines).

### Fix

For markdown bodies, when **`isTruncated(body)`** is true, render **`previewText(body)`** (same helper chain as plain text). Keep expanded rows stable by wrapping both collapsed text and **`PlainOrMarkdownBlock`** inside a persistent **`.discussion-row__text`** container so Playwright locators survive expand/collapse.

### Interpretation

Full-suite runs surfaced this because discussion specs execute late and depend on DOM structure + ellipsis semantics staying aligned with **`PREVIEW_LINE_LIMIT`**.

### Pitfall 55: Powerful `/api/e2e/dev/*` routes now expect admin Bearer when `E2E_DEV_REQUIRE_ADMIN_JWT` is true

### Symptom

Playwright or curl calls return **403** with detail mentioning **`administrator Bearer`** when hitting:

- `/api/e2e/dev/mock-llm/configure`
- `/api/e2e/dev/grading-state`
- `/api/e2e/dev/process-grading`
- `/api/e2e/dev/worker`
- `/api/e2e/dev/mark-preset-validated`

even though **`X-E2E-Seed-Token`** is correct.

### Context

The seed token alone proves possession of a shared CI secret; it does **not** prove an interactive admin session. When **`settings.E2E_DEV_REQUIRE_ADMIN_JWT`** is **true**, selected routes require **`Authorization: Bearer <admin JWT>`** in addition to the seed header. **`reset-scenario`** stays seed-only so **`globalSetup`** can run before any login.

Playwright stores the post-reset admin token in **`process.env.E2E_DEV_ADMIN_BEARER`** via **`tests/e2e/web-admin/e2e-seed-headers.cjs`** (`refreshE2eAdminBearer`). Specs that duplicate **`seedHeaders()`** locally must either import **`seedHeaders`** from **`e2e-seed-headers.cjs`** or duplicate the merge logic.

### Fix

- Managed Playwright: rely on **`fixtures.cjs`** / **`global-setup.cjs`** (they refresh the bearer after each seed).
- External API without Playwright env: login as seeded **`admin`** from **`scenario.json`** and pass **`Authorization`** with **`POST /api/e2e/dev/*`** calls.
- Opt out only for intentional legacy scripts: **`E2E_DEV_REQUIRE_ADMIN_JWT=false`** on the backend process.

### Interpretation

This pitfall appeared while closing **P0 E2E exposure** findings: misconfigured non-production hosts previously allowed powerful actions with only a static seed header.

### Pitfall 57: Default `SECRET_KEY` placeholder remains valid unless production or `REQUIRE_STRONG_SECRETS`

### Symptom

Operators expect **`SECRET_KEY=change-me-in-production`** to fail fast in **all** environments; instead the app starts when **`APP_ENV`** is not production-style **and** **`REQUIRE_STRONG_SECRETS`** is **false** (the default), because **`reject_weak_secrets_in_production`** only forces strong secrets when **`REQUIRE_STRONG_SECRETS` or production APP_ENV**.

### Context

Changing **`REQUIRE_STRONG_SECRETS`** default to **`true`** breaks **`from apps.backend.wailearning_backend.core.config import settings`** for processes that have **no** `.env` and rely on code defaults — pytest/conftest sets **`SECRET_KEY`** explicitly, but bare **`python -m uvicorn`** without env would crash unless operators create secrets first.

### Fix

Deployments must set **`APP_ENV=production`** (or **`REQUIRE_STRONG_SECRETS=true`**) **and** supply **`SECRET_KEY`** / **`DATABASE_URL`** per **`docs/operations/DEPLOYMENT_AND_OPERATIONS.md`**. Treat **`change-me-in-production`** as invalid anywhere tokens matter.

### Interpretation

This documents **P0 weak-default-key** risk without silently breaking developer **`import settings`** ergonomics.

### Pitfall 56: Attachment download by basename — ambiguous collision returns **400** (not 403)

### Symptom

`GET /api/files/download/<stored_basename>` returns **400** with text about passing **`attachment_url`**, where the same lesson previously returned **403** (“Ambiguous attachment reference…”).

### Context

Multiple logical **`attachment_url`** rows can reference the same on-disk name. Returning **403** misclassified “caller knows basename but DB has multiple logical URLs” as purely forbidden; **400** invites passing the canonical **`attachment_url`** query parameter to disambiguate after ACL checks.

### Fix

Clients that deep-link **`/api/files/download/{name}`** without a query parameter must tolerate **400** when collisions exist; prefer **`GET /api/files/download?attachment_url=...`** (already supported) or pass **`?attachment_url=`** on the basename route.

### Interpretation

**`tests/backend/files/test_files_attachment_download.py`** still expects **200** when the teacher has access and either there is a single matching URL or paths coincide.

### Pitfall 58: `ensure_course_access` raised `ValueError` inside FastAPI routes (500 instead of 404)

### Symptom

Calling course-scoped endpoints with a non-existent **`subject_id`** returned **500 Internal Server Error** because **`ensure_course_access`** calls **`get_course_or_404`**, which raises **`ValueError("Course not found.")`** — uncaught in many routers.

### Context

Only some handlers wrapped **`try/except ValueError`**. Others assumed **`ensure_course_access`** only raised **`PermissionError`**.

### Fix

**`ensure_course_access_http`** (in **`apps/backend/wailearning_backend/domains/courses/access.py`**) now maps **`ValueError`** to HTTP **404** and **`PermissionError`** to **403**. Route modules were migrated to call **`ensure_course_access_http`** instead of **`ensure_course_access`** for HTTP endpoints (**`homework.py`**, **`scores.py`**, **`attendance.py`**, **`dashboard.py`**, **`subjects.py`**, **`llm_settings.py`**, **`files.py`** attachment ACL helper).

### Interpretation

Regression guard: unknown course IDs must never surface as **500** for authenticated callers.

### Pitfall 59: Homework **`class_id`** vs course **`Subject.class_id`** mismatch

### Symptom

Corrupt rows where **`Homework.class_id`** references class A but **`Homework.subject_id`** points at a **`Subject`** owned by class B caused confusing auth: **`ensure_course_access`** could return **404** (“course not in accessible list”) after the user already passed class-level homework checks.

### Context

Multi-column inconsistency is an administrator/data-import defect; students should not see **404** suggesting “wrong roster” when the real issue is inconsistent homework wiring.

### Fix

**`_ensure_homework_access`** compares **`Subject.class_id`** to **`Homework.class_id`** when both are set and returns **403** with an explicit **data integrity** message before calling **`ensure_course_access_http`**.

### Interpretation

Covered by **`tests/backend/homework/test_homework_course_class_integrity.py`** (admin sees integrity **403**; student is blocked **403**).

### Pitfall 60: `POST /api/auth/forgot-password` spam and throttle semantics

### Symptom

Repeated forgot-password requests for the same username flood **`notifications`** rows for administrators; scripted clients can also hammer the endpoint from one IP.

### Context

The endpoint intentionally returns the **same generic message** for missing accounts (anti-enumeration). Throttling must therefore avoid leaking “account exists” via different HTTP codes — skipped work still returns the canonical success body.

### Fix

- **`FORGOT_PASSWORD_USERNAME_COOLDOWN_SECONDS`** (default **600**): suppresses a **new** admin notification if another **`password_reset_request`** notification for the same titled user was created within the window. A **`operation_logs`** row with **`result=cooldown`** records the skip (no notification row).
- **`FORGOT_PASSWORD_MAX_REQUESTS_PER_IP_PER_HOUR`** (default **40**): counts **`operation_logs`** rows with **`action=forgot_password_request`** per IP in the rolling hour; when over budget, skip notification creation and log **`result=rate_limited`**.

Disable by setting **`FORGOT_PASSWORD_USERNAME_COOLDOWN_SECONDS=0`** and/or **`FORGOT_PASSWORD_MAX_REQUESTS_PER_IP_PER_HOUR=0`** (zero disables that gate).

### Interpretation

**`tests/backend/auth/test_forgot_password_flow.py`** still expects the first successful path unchanged; add parallel tests if you tighten defaults further.

### Pitfall 61: Public registration with invented **`class_id`**

### Symptom

With **`ALLOW_PUBLIC_REGISTRATION=true`**, **`POST /api/auth/register`** accepted arbitrary **`class_id`** values, creating student accounts pointing at non-existent **`classes`** rows (orphan **`users.class_id`**).

### Fix

When **`PUBLIC_REGISTRATION_VALIDATE_CLASS_EXISTS`** is **true** (default), **`register`** queries **`classes`** and returns **400** with **`Invalid class_id: class does not exist.`** if missing.

### Interpretation

**`tests/backend/auth/test_public_registration_validation.py`** asserts rejection for a synthetic ID; **`tests/backend/courses/test_student_course_roster_behavior.py::test_public_register_student_then_roster_same_username_gets_enrollments`** still uses a real class from the scenario.

### Pitfall 62: Student LLM quota GET endpoint creating **`CourseLLMConfig`** rows

### Symptom

**`GET /api/llm-settings/courses/student-quota/{subject_id}`** called **`ensure_course_llm_config`**, which inserts **`course_llm_configs`** and may sync template endpoints — an unintended **write** side effect for a read-only quota view.

### Fix

After **`ensure_course_access_http`**, build usage via **`get_student_quota_usage_snapshot(db, None, student_id=..., subject_id=...)`** (extended signature in **`domains/llm/quota.py`**) without initializing course LLM config.

**`GET /api/llm-settings/courses/student-quotas`** no longer calls **`ensure_course_llm_config`** per enrollment row (read-only aggregation).

### Interpretation

Teachers still invoke **`ensure_course_llm_config`** through **`GET/PUT /api/llm-settings/courses/{subject_id}`** when editing LLM settings — that path intentionally creates/configures rows.

### Pitfall 63: Stale `node` / `uvicorn` on default E2E ports after interrupted full run

### Symptom

`npm run test:e2e` aborts before tests start:

```text
Error: http://127.0.0.1:3012/ is already used
Error: http://127.0.0.1:8012/api/health is already used
```

### Context

Playwright `webServer` in **`apps/web/admin/playwright.config.cjs`** tries to bind **Vite** and **uvicorn**. A killed CLI may leave the child **`node`** (Vite) or Python server alive; **`fuser`** may be missing in the image.

### Fix

**`lsof -i :<E2E_UI_PORT>`** and **`lsof -i :<E2E_API_PORT>`** then **`kill -9`**, or use **`PLAYWRIGHT_USE_EXTERNAL_SERVERS=1`** and manage processes explicitly.

### Interpretation

This is an **operator / environment** failure, not a test assertion failure. Documented in [FULL_PLAYWRIGHT_E2E_RUNBOOK.md](FULL_PLAYWRIGHT_E2E_RUNBOOK.md) as runbook **Pitfall 63** (mirrors this pitfall number for cross-linking).

### Pitfall 64: `header-course-switch` — hover-based Element Plus dropdown vs Playwright click

### Symptom

**`e2e-notification-header-sync-tier.spec.js`** / **`e2e-notification-sync-deep-tier.spec.js`**: timeout on **`.course-dropdown-menu`** click — “element is not visible / not stable”.

### Context

**`el-dropdown` `trigger="hover"`** + teleported menu: **`hover()` + getByText** on nested **`<strong>`** is fragile; **`scrollIntoViewIfNeeded`** on an animating popper can block until test timeout.

### Fix

**`clickCourseSwitcherOption`** in **`tests/e2e/web-admin/future-advanced-coverage-helpers.cjs`**: click **切换课程**, visible **`.course-dropdown-menu`**, **force** click **`.course-option`**.

### Pitfall 65: Mock LLM `discuss_<suffix>` profile cursor drift in full Playwright run

### Symptom

**`e2e-homework-comment-cover-tier4.spec.js`** case **08** — **`expect.poll` on `comment_preview`** never contains **`复`**, value stays **`discuss_<hex>:ok`**.

### Context

**`/api/e2e/dev/mock-llm/<profile>/v1/chat/completions`** advances a **per-profile cursor** in **`e2e_dev.py`**. Other specs (discussion LLM, validation) and ordering can exhaust **`steps`** so the handler falls back to default **`{profile}:ok`**.

### Fix

After the first graded comment is confirmed, **`configureMockLlm`** again with **only** the step intended for the **regrade** attempt.

### Interpretation

Same numbered narrative as **FULL_PLAYWRIGHT_E2E_RUNBOOK.md** sections **Pitfall 64–65** (course switcher vs mock cursor).

### Pitfall 66: Tier-4 chapter reorder — wrong HTTP verb / payload vs tree shape

### Symptom

**`tests/e2e/web-admin/e2e-tier4-stress-backlog.spec.js`** case **13**: **`movable.length >= 2`** fails at **1**, or reorder returns **405/422** after fixing counts.

### Context

1. **`GET /api/material-chapters/tree`** returns a **nested** tree. Filtering **`tree.nodes`** only counts **root-level** rows. A single extra **`CourseMaterialChapter`** inserted as a **child** under another chapter still yields **one** movable root sibling alongside **未分类**.
2. Reorder is **`POST /api/material-chapters/reorder?subject_id=...`** with JSON **`{ parent_id: null, ordered_chapter_ids: [...] }`** — not **`PUT`**, and not **`chapter_ids`** (see **`material_chapters.py`**).

### Fix

- Seed **two non-uncategorized root chapters** (`parent_id=None`) for the required course in **`e2e_dev.py`** so **`nodes.filter(!is_uncategorized)`** has **≥ 2** entries at the root.
- Call **`apiPostJson`** with **`ordered_chapter_ids`**, matching the SPA client (**`apps/web/admin/src/api/index.js`** → **`reorderChapters`**).

### Interpretation

When authoring chapter reorder specs, align with **`CourseMaterialChapterReorderRequest`** in **`apps/backend/.../schemas.py`** and prefer **`flattenChapterTree`** from **`future-advanced-coverage-helpers.cjs`** if you must include nested chapters.

### Pitfall 67: Responsive E2E — **`boundingBox()`** over huge **`catalog-mobile-item`** lists times out

### Symptom

**`ui-responsive-layout-regression.spec.js`** — **`mobile course cards and catalog cards stay inside a 390px viewport`** exceeds **120s** while **`waiting for locator('.catalog-mobile-item').nth(N)`** with **N** in the hundreds.

### Context

The elective catalog can return **many** rows in smoke databases. **`expectLocatorBoxesWithinViewport`** previously iterated **every** match; each **`boundingBox()`** forces layout work — **O(n)** becomes prohibitive.

### Fix

Cap sampled rows (**first `maxItems`**) and rely on **`expectNoPageHorizontalOverflow`** for the global **`scrollWidth`** invariant.

### Pitfall 68: Users-page **`tbody tr`** + **`batch-set-class`** UI vs accumulated SQLite user rows

### Symptom

**`e2e-scenario-resilience.spec.js`** (`student mid-session class migration`, `stale roster dialog…`) times out on **`expect(tr).toBeVisible`** or on **`batch-class`** dropdown option clicks after many full Playwright runs against the **same file-backed SQLite** (`<E2E_SQLITE>` in **`FULL_PLAYWRIGHT_E2E_RUNBOOK.md`**).

### Context

**`/users`** loads **all** users (`GET /api/users` returns `query.all()`). **`reset-scenario`** does not truncate unrelated historical rows; **local E2E user counts grow**. **`getByRole('row', { name: … })`** on **`el-table`** can also miss when the accessible **name** does not include the username column text.

### Fix

- Prefer **`POST /api/users/batch-set-class`** from the test harness when the scenario only needs **authoritative class migration + enrollment sync**, not **batch-class dialog UX**.
- When asserting presence on **`Users.vue`**, use **`locator('tbody tr').filter({ hasText: username })`** instead of **`getByRole('row', { name: regex })`**.
- **`boundary: admin creates a new student`** now creates via **`POST /api/users`** then verifies the **table row** — avoids **`el-select`** teleport edge cases under heavy lists.

### Pitfall 69: E2E assertions vs **`prepare_student_course_context`** and inconsistent **`page_size`** caps across routers

### Symptom

Authoring **`tests/e2e/web-admin/e2e-docs-gap-tier15.spec.js`** (or similar API-heavy specs):

1. **`student_b`** “not enrolled in required course” — **`GET /api/homeworks/{id}/submission/me`** unexpectedly returns **200** because **`prepare_student_course_context`** + **`sync_student_course_enrollments`** auto-create **`CourseEnrollment`** for **all** students in the class when the required-course sync runs — **待人工确认** whether treating every roster student as implicitly enrolled is intended product-wise.

2. Cross-class homework submission expectation **`404`** from **`_resolve_student_for_user`** sometimes yields **`403`** instead because **`_ensure_homework_access`** runs **`ensure_course_access_http`** first; students enrolled only elsewhere hit **`PermissionError`** (**403**) before roster mismatch (**404**).

3. **`GET /api/scores/appeals`** has **no `page_size` query parameter** — FastAPI ignores unknown query keys; **`page_size=5000`** returns **200** with the router's fixed **`limit(200)`** behavior. Tests that expect **422** from oversized **`page_size`** must target a route that actually declares **`Query(..., le=...)`** (for example **`GET /api/students`** uses **`le=1000`**).

4. Same-class students may **`GET /api/points/students/{other_student_id}`** without **403** when both share a **`class_id`** — privacy expectations must not assume “student cannot read peer points” unless product explicitly forbids it (**待人工确认**).

### Fix

- Prefer **explicit cross-class homework rows** (admin-created **`Homework`** with **`class_id`** / **`subject_id`** pointing at **`course_other_teacher_id`** + **`class_id_2`**) when testing “wrong class” submission denial.
- Accept **`[403, 404]`** where course-access vs roster-order differs.
- Validate pagination bounds only against routers that validate **`page_size`** in **`Query`** — grep **`apps/backend/wailearning_backend/api/routers/*.py`** before writing **`422`** expectations.

### Interpretation

Documentation that says “enrollment must exist” should mention **class-wide required-course sync** on student requests, or new readers (and agents) will mis-design tests and false-positive “bugs”.

### Pitfall 70: **`ElMessageBox.confirm`** vs **`el-dialog`** — wrong overlay target after long SQLite runs

### Symptom

**`tests/e2e/web-admin/e2e-pitfall-guard-rails.spec.js`** case **01**, **`e2e-scenario-boundary-dynamic-complex.spec.js`** delete path, **`future-advanced-coverage.spec.js`** case **3**, **`e2e-scenario-resilience.spec.js`** batch-class paths:

- `waitForResponse` on **`DELETE /api/subjects/:id`** times out,
- or `getByRole('dialog').filter({ has: button OK })` clicks the **wrong** overlay,
- or Playwright waits until **test timeout** (~300s) while the **MessageBox** never receives the intended click.

### Context

Element Plus **`ElMessageBox.confirm`** renders a **teleported** small modal with class **`el-message-box`**, not the same accessibility tree as large **`el-dialog`** course forms. After hundreds of seeds, **multiple** hidden `.el-select-dropdown` nodes and **stacked** overlays can exist; targeting **“last dialog”** is ambiguous.

### Fix

Use a **MessageBox-scoped** primary button:

- helper **`confirmElMessageBoxPrimary`** in **`tests/e2e/web-admin/future-advanced-coverage-helpers.cjs`** — waits for **`.el-message-box`** then clicks **`.el-message-box__btns .el-button--primary`**.

### Interpretation

Do not assert delete flows by title **`删除课程`** alone — pair **network** assertions with the **MessageBox** button actually wired to **`ElMessageBox.confirm`**.

### Pitfall 71: **`el-select-dropdown`** — many nodes stay **`hidden`** in DOM; prefer **visible** scoping

### Symptom

**`e2e-scenario-boundary-dynamic-complex.spec.js`** — `clickSelectOptionByLabel` waits forever on **`.el-select-dropdown.last()`** where the last node is **always hidden** (teleported popper retain).

### Fix

Use **`.filter({ visible: true })`**, wait for **visible** popper after opening the trigger, or **avoid UI selects entirely** for setup — e.g. **`POST /api/subjects`** with **`SubjectCreate`** for course rows when the test goal is **delete / list consistency**, not **form layout**.

### Pitfall 72: Roster-enroll UI assumes **`student_b`** is **not** already in the required course

### Symptom

**`roster-and-users.spec.js`** — checkbox stays disabled / no **`POST .../roster-enroll`**.

### Context

**`sync_course_enrollments`** (bootstrap + course writes) can enroll **all** class roster students into **required** courses. **`student_b`** is often already **`已在课`**, and **`el-table`** selection is **`selectable: row => !row._enrolled`**.

### Fix

Before opening **从花名册进课**, **`DELETE /api/subjects/{course_required_id}/students/{student_row_id}`** as admin (ignore **404**) so the row returns to **未在课** for the UI assertion.

### Pitfall 73: **Batch调班** — enable **`users-open-batch-class`** before open; optional filter on **`filterable`** `el-select`

### Symptom

**`dialog-batch-class`** never appears — **`users-open-batch-class`** stays disabled because **no row selected** in a huge **`/users`** table.

### Fix

**`scrollIntoViewIfNeeded`** on the **`tr`**, then **`expect(users-open-batch-class).toBeEnabled`**, then open dialog; pick target class via **visible** dropdown + **`getByRole('option')`** (filter input is **optional** — may not exist in all EP builds).

### Pitfall: system-wide student quota totals are repeated on course attribution rows

Symptom:

```text
assert used_b1 == used_b0
E       assert 10 == 0
```

Context:

A behavior test submitted homework in course A, then read the
`/api/llm-settings/courses/student-quotas` summary and expected the course B row
to keep `student_used_tokens_today` unchanged.

Cause:

After quota consolidation, `student_used_tokens_today` is the student's
system-wide daily LLM usage total. It is intentionally repeated on every course
row so each row can show the same daily pool context. The per-course field is
`course_used_tokens_today`; that field is the attribution value that should stay
unchanged for a course that did not receive new usage.

Fix:

When testing the post-consolidation model, assert both sides explicitly:

```text
course A row student_used_tokens_today == course B row student_used_tokens_today
course A row course_used_tokens_today increased
course B row course_used_tokens_today did not change
```

Interpretation:

This failure is not evidence that course attribution broke. It is evidence that
the old per-course-pool mental model leaked into a test assertion.

### Pitfall: Element Plus switch test id may be on the wrapper, not the role element

Symptom:

```text
expect(locator).toHaveAttribute("aria-checked", "false")
Received: ""
locator resolved to <div class="el-switch" data-testid="...">...</div>
```

Cause:

Element Plus can render the `data-testid` on the switch wrapper while the
actual accessible switch state lives on the nested element with `role="switch"`.
The wrapper is useful for clicking, but it may not carry `aria-checked`.

Fix:

Click the stable test id if that is the most convenient target, then assert on
the role locator inside the same dialog or component:

```text
const enableSwitch = dialog.getByRole('switch')
await page.getByTestId('llm-course-enable').click()
await expect(enableSwitch).toHaveAttribute('aria-checked', 'false')
```

Interpretation:

This is a selector issue in the test, not evidence that the UI failed to toggle.

### Pitfall: parallel Playwright commands can reset local E2E backend fetches

Symptom:

```text
TypeError: fetch failed
[cause]: Error: read ECONNRESET
```

Context:

Two separate Playwright CLI commands were started at the same time from
`<repo>/apps/web/admin`, both using the default admin Playwright config.

Relevant config shape:

```text
E2E_API_PORT defaults to 8012
E2E_UI_PORT defaults to 3012
DATABASE_URL defaults to a temp SQLite file keyed by E2E_API_PORT
webServer starts FastAPI at http://127.0.0.1:8012
webServer starts Vite at http://127.0.0.1:3012
```

Cause:

The two CLI processes share the same default local ports and temp SQLite file.
One process can reset/restart/tear down the backend while the other process is
performing a Node-side `fetch(...)` against the local API. The resulting error
is a local backend/webServer connection reset. It is not evidence of Codex
platform high demand, and it is not evidence that a real external LLM provider
was called.

How to identify the target:

For the admin Playwright config, helper `apiBase()` resolves to:

```text
http://127.0.0.1:<E2E_API_PORT>
```

The affected LLM hard-scenario tests create presets with mock base URLs such as:

```text
http://127.0.0.1:<E2E_API_PORT>/api/e2e/dev/mock-llm/<profile>/v1/
```

Therefore a `fetch failed` in those helpers should first be investigated as a
local backend/webServer issue unless the stack trace or preset data shows a
non-localhost URL.

Fix:

Prefer one Playwright CLI process at a time when using the default local
webServer config. If parallel CLI processes are required, give each process its
own ports and isolated database, for example:

```text
E2E_API_PORT=8013 E2E_UI_PORT=3013 npx playwright test ...
E2E_API_PORT=8014 E2E_UI_PORT=3014 npx playwright test ...
```

On Windows PowerShell use separate `$env:` assignments in the same command
session before invoking Playwright. Keep `NO_PROXY=localhost,127.0.0.1,::1` when
a local HTTP proxy is configured so localhost E2E traffic does not leave the
machine.

Interpretation:

If the same test passes when rerun serially with the same code and local mock
LLM endpoint, treat the earlier `ECONNRESET` as local E2E orchestration
contention rather than product behavior.

- It does not claim the product code is bug-free.
- It does not claim all Windows environments need the exact same workarounds.
- It does not claim the sandbox restrictions seen here will match CI or a developer's normal terminal.
- It does not claim Linux agents exhibit only the Linux-specific pitfalls above; many Windows pitfalls (ports, readiness, flake in long suites) still apply cross-platform.

It records what actually happened during validation sessions (starting with the May 1, 2026 Windows-focused pass, extended by later Linux/CI observations) so the next operator can start from firmer ground.
