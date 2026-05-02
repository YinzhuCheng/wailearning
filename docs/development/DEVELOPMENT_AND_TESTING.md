# Development and Testing

## Required Reading Before Running Commands

Do not start with ad hoc commands if you are new to this repository or returning after a break.

Read in this order first:

1. [../architecture/REPOSITORY_STRUCTURE.md](../architecture/REPOSITORY_STRUCTURE.md)
2. [TEST_SUITE_MAP.md](TEST_SUITE_MAP.md)
3. [TEST_REDUNDANCY_AUDIT.md](TEST_REDUNDANCY_AUDIT.md) if you are evaluating test cleanup or consolidation
4. [TEST_EXECUTION_PITFALLS.md](TEST_EXECUTION_PITFALLS.md)
5. the feature-specific document for the workflow you are about to touch
6. when triaging full-suite outcomes or structural risk from tests, optionally read [../architecture/TEST_INFERRED_RISKS_AND_FOLLOWUPS.md](../architecture/TEST_INFERRED_RISKS_AND_FOLLOWUPS.md)

Why this is mandatory:

- the repository includes compatibility layers that are easy to misinterpret if you only inspect paths
- Windows + PowerShell execution has known traps that can produce false test failures
- Playwright failures in this repository are often environment or process-management issues before they are product regressions
- local artifact directories can look like source or canonical output if you do not read the structure notes first
- cross-platform and cloud-automation runs can hit additional traps (Element Plus locale, Playwright selector ambiguity, API `page_size` limits, stale ports); see [TEST_EXECUTION_PITFALLS.md](TEST_EXECUTION_PITFALLS.md) Pitfalls 11–16 and [../architecture/TEST_INFERRED_RISKS_AND_FOLLOWUPS.md](../architecture/TEST_INFERRED_RISKS_AND_FOLLOWUPS.md) for follow-up risk notes

## Local Development Setup

Before running commands, understand the repository boundary rules in [../architecture/REPOSITORY_STRUCTURE.md](../architecture/REPOSITORY_STRUCTURE.md). In particular:

- the real backend source lives in `apps/backend/app/`,
- the root `app/` package is a compatibility shim that still powers current imports and startup commands,
- the root `conftest.py` is intentionally repository-scoped,
- Windows launcher scripts live in `../../ops/scripts/windows/`.

### Backend

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
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

Defined in [`../../apps/backend/app/config.py`](../../apps/backend/app/config.py):

- `APP_ENV`
- `DEBUG`
- `DATABASE_URL`
- `SECRET_KEY`
- `ALLOW_PUBLIC_REGISTRATION`
- `INIT_DEFAULT_DATA`
- `E2E_DEV_SEED_ENABLED`
- `E2E_DEV_SEED_TOKEN`
- `ENABLE_LLM_GRADING_WORKER`
- `LLM_GRADING_WORKER_LEADER`

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

### Playwright backlog scenarios (optional)

Two specs under `tests/e2e/web-admin/` hold **placeholder titles** for advanced E2E coverage (`future-advanced-coverage*.spec.js`). By default they do not inflate routine run counts: see **`E2E_ENABLE_BACKLOG_SPECS`** and [E2E_BACKLOG_SCENARIOS.md](E2E_BACKLOG_SCENARIOS.md) for how to enable them while implementing scenarios.

Follow-up: when present in your tree, **`future-advanced-coverage.spec.js`** / **`future-advanced-coverage-2.spec.js`** should contain **real tests** and **`future-advanced-coverage-helpers.cjs`** shared helpers; treat them like other Playwright specs unless your branch still documents the older skipped-placeholder workflow.

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

When extending Playwright or threaded pytest coverage, the friction usually clusters around **contract mismatches** (HTTP method/parameter shape), **router redirects by role**, **SQLite races**, and **Playwright locator ambiguity**. Pitfalls **17–24** were appended to [TEST_EXECUTION_PITFALLS.md](TEST_EXECUTION_PITFALLS.md)— read those before debugging failures that look like “flaky UI” but are actually environment or selector discipline issues.

Further **test-authoring** lessons from the tier-4 stress E2E pass are recorded as pitfalls **25–31** in the same document (double `apiBase`, JSON encoding, schema `ge=` limits, homework title DOM vs API, password-change token capture, attachment ACL). A subsequent **full `pytest` + full admin Playwright** pass on a Linux agent added pitfalls **32–37** (MessageBox a11y, duplicate course title rows, disabled `force` clicks, `waitForResponse` race, password button label, Vite `goto` races). A **pitfall-guard** follow-up added **38–39** (delete-list UI vs API truth, per-route `page_size` limits).

### Recommendations for new test samples (E2E and API)

- **Confirm the contract first**: path, verb, query vs body, and Pydantic bounds — align with `apps/backend/app/routers/*.py` and `schemas.py`, and mirror the admin client in `apps/web/admin/src/api` when in doubt.
- **Assert server state before UI**: use `page.request`, shared `apiGetJson`, or `expect.poll` on an API predicate, then reload or widen locators for the UI (see pitfalls 29–30 in [TEST_EXECUTION_PITFALLS.md](TEST_EXECUTION_PITFALLS.md)).
- **Prefer stable hooks**: `data-testid`, course context helpers (`enterSeededRequiredCourse`), and explicit `waitForResponse` registration before clicks — especially for Element Plus dialogs and batch actions.
- **Concurrency**: prefer API-only parallel storms when the UI disables controls; avoid `Promise.all` on clicks that may be no-ops when disabled (see Pitfall 22).
- **Conditional scenarios**: if a test needs two movable material chapters, a parent code, or a class-teacher seed, use `test.skip` with a clear reason when the seed layout does not support it — document the assumption in the spec comment.
- **Regression placement**: put **API contract and idempotency** checks in `pytest` where possible; reserve Playwright for routing, visibility, and multi-tab behavior that HTTP tests cannot see.

### Sample hygiene: overlap, redundancy, and refinement targets

This is judgment for maintainers, not an automatic delete list:

- **`tests/e2e/web-admin/e2e-tier4-stress-backlog.spec.js`** and the optional **`future-advanced-coverage*.spec.js`** family can overlap conceptually (multi-role, LLM, notifications). When adding scenarios, check for an existing spec that already proves the same **invariant**; extend or parameterize before copying a full new test.
- Older E2E that still rely on **`toBeHidden`** on Element Plus dialogs alone are **more fragile** than patterns that confirm success via **network response + navigation + table row** (see resilience and boundary specs). Prefer aligning those tests with the “authoritative state first” rule rather than deleting them outright.
- **`TEST_REDUNDANCY_AUDIT.md`** remains the formal gate for safe deletes; the audit’s **protected** list intentionally keeps high-difficulty files — do not “clean up” stress specs without reading that policy.
- Optional backlog specs gated by **`E2E_ENABLE_BACKLOG_SPECS`** ([E2E_BACKLOG_SCENARIOS.md](E2E_BACKLOG_SCENARIOS.md)): if placeholders remain in a branch, do not treat them as failing debt — treat them as a **queue** with explicit enablement.

### May 2026: lessons from a full `pytest` + full admin Playwright run (Linux agent)

These notes **add** to the bullets above; they do not replace the redundancy audit or protection rules.

**Further recommendations when authoring new samples**

- **MessageBox and locale**: treat delete/confirm flows as “overlay + OK button” problems first; see Pitfall **32** in [TEST_EXECUTION_PITFALLS.md](TEST_EXECUTION_PITFALLS.md).
- **Student course pages**: any test that drives **选课/退选** must scope to the **catalog table** and wait for **enabled** action buttons; see Pitfalls **33–34**.
- **Network pairing**: for idempotent POSTs that return quickly, pair **`waitForResponse` with `click`** atomically; see Pitfall **35**.
- **Personal settings**: match the **exact** primary action label (`更新密码`) for password flows; see Pitfall **36**.
- **Login helpers shared across specs**: harden `goto('/login')` against Vite navigation races; see Pitfall **37**. Any new shared helper should follow the same pattern.
- **Admin `/users` table**: `el-table`’s inner layout can make raw `.el-table__body` **visibility** checks misleading; prefer waiting for a **known toolbar** `data-testid` (e.g. `users-open-create`) plus a **row/cell** locator scoped to the user table, or poll the API if the scenario allows.

**Samples that were misleading or easy to mis-maintain (refine in place, not necessarily delete)**

- **`e2e-scenario-resilience.spec.js` elective dual-context cases** historically used **unscoped** `tr:has-text(courseName)` and **`button.first()`** — wrong target and silent **`force`** on disabled **退选**. The fix is **scoping + enabled waits**; other files that copy the old pattern should be aligned when touched.
- **Tier-4 password test** using **`/密码/`** on the personal-settings page was **too broad**; prefer explicit labels or testids.
- **Overlap** between **`e2e-tier4-stress-backlog.spec.js`**, **`e2e-scenario-resilience.spec.js`**, and **`future-advanced-coverage*.spec.js`** remains: before adding a new case, grep for the same **invariant** (enroll idempotency, token invalidation, mark-all-read). Parameterize or extend an existing spec when the setup cost is high.
- **Redundancy**: still governed by [TEST_REDUNDANCY_AUDIT.md](TEST_REDUNDANCY_AUDIT.md); the audit’s merge-only candidates (courses/roster/LLM token files) are **review prompts**, not an automatic delete list.

### May 2026 (second pass): pitfall-guard batch specs and `page_size` discipline

- A second small Playwright file **`tests/e2e/web-admin/e2e-pitfall-guard-rails-batch2.spec.js`** was added to widen **`page_size` 422** coverage across **logs**, **points**, **parent scores/homework**, **homework submissions**, and **students** (where `le` differs — see Pitfall **39** in [TEST_EXECUTION_PITFALLS.md](TEST_EXECUTION_PITFALLS.md)). Run it alone with:
  - `npx playwright test e2e-pitfall-guard-rails-batch2.spec.js`
- When adding more list-endpoint tests, **parameterize `(path, max_page_size)`** from code or a tiny shared table in the spec — avoid magic `200` unless you confirmed `le` for that router.
- **`e2e-pitfall-guard-rails.spec.js`** (15 cases) and **batch2** (10 cases) overlap conceptually with **`e2e-cross-cutting-tier3.spec.js`** HTTP-edge tests; new edges should **extend** batch2 or tier3, not fork a third file, unless the invariant is genuinely new.

## After Documentation Updates

For documentation-only work, full test runs are not always necessary. For changes that also touch behavior, prefer:

```bash
python -m pytest tests/behavior -q
```

and then any targeted Playwright spec that covers the affected workflow.

### Cross-platform and CI smoke expectations

If you only run `pytest` on the default SQLite configuration, note that `tests/behavior/test_regression_llm_quota_behavior.py::test_r3_course_llm_config_columns_no_legacy_token_limits` is skipped unless the dialect is PostgreSQL. Full PostgreSQL-only assertions require `TEST_DATABASE_URL` (or equivalent) pointing at a live Postgres instance with migrated schema. This does not replace the default workflow for most changes; it matters when validating schema-level regressions.

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
