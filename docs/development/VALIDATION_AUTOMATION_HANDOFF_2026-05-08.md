# Homework Table Button Layout Handoff - 2026-05-08

This handoff replaces the previous validation automation handoff content for the
current branch. The active follow-up is the admin homework list action layout.

## Branch And Context

- Worktree: `cursor/discussion-avatar-chat-ui-921d`
- Branch: `cursor/discussion-avatar-chat-ui-921d`
- The user provided a screenshot showing the homework list action buttons in the
  admin SPA. The `查看` and `删除` buttons were visibly clipped inside the
  `操作` column.
- `.agent-run/` is local-only and ignored. Do not commit screenshots, logs, or
  other local evidence from that directory.

## User-Visible Problem

The admin homework table in `apps/web/admin/src/views/Homework.vue` rendered the
action buttons too tightly. In the screenshot:

- the `查看` button label was clipped on the right;
- the `删除` button label was clipped on the right;
- the action area looked cramped and unstable inside the table cell.

The issue is in the table layout and button spacing, not in homework routing or
the underlying API.

## Relevant Files

- `apps/web/admin/src/views/Homework.vue`
  - Owns the homework list table, action column, and table-level spacing.
- `tests/TEST_SELECTION_TARGETS.json`
  - Registry already maps this view to `frontend.admin.build` and the
    homework-related Playwright tier.
- `docs/development/TEST_EXECUTION_LEDGER.md`
  - Execution record for the build and validation steps used in this pass.
- `AGENTS.md`
  - Updated with the change-scoped validation rule requested by the user.

## Fix Implemented

`apps/web/admin/src/views/Homework.vue` was updated in three places:

1. The `操作` column width increased from `280` to `340` for staff rows and
   from `200` to `220` for student rows.
2. The table's minimum width increased from `1060px` to `1160px` to reduce
   pressure on the right-side columns.
3. The action button container now neutralizes the default adjacent button
   margin and gives each button a stable `min-width` and padding, so the labels
   remain fully visible.

These changes keep the action area readable without changing behavior or route
flow.

## Validation Policy Update

`AGENTS.md` now includes a rule stating that, unless the user explicitly asks
for a broader validation level, verification should stay change-scoped:

- run the diff selector first;
- run only the relevant static/targeted targets by default;
- treat `needs_review` and `not_sufficient` as explicit review points;
- do not use the default rule to ignore unmatched paths or high-risk gaps.

That rule is intentionally written to support incremental validation, not to
justify under-testing.

## Validation Performed

1. `select_validation_targets.py --worktree`
   - Result: `needs_review`
   - Relevant targets found:
     - `static.encoding_text_tools`
     - `frontend.admin.build`
     - `admin.e2e.homework_comment_cover_tier4`
   - No unmatched paths.
2. `python -m py_compile` / selector smoke / local selector history checks
   - Already completed in the current branch history and reflected in the
     execution ledger.
3. `npm.cmd install` in `apps/web/admin`
   - Required because the local admin package did not yet have `vite` available.
4. `npm.cmd run build`
   - Passed after install.
5. `npx.cmd playwright test e2e-homework-comment-cover-tier4.spec.js --project=chromium`
   - Blocked before browser assertions because the repository `.venv` is missing
     `uvicorn`:
     `No module named uvicorn`

## Important Environment Note

The Playwright attempt did not reach product assertions. It failed while the
managed backend process was starting. That means the browser test result is an
environment block, not a regression verdict on the homework layout.

## Notes For Next Agent

- Stay on `cursor/discussion-avatar-chat-ui-921d`.
- Do not reuse the previous LaTeX copy/rendering handoff as if it still matches
  the current task; it has been replaced with this homework layout context.
- If you need browser verification for the homework action buttons, install or
  provision the missing backend dependency in `.venv` first so Playwright can
  start `uvicorn`.
- The build is already green, and the validation ledger has been updated with
  the observed result.

## Validation Infrastructure Follow-up

The Playwright blocker from the previous section was reproduced and narrowed:

- `npx.cmd playwright test --list` worked from `apps/web/admin`, so Node,
  Playwright discovery, and `playwright.config.cjs` were not the blocker.
- The repository `.venv` existed but initially had no backend packages; both
  `.venv\Scripts\python.exe` and system `python` failed to import `uvicorn`.
- The host only exposed Python 3.14. The pinned `requirements.txt` set cannot be
  installed unchanged on that interpreter because `pydantic==2.5.3` requires
  `pydantic-core==2.14.6`, which has no Python 3.14 wheel, and
  `psycopg2-binary==2.9.9` falls back to a source build requiring `pg_config`.
- For local Playwright-on-SQLite validation, the `.venv` was populated with
  Python-3.14-compatible backend wheels and `bcrypt` was explicitly restored to
  the repository-pinned `bcrypt==4.0.1`. `bcrypt==5.0.0` is incompatible with
  `passlib==1.7.4` for the long E2E seed passwords and caused
  `reset-scenario` to return 500.

The reusable runner behavior was improved:

- `ops/scripts/dev/run_validation_target.py` now runs
  `ops/scripts/dev/playwright_preflight.py --json` before any
  `category: admin-playwright` target.
- Failed Playwright preflight is classified as `blocked` with
  `failure_class=environment`, so missing `.venv`, missing backend imports, or
  occupied ports do not get recorded as product failures.
- Playwright `spawn EPERM` is also classified as an environment block. In this
  Windows sandbox, direct Playwright execution needs the approved/elevated
  command path because it launches uvicorn, Vite, and Chromium child processes.
- Runner JSON is written to stdout as UTF-8 bytes, avoiding GBK console crashes
  when captured logs contain replacement characters.

Useful commands after this follow-up:

```powershell
.\.venv\Scripts\python.exe ops\scripts\dev\playwright_preflight.py --json
.\.venv\Scripts\python.exe ops\scripts\dev\run_validation_target.py admin.e2e.core_flows_smoke --timeout-seconds 180
```

Validation performed for the infrastructure follow-up:

1. `.\.venv\Scripts\python.exe -m py_compile ops\scripts\dev\run_validation_target.py tests\backend\manual\test_validation_selector.py`
   - Passed.
2. `.\.venv\Scripts\python.exe -m unittest tests.backend.manual.test_validation_selector -v`
   - Passed: `17` tests.
3. `.\.venv\Scripts\python.exe ops\scripts\dev\playwright_preflight.py --json`
   - Passed: admin root, config, Vite, Node/npm/npx, E2E Python, backend imports,
     and ports `8012`/`3012`.
4. `npx.cmd playwright test e2e-core-flows-smoke.spec.js --project=chromium`
   - Passed twice after dependency setup: `10 passed`.
5. `.\.venv\Scripts\python.exe ops\scripts\dev\run_validation_target.py admin.e2e.core_flows_smoke --timeout-seconds 180`
   - Passed through the new runner path: preflight passed, then Playwright
     smoke passed with `10 passed`.

Open environment note:

- The durable fix is still to use a Python version compatible with
  `requirements.txt` pins, such as Python 3.11/3.12, for release-like local
  validation. Chocolatey installation of `python312` was attempted but blocked
  by local Chocolatey lock/permission errors under `C:\ProgramData\chocolatey`.
  The current `.venv` is sufficient for SQLite-backed Playwright smoke on this
  machine, but it is not a proof that the old pinned dependency set installs on
  Python 3.14.
