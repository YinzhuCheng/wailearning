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

## Validation Infrastructure First-Round Guardrails

The first follow-up round converted the Playwright lessons above into preflight
checks and committed documentation guidance.

`ops/scripts/dev/playwright_preflight.py` now checks more than the shallow
backend startup imports:

- `python-version` records the selected `E2E_PYTHON` version. Python 3.14 is
  allowed for local smoke only when dependencies are already installed, and the
  detail explicitly tells operators to prefer Python 3.11/3.12 for release-like
  validation.
- `requirements-python-compat` surfaces the known Python-3.14 install risk from
  current pins (`pydantic==2.5.3` / `pydantic-core==2.14.6`, and
  `psycopg2-binary==2.9.9`).
- `backend-imports` now covers modules needed by startup and seed routes:
  `uvicorn`, `fastapi`, `sqlalchemy`, `pydantic`, `pydantic_settings`, `jose`,
  `passlib`, `multipart`, and `httpx`.
- `password-hash-smoke` hashes a seed-style password with `passlib` + `bcrypt`
  so the `bcrypt==5.0.0` / `passlib==1.7.4` reset-scenario 500 class is caught
  before Playwright launches.
- `playwright-sqlite` reports whether the default SQLite file for
  `E2E_API_PORT` already exists. It does not fail the run by itself; it makes
  persistent local state visible during triage.

The Node diagnostic test in
`tests/frontend/admin/markdown_latex_and_clipboard.test.mjs` now forces a
missing `E2E_PYTHON` path and asserts structured failures for `e2e-python`,
`python-version`, `requirements-python-compat`, `backend-imports`, and
`password-hash-smoke`. This keeps the test deterministic even when the current
worktree has a valid `.venv`.

Docs updated in this round:

- `docs/development/TEST_EXECUTION_PITFALLS.md` records the Python 3.14 pin
  risk, bcrypt/passlib seed hashing failure, and leftover Playwright SQLite
  artifact as one operational cluster.
- `docs/development/FULL_PLAYWRIGHT_E2E_RUNBOOK.md` now makes
  `playwright_preflight.py --json` a managed-webServer prerequisite and explains
  how to interpret hash-smoke and Python-version results.

Validation performed for this first guardrail round:

1. `.\.venv\Scripts\python.exe -m py_compile ops\scripts\dev\playwright_preflight.py`
   - Passed.
2. `.\.venv\Scripts\python.exe ops\scripts\dev\playwright_preflight.py --json`
   - Passed with `exit_code: 0`; the current host reports Python `3.14.4`,
     known pin-risk details, successful backend imports, successful
     `password-hash-smoke`, and an existing default Playwright SQLite file.
3. `node --test tests\frontend\admin\markdown_latex_and_clipboard.test.mjs`
   - Passed: `10` tests.
4. `git diff --check`
   - Passed.

## Validation Infrastructure Second-Round Reflection

The second follow-up round did not add more runner behavior. It reviewed the
current selector, target runner, profile runner, preflight, local JSONL history,
and committed ledger boundaries, then captured the outcome in:

- `docs/development/VALIDATION_INFRASTRUCTURE_REVIEW_2026-05-08.md`

Main conclusion:

- The current validation infrastructure is useful and should stay
  change-scoped by default.
- The main risk is now result ambiguity, not the absence of a selector. Agents
  can still overclaim when a profile run passes only the cheap subset while
  review-required, broad, full, skipped, or blocked targets remain unresolved.
- Third-round work should prioritize making those states harder to misread,
  especially `needs_review` profile output, unresolved command placeholders,
  registry linting, and Playwright machine-readable result artifacts.

Validation performed for the second reflection round:

1. `.\.venv\Scripts\python.exe ops\scripts\dev\select_validation_targets.py --worktree --json`
   - Passed; reported `non_full_validation.status=acceptable` and
     `unmatched_paths=[]`.
2. `python -m json.tool tests\TEST_SELECTION_TARGETS.json`
   - Passed.
3. `.\.venv\Scripts\python.exe -m py_compile ops\scripts\dev\playwright_preflight.py`
   - Passed.
4. `node --test tests\frontend\admin\markdown_latex_and_clipboard.test.mjs`
   - Passed: `10` tests.
5. `.\.venv\Scripts\python.exe ops\scripts\dev\playwright_preflight.py --json`
   - Passed with `exit_code: 0`.
6. `.\.venv\Scripts\python.exe ops\scripts\dev\run_validation_target.py static.validation_selector --timeout-seconds 120`
   - Passed.
7. `.\.venv\Scripts\python.exe ops\scripts\dev\check_text_encoding.py <changed files>`
   - Passed: `scanned=7 decode_errors=0 suspicious=0`.
8. `git diff --check`
   - Passed.

Important second-round observation:

- `static.encoding_text_tools` is still not fully self-service because its
  registry command uses `<changed-text-files>`. The manual explicit-file
  encoding scan above was used for this round. Removing that placeholder trap
  is a high-priority third-round code change.

## Validation Infrastructure Third-Round Automation

The third follow-up round converted the highest-priority reflection items into
code and policy.

Implemented guardrails:

- `ops/scripts/dev/run_validation_profile.py`
  - returns `result=passed_with_deferred_review` when executed targets pass but
    review-required targets were skipped by policy;
  - includes `deferred_targets` in profile JSON so final handoffs can name what
    remains unresolved instead of saying plain "passed".
- `ops/scripts/dev/run_validation_target.py`
  - expands `<changed-text-files>` from the current worktree changed-path
    snapshot before command execution;
  - excludes deleted files and non-text files from that expansion.
- `ops/scripts/dev/check_text_encoding.py`
  - supports `--skip-if-empty`, allowing placeholder expansion to produce an
    intentional zero-file scan instead of falling back to all tracked files.
- `tests/TEST_SELECTION_TARGETS.json`
  - updated `static.encoding_text_tools` to use `--skip-if-empty
    <changed-text-files>`.
- `tests/backend/manual/test_validation_selector.py`
  - covers placeholder expansion, empty encoding-scan behavior, and
    `passed_with_deferred_review` profile output.
- `AGENTS.md`
  - now states that repeatable pitfalls should be converted into executable
    guardrails when practical: preflight checks, selector/runner rules, lint
    scripts, tests, registry entries, or CI/profile steps.

Validation performed for the third automation round:

1. `.\.venv\Scripts\python.exe -m py_compile ops\scripts\dev\check_text_encoding.py ops\scripts\dev\run_validation_target.py ops\scripts\dev\run_validation_profile.py tests\backend\manual\test_validation_selector.py ops\scripts\dev\playwright_preflight.py`
   - Passed.
2. `python -m json.tool tests\TEST_SELECTION_TARGETS.json`
   - Passed.
3. `.\.venv\Scripts\python.exe -m unittest tests.backend.manual.test_validation_selector -v`
   - Passed: `19` tests.
4. `node --test tests\frontend\admin\markdown_latex_and_clipboard.test.mjs`
   - Passed: `10` tests.
5. `.\.venv\Scripts\python.exe ops\scripts\dev\run_validation_target.py static.encoding_text_tools --timeout-seconds 120`
   - Passed; runner expanded `<changed-text-files>` to `13` files and the
     encoding scan reported `scanned=13 decode_errors=0 suspicious=0`.
6. `.\.venv\Scripts\python.exe ops\scripts\dev\run_validation_profile.py selector-recommended --paths apps\web\admin\src\views\HomeworkSubmissions.vue --dry-run --timeout-seconds 120`
   - Passed with `result=passed_with_deferred_review`; profile JSON listed
     `admin.e2e.homework_comment_cover_tier4` under `deferred_targets`.
7. `.\.venv\Scripts\python.exe ops\scripts\dev\select_validation_targets.py --worktree --json`
   - Passed; reported `non_full_validation.status=acceptable` and
     `unmatched_paths=[]`.
8. `git diff --check`
   - Passed.
9. `.\.venv\Scripts\python.exe ops\scripts\dev\run_validation_target.py static.validation_selector --timeout-seconds 120`
   - Passed.
10. `.\.venv\Scripts\python.exe ops\scripts\dev\playwright_preflight.py --json`
    - Passed with `exit_code: 0`.
