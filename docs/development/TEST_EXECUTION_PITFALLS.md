# Test Execution Pitfalls

## Purpose

This document records pitfalls encountered while executing the repository test suites on Windows + PowerShell during the repository-structure refactor completed on May 1, 2026. The focus here is the tester environment, test runner behavior, and execution workflow friction, not product-code bugs.

Later passes (same overall repository layout) added Linux / CI / cloud-agent notes and Playwright selector pitfalls discovered while fixing false failures. Those additions are additive: they do not replace the Windows-focused guidance above.

This file is meant to save future test operators from rediscovering the same issues.

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
  - `apps/backend/app/`
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

## What This Document Does Not Claim

- It does not claim the product code is bug-free.
- It does not claim all Windows environments need the exact same workarounds.
- It does not claim the sandbox restrictions seen here will match CI or a developer's normal terminal.
- It does not claim Linux agents exhibit only the Linux-specific pitfalls above; many Windows pitfalls (ports, readiness, flake in long suites) still apply cross-platform.

It records what actually happened during validation sessions (starting with the May 1, 2026 Windows-focused pass, extended by later Linux/CI observations) so the next operator can start from firmer ground.
