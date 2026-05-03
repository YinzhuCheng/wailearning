# Development and Testing

## Required Reading Before Running Commands

Do not start with ad hoc commands if you are new to this repository or returning after a break.

Read in this order first:

1. [../architecture/REPOSITORY_STRUCTURE.md](../architecture/REPOSITORY_STRUCTURE.md)
2. [ENCODING_AND_MOJIBAKE_SAFETY.md](ENCODING_AND_MOJIBAKE_SAFETY.md) if your shell is Windows + PowerShell or you may touch multilingual files
3. [TEST_SUITE_MAP.md](TEST_SUITE_MAP.md)
4. [TEST_REDUNDANCY_AUDIT.md](TEST_REDUNDANCY_AUDIT.md) if you are evaluating test cleanup or consolidation
5. [TEST_EXECUTION_PITFALLS.md](TEST_EXECUTION_PITFALLS.md)
6. [HISTORICAL_CODE_CLEANUP.md](HISTORICAL_CODE_CLEANUP.md) before deleting legacy-looking code, compatibility branches, or duplicate helpers
7. the feature-specific document for the workflow you are about to touch
8. when triaging full-suite outcomes or structural risk from tests, optionally read [../architecture/TEST_INFERRED_RISKS_AND_FOLLOWUPS.md](../architecture/TEST_INFERRED_RISKS_AND_FOLLOWUPS.md)

Why this is mandatory:

- the repository has strict package-boundary rules that are easy to misread if you only inspect paths
- Windows + PowerShell execution has known traps that can produce false test failures
- Windows + PowerShell sessions can also mis-render UTF-8 text; cleanup and documentation edits must follow [ENCODING_AND_MOJIBAKE_SAFETY.md](ENCODING_AND_MOJIBAKE_SAFETY.md) and the structural cleanup rules in [HISTORICAL_CODE_CLEANUP.md](HISTORICAL_CODE_CLEANUP.md)
- Playwright failures in this repository are often environment or process-management issues before they are product regressions
- local artifact directories can look like source or canonical output if you do not read the structure notes first
- cross-platform and cloud-automation runs can hit additional traps such as Element Plus locale behavior, Playwright selector ambiguity, API `page_size` limits, and stale ports; see [TEST_EXECUTION_PITFALLS.md](TEST_EXECUTION_PITFALLS.md) and [../architecture/TEST_INFERRED_RISKS_AND_FOLLOWUPS.md](../architecture/TEST_INFERRED_RISKS_AND_FOLLOWUPS.md) for follow-up risk notes

## Local Development Setup

Before running commands, understand the repository boundary rules in [../architecture/REPOSITORY_STRUCTURE.md](../architecture/REPOSITORY_STRUCTURE.md). In particular:

- the canonical backend package lives in `apps/backend/wailearning_backend/`,
- the canonical backend import root is `apps.backend.wailearning_backend`,
- the root `conftest.py` is intentionally repository-scoped,
- Windows launcher scripts live in `../../ops/scripts/windows/`.

### Backend

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn apps.backend.wailearning_backend.main:app --host 127.0.0.1 --port 8001 --reload
```

Optional Windows convenience launcher:

```bat
ops\scripts\windows\start-backend.bat
```

### Admin frontend

```bash
cd apps/web/admin
npm install
npm run dev
```

Optional Windows convenience launcher:

```bat
ops\scripts\windows\start-admin-frontend.bat
```

### Parent portal

```bash
cd apps/web/parent
npm install
npm run dev
```

Optional Windows convenience launcher:

```bat
ops\scripts\windows\start-parent-frontend.bat
```

## Key Development Settings

Defined in [`../../apps/backend/wailearning_backend/core/config.py`](../../apps/backend/wailearning_backend/core/config.py):

- `APP_ENV`
- `DEBUG`
- `DATABASE_URL`
- `SECRET_KEY`
- `BACKEND_CORS_ORIGINS`
- `TRUSTED_HOSTS`
- `INIT_ADMIN_USERNAME`
- `INIT_ADMIN_PASSWORD`
- `INIT_ADMIN_REAL_NAME`
- `ALLOW_PUBLIC_REGISTRATION`
- `INIT_DEFAULT_DATA`
- `E2E_DEV_SEED_ENABLED`
- `E2E_DEV_SEED_TOKEN`
- `ENABLE_LLM_GRADING_WORKER`
- `LLM_GRADING_WORKER_LEADER`
- `LLM_GRADING_WORKER_POLL_SECONDS`
- `LLM_GRADING_TASK_STALE_SECONDS`
- `DEFAULT_LLM_API_KEY`
- `REQUIRE_STRONG_SECRETS`

## Test Layers

### Backend `pytest`

Use backend tests for API logic, permission checks, grading behavior, and state-convergence rules.

```bash
python -m pytest
python -m pytest tests/behavior -q
```

Important directories:

- `tests/backend/`
- `tests/behavior/`
- `tests/scenarios/`

Before concluding that a backend test failure is a product regression, review the temp-path, Windows, and environment notes in [TEST_EXECUTION_PITFALLS.md](TEST_EXECUTION_PITFALLS.md).

For a domain-by-domain map of the backend suites, read [TEST_SUITE_MAP.md](TEST_SUITE_MAP.md).

### Frontend Playwright E2E

Use browser tests for login flows, stale-tab behavior, deep links, and UI-to-backend convergence.

```bash
cd apps/web/admin
npx playwright install chromium
npm run test:e2e
```

Key files:

- `apps/web/admin/playwright.config.cjs`
- `tests/e2e/web-admin/`
- `docs/development/TEST_EXECUTION_PITFALLS.md`
- `tests/TEST_PROTECTION_RULES.json`

Before running Playwright on Windows, read the pitfalls document first. Known false-failure causes include:

- `npm.ps1` execution-policy blocking,
- stale API or UI ports,
- hidden old processes serving the wrong app,
- sandbox `EPERM` during subprocess startup,
- readiness checks that accept the wrong HTTP response.

### Playwright advanced-coverage scenarios

In this branch, the pair below is already implemented as normal runnable Playwright coverage:

- `tests/e2e/web-admin/future-advanced-coverage.spec.js`
- `tests/e2e/web-admin/future-advanced-coverage-2.spec.js`

Shared helpers live in:

- `tests/e2e/web-admin/future-advanced-coverage-helpers.cjs`

Historical note:

- older documentation and older branches described these files as a skipped placeholder backlog behind `E2E_ENABLE_BACKLOG_SPECS`
- that description is no longer true for this branch, but the historical workflow is still preserved in [E2E_BACKLOG_SCENARIOS.md](E2E_BACKLOG_SCENARIOS.md) so future maintainers can interpret older commits correctly

## E2E Seed and Environment

The repository includes an E2E-only reset API used by browser tests.

- Route family: `/api/e2e/...`
- Guarded by `E2E_DEV_SEED_ENABLED` and `E2E_DEV_SEED_TOKEN`
- Never enable this in production

Playwright scenarios commonly use:

- `POST /api/e2e/dev/reset-scenario`
- a local API URL,
- a local frontend base URL,
- a local Playwright browser cache path on Windows.

## Windows Notes

This repository is actively used on Windows, so path and encoding discipline matters.

- Prefer running `pytest` from the repository root.
- Prefer the repository virtual environment instead of a global Python.
- Keep documentation and scripted edits ASCII-first when possible.
- Avoid shell-side bulk rewriting of Chinese strings.
- Treat terminal-rendered Unicode as display-only until it is verified against file content or git diff.
- Do not treat local directories such as `frontend/`, `test-results/`, `.e2e-run/`, or `.pytest_tmp/` as source layout. They are local artifacts.
- For Playwright, explicitly set `PLAYWRIGHT_BROWSERS_PATH` when using a local browser cache.

Example command pattern for targeted Playwright runs:

```powershell
$env:PLAYWRIGHT_BROWSERS_PATH='C:\Users\<user>\AppData\Local\ms-playwright'
$env:E2E_API_URL='http://127.0.0.1:8012'
$env:PLAYWRIGHT_BASE_URL='http://127.0.0.1:3012'
$env:E2E_DEV_SEED_TOKEN='test-playwright-seed'
npm run test:e2e
```

Concrete safe-edit strategy for multilingual files in this repository:

- prefer editing through repository-aware patching instead of copying terminal-rendered Chinese text back into files
- do not trust PowerShell display output as the source of truth for non-ASCII content
- if a Chinese string must be changed, anchor the edit on surrounding ASCII structure (`data-testid`, route path, JSON key, Markdown heading, or code identifier) rather than on terminal-rendered mojibake
- after editing, verify via git diff and file-local context instead of trusting the console glyphs alone

## Current High-Value Regression Areas

These are the areas most worth testing when behavior changes:

- startup-time idempotency and backfill behavior,
- roster and class-move synchronization,
- required versus elective enrollment rules,
- homework submission history and max-submission limits,
- LLM routing, quota, retry, and regrade recovery,
- notification read-state convergence,
- grade and homework appeal deduplication,
- deep-link recovery when local course context is stale or missing.

## Complex Regression Coverage Added In This Repository

Recent behavior coverage includes scenarios such as:

- score-appeal reopen after resolve or reject,
- concurrent duplicate appeal submission settling to one pending row,
- targeted-student notification privacy,
- subject-scoped mark-all-read behavior,
- concurrent notification read-state convergence,
- batch class flip-flop preserving one required enrollment,
- batch import retry idempotency,
- quota exhaustion followed by recovery,
- disable-then-reenable LLM grading flows.

Browser note: `tests/e2e/web-admin/e2e-discussion-cover-llm-tier3.spec.js` (15 cases) exercises **discussion LLM assistant**, **long-body preview/collapse**, and **course cover** flows against the seeded scenario; `POST /api/e2e/dev/reset-scenario` now seeds a per-run **`discussion_llm_profile`** plus an enabled course LLM row wired to the mock chat endpoint so discussion jobs can complete without manual admin setup.

Additional browser coverage: `tests/e2e/web-admin/e2e-homework-comment-cover-tier4.spec.js` (15 cases) stresses **homework submissions list** `content_preview` / `comment_preview` ellipsis behavior (teacher UI uses stable `data-testid`s), **LLM auto-grade** long comments, **regrade** and **429-then-success** mock paths, concurrent teacher/student API interactions, and **course cover** uploads (teacher UI + admin POST + student-visible banners).

## Practical Testing Rules

- Assert authoritative business state before asserting visual transitions.
- Prefer stable identifiers and API-level validation over UI copy.
- Run the narrow failing test first, then the relevant suite, then the broader suite.
- Separate product bugs from environment mistakes such as working-directory or temp-path issues.
- If running on Windows + PowerShell, review `TEST_EXECUTION_PITFALLS.md` before assuming Playwright or pytest failures are product regressions.

### Incremental lessons from higher-difficulty browser/API suites (May 2026)

When extending Playwright or threaded pytest coverage, the friction usually clusters around contract mismatches, router redirects by role, SQLite races, and Playwright locator ambiguity. Read the later pitfall entries in [TEST_EXECUTION_PITFALLS.md](TEST_EXECUTION_PITFALLS.md) before debugging failures that look like flaky UI but are actually environment or selector-discipline issues.

Further test-authoring lessons from the tier-4 stress E2E pass are recorded in the same document, including `apiBase` mismatches, JSON encoding mistakes, schema `ge=` limits, homework title DOM-vs-API mismatches, password-change token capture, and attachment ACL issues. A subsequent full `pytest` plus full admin Playwright pass on a Linux agent added notes about MessageBox accessibility, duplicate course-title rows, disabled-force click mistakes, `waitForResponse` races, password button labels, and Vite `goto` races. A later pitfall-guard follow-up added delete-list UI-vs-API truth and per-route `page_size` lessons.

### Recommendations for new test samples (E2E and API)

- **Confirm the contract first**: path, verb, query-vs-body shape, and Pydantic bounds should align with `apps/backend/wailearning_backend/api/routers/*.py` and `apps/backend/wailearning_backend/api/schemas.py`, and should mirror the admin client in `apps/web/admin/src/api` when in doubt.
- **Assert server state before UI**: use `page.request`, shared `apiGetJson`, or `expect.poll` on an API predicate, then reload or widen locators for the UI.
- **Prefer stable hooks**: `data-testid`, course context helpers such as `enterSeededRequiredCourse`, and explicit `waitForResponse` registration before clicks are safer, especially for Element Plus dialogs and batch actions.
- **Concurrency**: prefer API-only parallel storms when the UI disables controls; avoid `Promise.all` on clicks that may be no-ops when disabled (see Pitfall 22).
- **Conditional scenarios**: if a test needs two movable material chapters, a parent code, or a class-teacher seed, use `test.skip` with a clear reason when the seed layout does not support it, and document the assumption in the spec comment.
- **Playwright environment contract**: default managed E2E in this branch starts the API on `8012` and the admin UI on `3012`, uses `PLAYWRIGHT_USE_EXTERNAL_SERVERS` to opt out of managed servers, and accepts `E2E_PYTHON` plus `E2E_USE_REAL_WORKER` for backend-process control; keep docs and CI commands aligned with `apps/web/admin/playwright.config.cjs`.
- **Regression placement**: put **API contract and idempotency** checks in `pytest` where possible; reserve Playwright for routing, visibility, and multi-tab behavior that HTTP tests cannot see.

### Sample hygiene: overlap, redundancy, and refinement targets

This is judgment for maintainers, not an automatic delete list:

- **`tests/e2e/web-admin/e2e-tier4-stress-backlog.spec.js`** and the implemented **`future-advanced-coverage*.spec.js`** family can overlap conceptually (multi-role, LLM, notifications). When adding scenarios, check for an existing spec that already proves the same **invariant**; extend or parameterize before copying a full new test.
- Older E2E that still rely on `toBeHidden` on Element Plus dialogs alone are more fragile than patterns that confirm success via network response, navigation, and table-row state. Prefer aligning those tests with the authoritative-state-first rule rather than deleting them outright.
- **`TEST_REDUNDANCY_AUDIT.md`** remains the formal gate for safe deletes; the audit's protected list intentionally keeps high-difficulty files, so do not clean up stress specs without reading that policy.
- Historical backlog note: if you are reading an older branch where `E2E_ENABLE_BACKLOG_SPECS` still gates placeholder suites, do not treat those placeholders as failing debt; treat them as a queue with explicit enablement. In this branch, the `future-advanced-coverage*.spec.js` pair is already runnable coverage.

### May 2026: lessons from a full `pytest` + full admin Playwright run (Linux agent)

These notes **add** to the bullets above; they do not replace the redundancy audit or protection rules.

**Further recommendations when authoring new samples**

- **MessageBox and locale**: treat delete and confirm flows as overlay-plus-confirm-button problems first.
- **Student course pages**: any test that drives **选课/退选** must scope to the **catalog table** and wait for **enabled** action buttons; see Pitfalls **33–34**.
- **Network pairing**: for idempotent POSTs that return quickly, pair **`waitForResponse` with `click`** atomically; see Pitfall **35**.
- **Personal settings**: match the **exact** primary action label (`更新密码`) for password flows; see Pitfall **36**.
- **Login helpers shared across specs**: harden `goto('/login')` against Vite navigation races; see Pitfall **37**. Any new shared helper should follow the same pattern.
- **Admin `/users` table**: `el-table` inner layout can make raw `.el-table__body` visibility checks misleading; prefer waiting for a known toolbar `data-testid` such as `users-open-create` plus a row-or-cell locator scoped to the user table, or poll the API if the scenario allows.

**Samples that were misleading or easy to mis-maintain (refine in place, not necessarily delete)**

- **`e2e-scenario-resilience.spec.js` elective dual-context cases** historically used **unscoped** `tr:has-text(courseName)` and **`button.first()`** — wrong target and silent **`force`** on disabled **退选**. The fix is **scoping + enabled waits**; other files that copy the old pattern should be aligned when touched.
- **Tier-4 password test** using **`/密码/`** on the personal-settings page was **too broad**; prefer explicit labels or testids.
- **Overlap** between **`e2e-tier4-stress-backlog.spec.js`**, **`e2e-scenario-resilience.spec.js`**, and **`future-advanced-coverage*.spec.js`** remains: before adding a new case, grep for the same **invariant** (enroll idempotency, token invalidation, mark-all-read). Parameterize or extend an existing spec when the setup cost is high.
- **Redundancy**: still governed by [TEST_REDUNDANCY_AUDIT.md](TEST_REDUNDANCY_AUDIT.md); the audit's merge-only candidates are review prompts, not an automatic delete list.

### May 2026 (second pass): pitfall-guard batch specs and `page_size` discipline

- A second small Playwright file **`tests/e2e/web-admin/e2e-pitfall-guard-rails-batch2.spec.js`** was added to widen **`page_size` 422** coverage across **logs**, **points**, **parent scores/homework**, **homework submissions**, and **students** where router-specific `le` limits differ. Run it alone with:
  - `npx playwright test e2e-pitfall-guard-rails-batch2.spec.js`
- When adding more list-endpoint tests, **parameterize `(path, max_page_size)`** from code or a tiny shared table in the spec; avoid magic `200` unless you confirmed `le` for that router.
- **`e2e-pitfall-guard-rails.spec.js`** (15 cases) and **batch2** (10 cases) overlap conceptually with **`e2e-cross-cutting-tier3.spec.js`** HTTP-edge tests; new edges should **extend** batch2 or tier3, not fork a third file, unless the invariant is genuinely new.

## After Documentation Updates

For documentation-only work, full test runs are not always necessary. For changes that also touch behavior, prefer:

```bash
python -m pytest tests/behavior -q
```

and then any targeted Playwright spec that covers the affected workflow.

### Cross-platform and CI smoke expectations

If you only run `pytest` on the default SQLite configuration, note that `tests/behavior/test_regression_llm_quota_behavior.py::test_r3_course_llm_config_columns_no_legacy_token_limits` is skipped unless the dialect is PostgreSQL. Full PostgreSQL-only assertions require `TEST_DATABASE_URL` (or equivalent) pointing at a live Postgres instance with migrated schema. This does not replace the default workflow for most changes; it matters when validating schema-level regressions.

**PostgreSQL local smoke (Linux example):** Install Postgres, create a dedicated empty database and user, export `TEST_DATABASE_URL=postgresql://USER:PASSWORD@127.0.0.1:5432/DBNAME`, then run `python -m pytest`. Tests recreate schema via `tests/db_reset.py` (`DROP SCHEMA public CASCADE` on non-SQLite). Use a database reserved for automation only; do not point at production. Avoid running two pytest processes against the same `TEST_DATABASE_URL` concurrently — resets collide.

**RAR attachment tests:** `tests/backend/llm/test_llm_attachment_formats.py` includes cases that shell out to the **`rar`** CLI to build archives; Debian/Ubuntu provide it in the **`rar`** package (non-free section may need `contrib` / mirror enabled). Without `rar`, those tests skip; **`unrar`** is used when unpacking in-app paths.

## Test Cleanup Policy

If you are considering deleting or consolidating tests, do not start from ad hoc judgment.

Read and use:

- [TEST_REDUNDANCY_AUDIT.md](TEST_REDUNDANCY_AUDIT.md)
- `tools/testing/audit_test_redundancy.py`
- `tests/TEST_PROTECTION_RULES.json`

Policy:

- high-difficulty and high-value tests are protected first,
- exact duplicates may be considered for removal only when they are outside the protection policy,
- same-file duplicates should usually be parameterized rather than deleted,
- overlap candidates should be reviewed manually before any deletion is proposed.
