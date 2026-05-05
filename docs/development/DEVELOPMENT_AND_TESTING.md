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
- Never enable this in production; additionally, `APP_ENV=production` forces `expose_e2e_dev_api()` to **false**, so every `/api/e2e/...` request returns **404** even if seed flags were mis-set (see `tests/backend/test_settings_e2e_router_gate.py`). The router remains registered for test-time toggles; access is blocked by a router-level dependency.

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

If you only run `pytest` on the default SQLite configuration, note that `tests/behavior/test_regression_llm_quota_behavior.py::test_r3_course_llm_config_columns_no_legacy_token_limits` is skipped unless the dialect is PostgreSQL (unless you set **`WAILEARNING_AUTO_PG_TESTS=1`** after provisioning the standard throwaway DB — see below). That guard asserts `information_schema` shows **no** legacy token-limit or course-level quota-policy columns on `course_llm_configs` (including removed `quota_timezone`, `estimated_chars_per_token`, `estimated_image_tokens`). Full PostgreSQL-only assertions require `TEST_DATABASE_URL` (or auto-pick) pointing at a live Postgres instance with migrated schema. This does not replace the default workflow for most changes; it matters when validating schema-level regressions.

**PostgreSQL local smoke (Linux example):** Install Postgres, then either:

1. **Idempotent helper (recommended):** run `bash ops/scripts/dev/provision_postgres_pytest.sh` as a user who may `sudo -u postgres psql` (creates role `wailearning_test`, database `wailearning_pytest_all`, password `wailearning_test` by default; override with `WAILEARNING_PYTEST_DB_*` env vars documented in the script). Then either export the printed `TEST_DATABASE_URL`, **or** run pytest with **`WAILEARNING_AUTO_PG_TESTS=1`** so `tests/conftest.py` auto-selects that URL when TCP + credentials succeed (no manual export).

2. **Manual:** create a dedicated empty database and user, export `TEST_DATABASE_URL=postgresql+psycopg2://USER:PASSWORD@127.0.0.1:5432/DBNAME`, then run `python3 -m pytest`.

Tests recreate schema via `tests/db_reset.py` (`DROP SCHEMA public CASCADE` on non-SQLite, plus dropping leftover **`pg` ENUM types** in `public` before `create_all` so SQLAlchemy can recreate enums cleanly). Use a database reserved for automation only; do not point at production. Avoid running two pytest processes against the same `TEST_DATABASE_URL` concurrently — resets collide.

**RAR attachment tests:** `tests/backend/llm/test_llm_attachment_formats.py` exercises the same RAR code path as production (`domains/llm/attachments.py` via `llm_grading` imports). Committed sample archives live under **`tests/fixtures/llm_rar/`** so tests do **not** shell out to the **`rar`** compressor at runtime. Unpacking still requires **`unrar`** or **`unrar-free`** on `PATH` (the product’s `_unrar_tool_path` check). If neither tool is installed, the two RAR tests **skip** with a short message (same failure mode as missing extractors in production for RAR inputs). Regenerating the binary fixtures (optional) still uses **`rar a ...`** on a maintainer machine; do not commit regenerated bytes without re-running the full attachment suite.

**Full regression prerequisites (what maintainers should enable before claiming “no skips”):**  
CI machines and anyone publishing “green full-suite” results should install **`unrar`** (or `unrar-free`), provision the throwaway database (see `ops/scripts/dev/provision_postgres_pytest.sh`), then run one of:

```bash
# Option A — explicit URL (works on all platforms once Postgres listens on TCP)
export TEST_DATABASE_URL='postgresql+psycopg2://wailearning_test:wailearning_test@127.0.0.1:5432/wailearning_pytest_all'
python3 -m pytest tests/

# Option B — Linux/macOS: auto-pick the same URL when the probe DB answers (after provision script)
WAILEARNING_AUTO_PG_TESTS=1 python3 -m pytest tests/
```

That executes **`tests/postgres/`** (dialect guards, LLM schema guards, and the additive **quota / constraint hazard** module described below), **`tests/behavior/test_regression_llm_quota_behavior.py::test_r3_...`** (`information_schema`), and the RAR-based attachment tests (when **`unrar`** is available).

**Skip counts (reference):** On **SQLite** with **`unrar`** (or `unrar-free`) on `PATH` but **without** `TEST_DATABASE_URL` / auto-Postgres, expect **43 skipped** (PostgreSQL-only modules + `test_r3`). If **`unrar` is also missing**, add **2** skips for the RAR attachment cases (**45** total). With **`WAILEARNING_AUTO_PG_TESTS=1`** (or `TEST_DATABASE_URL` set) against a live Postgres, expect **432 passed, 0 skipped** in the current collection (same **432** tests collected as SQLite; Postgres runs the previously skipped `tests/postgres/*` and `test_r3`, May 2026).

The **SQLite-only `passed` integer** (for example **389** when **43** tests skip) is not a permanent constant as new tests land in the default collection; rely on **skip deltas** and the **432 / 0** Postgres matrix instead of memorizing a single `passed` tally.

Default `pytest` without Postgres or **`unrar`** remains valid for fast loops but **will report skips** for those items — treat that as **environment debt**, not product absence.

**Agent recipe — Debian/Ubuntu cloud image with only `apt` (no preinstalled Node):** Minimal Python-only sandboxes can still reach **432 passed, 0 skipped** and run **one** Playwright hazard file without hand-installing Node from upstream tarballs:

1. **PostgreSQL + throwaway DB:** `sudo apt-get install -y postgresql postgresql-contrib` → `sudo pg_ctlcluster 16 main start` (version may differ) → `bash <REPO_ROOT>/ops/scripts/dev/provision_postgres_pytest.sh` (requires `sudo -u postgres`).
2. **RAR extractors:** `sudo apt-get install -y unrar rar` (or `unrar-free` where `unrar` is unavailable).
3. **pytest:** `python3 -m pip install -r <REPO_ROOT>/requirements.txt` then `cd <REPO_ROOT> && WAILEARNING_AUTO_PG_TESTS=1 python3 -m pytest tests/ -q` → expect **432 passed, 0 skipped** when steps 1–2 succeeded.
4. **Node + Playwright (apt, not `nvm`):** `sudo apt-get install -y nodejs npm` — on Ubuntu 24.04 this typically yields **Node 18.x** and **npm 9.x**, sufficient for `<REPO_ROOT>/apps/web/admin/package.json`.
5. **Admin deps + browser:** `cd <REPO_ROOT>/apps/web/admin && npm ci && npx playwright install chromium`.
6. **E2E run:** Use **`E2E_PYTHON`** pointing at an interpreter that has **`uvicorn`** on `PYTHONPATH` (repository **`.venv`** if present, else **`/usr/bin/python3`** after `pip install -r requirements.txt`). Example smoke:

```bash
cd <REPO_ROOT>/apps/web/admin
CI=1 E2E_PYTHON=/usr/bin/python3 E2E_DEV_SEED_TOKEN=test-playwright-seed \
  npx playwright test e2e-agent-hazard-tier-15.spec.js --project=chromium
```

Observed in one cloud session: **`npm ci` + `npx playwright install chromium` + the command above** produced **15 passed** for `e2e-agent-hazard-tier-15.spec.js` in ~15s wall time. Do **not** run multiple Playwright CLI processes on default ports **8012/3012** (Pitfall 41).

**Authoring convention — database-backed tests:** When adding or reviewing tests that touch persistence, schema, transactions, concurrency, or dialect-specific behavior, **assume PostgreSQL as the production-aligned reference**: write assertions and fixtures compatible with Postgres first; use SQLite for speed locally where the suite allows, but **do not rely on SQLite-only semantics** as proof for shipping schema-sensitive changes. Re-validate meaningful DB changes against **`TEST_DATABASE_URL`** (Postgres).

### PostgreSQL full-suite and cloud-agent session notes (additive, for LLM agents)

This subsection is intentionally long. The primary reader is an automated coding agent that benefits from exhaustive, searchable operational detail. Human maintainers may skim the headings and follow links to [TEST_EXECUTION_PITFALLS.md](TEST_EXECUTION_PITFALLS.md).

#### 1. Environment recipe used when validating `TEST_DATABASE_URL` on a blank Linux VM

The following pattern is representative; replace `<REPO_ROOT>`, `<DBNAME>`, `<USER>`, `<PASSWORD>` with your own throwaway values. Never point `TEST_DATABASE_URL` at production.

1. Install PostgreSQL server packages (example: `postgresql` / `postgresql-contrib` on Debian-derived images).
2. Start the cluster (example: `pg_ctlcluster 16 main start` or your distribution’s equivalent).
3. Create a dedicated role and database:

```sql
DROP DATABASE IF EXISTS <DBNAME>;
DROP ROLE IF EXISTS <USER>;
CREATE USER <USER> WITH PASSWORD '<PASSWORD>';
CREATE DATABASE <DBNAME> OWNER <USER>;
```

4. Export before pytest:

```bash
export TEST_DATABASE_URL='postgresql://<USER>:<PASSWORD>@127.0.0.1:5432/<DBNAME>'
cd <REPO_ROOT>
python3 -m pytest tests/ -q
```

5. **Concurrency rule:** do not run two `pytest` processes against the same `TEST_DATABASE_URL`. `tests/db_reset.py` issues `DROP SCHEMA public CASCADE` on PostgreSQL; concurrent resets produce nondeterministic failures that look like product bugs.

#### 2. Concrete failures observed during a full `pytest tests/` run on PostgreSQL (and fixes)

These are documented so the next agent does not burn time re-diagnosing the same issues.

**2a. `IN (...)` trailing comma is a syntax error on PostgreSQL only**

Symptom: `psycopg2.errors.SyntaxError: syntax error at or near ")"` when executing raw SQL in tests such as `tests/behavior/test_regression_llm_quota_behavior.py::test_r3_course_llm_config_columns_no_legacy_token_limits` or `tests/postgres/test_postgres_dialect_guards.py::test_pg03_...`.

Cause: PostgreSQL rejects `WHERE col IN ('a','b',)` (note the comma before the closing parenthesis). SQLite’s parser tolerated the same text in some configurations.

Fix: remove the trailing comma after the last literal in the `IN` list. See **Pitfall 42** in [TEST_EXECUTION_PITFALLS.md](TEST_EXECUTION_PITFALLS.md).

**2b. Behavioral test `test_a3` assumed a per-course quota calendar**

Symptom: `AssertionError: assert 'Asia/Shanghai' == 'UTC'` after the global admin policy timezone was changed.

Cause: after round-4 schema cleanup, **only** `LLMGlobalQuotaPolicy` defines the student-visible quota calendar. There is no longer a stable “course calendar pins UTC while admin changes global” behavior.

Fix: the test was renamed and inverted to assert that **student quota snapshots follow the global policy** when the admin updates `quota_timezone`. See `tests/behavior/test_admin_llm_policy_behavior.py::test_a3_global_timezone_change_reflects_in_student_quota_calendar`.

**2c. SQLAlchemy `Session.merge()` on `llm_student_token_overrides` can still attempt INSERT**

Symptom: `UniqueViolation` on `llm_student_token_overrides_student_id_key` when a test called `merge()` twice in one session after deleting the row in a way that left SQLAlchemy’s identity map inconsistent with the intended “upsert” mental model.

Cause: `merge()` is not a generic substitute for “UPDATE if exists”; for tables with a **natural unique key** (`student_id`) and no application-level merge key loaded in the session, the second `merge()` can resolve to an INSERT that collides with the row created by the first `merge()` in the same transaction boundary.

Fix for tests: prefer explicit `query(...).one()` then attribute mutation, or use the repository’s `apply_student_daily_token_overrides` API helpers instead of raw `merge()` in hazard tests. See **Pitfall 43** in [TEST_EXECUTION_PITFALLS.md](TEST_EXECUTION_PITFALLS.md).

**2d. Round-1 hardening (P0/P1 follow-ups from security audit, code changes)**

- **`/api/e2e/*` router access:** `e2e_dev.router` is **always** registered in `main.py` so pytest and tooling can toggle ``E2E_DEV_SEED_ENABLED`` at runtime without reloading the app. Every route on that router depends on ``require_e2e_dev_api_exposed`` (`api/routers/e2e_dev.py`), which raises **404** unless ``settings.expose_e2e_dev_api()`` is true. In production, ``expose_e2e_dev_api()`` is always false; ``Settings`` still rejects ``E2E_DEV_SEED_ENABLED`` with production ``APP_ENV`` at parse time. Regression coverage: `tests/backend/test_settings_e2e_router_gate.py`.
- **Attachment download by basename:** `apps/backend/wailearning_backend/api/routers/files.py::download_attachment_by_stored_name` resolves every **authorized** candidate URL to an on-disk path; if more than one **distinct** resolved path exists for the same basename, the handler returns **403** instead of picking an arbitrary row (mitigates basename collision widening access while still allowing multiple DB rows that reference the same physical file). Collisions are logged at warning level.
- **LLM worker executor:** `apps/backend/wailearning_backend/llm_grading.py` `_WorkerManager._run` pairs each `Future` with its `task_id`; on `fut.result()` failure it calls `_mark_task_failed_from_worker_executor` so tasks do not stick in `processing` until stale reclaim. Exceptions use `logging` instead of bare `print`.
- **Concurrent mark-all-read:** `POST /api/notifications/mark-all-read` uses dialect-specific `INSERT .. ON CONFLICT DO UPDATE` on `notification_reads(notification_id, user_id)` for PostgreSQL and SQLite so parallel mark-all-read / mark-read cannot hit `IntegrityError` on the unique index. Regression: `tests/behavior/test_complex_regression_roundtrip_behavior.py::test_c7b_concurrent_dual_mark_all_read_no_integrity_errors`.

#### 3. Agent “worries” and residual coverage gaps (explicit, not a bug list)

These are risk statements for planning; they are not confirmed production defects.

- **Worries**
  - **Dialect drift:** SQLite-first developers can ship SQL that parses on SQLite but fails on PostgreSQL (see `IN` trailing commas). CI that only runs SQLite will miss this until merge.
  - **Semantic drift after quota consolidation:** tests that encoded the old “per-course calendar” model will fail loudly on PostgreSQL full runs; that is desirable, but agents must read failure text as a **spec migration signal**, not random flakiness.
  - **E2E harness fragility:** Playwright `webServer` + fixed ports (`<E2E_API_HOST>:8012`, `<E2E_UI_HOST>:3012` by default) plus mock LLM on-loopback can produce `ECONNRESET` when parallelized; see Pitfall 41.
  - **`merge()` foot-guns:** ORM convenience methods behave differently per mapper configuration; hazard tests should prefer API-level assertions for business invariants.

- **Coverage gaps (examples, not exhaustive)**
  - **Multi-instance grading worker** leader election and stale-task reclamation under real wall-clock delays are not fully exercised by fast pytest loops.
  - **True external LLM providers** (network, rate limits, TLS) are intentionally mocked in E2E; production-only failure modes are not represented.
  - **Very large attachments** (multi-hundred-MB archives) and disk-quota interactions are only partially covered.
  - **Parent portal** and **mobile viewports** have thinner automated coverage than admin + student flows.
  - **Backup/restore and rolling upgrades** across schema versions are operational concerns, not unit-tested end-to-end in this repository.

#### 4. New additive suites (PostgreSQL hazard + E2E hazard tier)

The following files are **additive** regression nets. They do not replace the directories listed later under “New focused suites”; they extend them.

- **`tests/postgres/test_postgres_llm_schema_and_policy.py`** — `information_schema` and FK-shape checks for LLM global policy vs course config (round-4 alignment).
- **`tests/postgres/test_postgres_quota_api_and_constraints.py`** — fifteen **HTTP + raw SQL** checks: admin validation (`422` paths), teacher/student authorization edges, duplicate endpoint rows (`uq_course_llm_config_endpoint`), duplicate enrollment, orphan FK attempts, and metadata checks. Requires PostgreSQL (`TEST_DATABASE_URL`); skipped on SQLite.
- **`tests/e2e/web-admin/e2e-postgres-hazard-tier.spec.js`** — fifteen **API + light UI** checks: global quota policy round-trip, legacy JSON keys on course PUT, student quota alignment after admin timezone change, bulk overrides, parallel duplicate GETs, Settings and Subjects LLM dialog smoke. Requires Playwright global setup (`E2E_DEV_SEED_TOKEN`). Run **serially** with other Playwright jobs (`CI=1` recommended).

Example commands:

```bash
# PostgreSQL-only package (skips automatically without TEST_DATABASE_URL)
export TEST_DATABASE_URL='postgresql://<USER>:<PASSWORD>@127.0.0.1:5432/<DBNAME>'
python3 -m pytest tests/postgres/ -q

# E2E hazard tier (from admin frontend package root)
cd <REPO_ROOT>/apps/web/admin
CI=1 E2E_PYTHON=<REPO_ROOT>/.venv/bin/python npx playwright test e2e-postgres-hazard-tier.spec.js --project=chromium
```

Artifacts: Playwright may write `<REPO_ROOT>/apps/web/admin/test-results/` and `<REPO_ROOT>/apps/web/admin/playwright-report/`; these paths must remain **untracked** and must not be committed.

#### 5. Full-suite regression runs (cloud agent, May 2026) and line-count inventory

This subsection records **machine-verified** outcomes so future agents do not re-claim “green” without matching the same matrix.

##### 5a. `python3 -m pytest tests/` — two engine configurations

| Configuration | Command pattern | Outcome (representative) | Wall-clock order of magnitude |
|---------------|-----------------|---------------------------|--------------------------------|
| **Default SQLite** (no `TEST_DATABASE_URL`, no `WAILEARNING_AUTO_PG_TESTS`) | `cd <REPO_ROOT> && python3 -m pytest tests/ -q` | **389 passed**, **43 skipped** when **`unrar`** is present; **45 skipped** when **`unrar`** is missing (adds 2 RAR attachment tests) | ~8 minutes on a typical cloud CPU |
| **PostgreSQL** (`TEST_DATABASE_URL` **or** `WAILEARNING_AUTO_PG_TESTS=1` after `ops/scripts/dev/provision_postgres_pytest.sh`) | `export TEST_DATABASE_URL='postgresql+psycopg2://…'` or `WAILEARNING_AUTO_PG_TESTS=1 python3 -m pytest tests/ -q` | **432 passed**, **0 skipped** (with **`unrar`** + Postgres provisioned) | ~9.5 minutes on a typical cloud CPU |

Interpretation for agents:

- The **delta** (`432 - 389 = 43` extra tests executed on Postgres vs default SQLite) is dominated by **`tests/postgres/*`** plus **`test_r3`** (`information_schema`). Treat “SQLite-only green” as **necessary but not sufficient** for schema-sensitive merges.
- **Zero-skip CI:** install **`unrar`** (or `unrar-free`), run **`ops/scripts/dev/provision_postgres_pytest.sh`**, then set **`WAILEARNING_AUTO_PG_TESTS=1`** (Linux agents) or **`TEST_DATABASE_URL`** explicitly (portable).

**Not executed in the same session:** a full `npx playwright test` over **all** `tests/e2e/web-admin/*.spec.js` files (that run is hours-wide and belongs in a dedicated CI job). What **was** executed after the PostgreSQL pytest pass is the **additive** hazard file only:

```bash
cd <REPO_ROOT>/apps/web/admin
CI=1 E2E_PYTHON=<REPO_ROOT>/.venv/bin/python npx playwright test e2e-postgres-hazard-tier.spec.js --project=chromium
```

Outcome: **15 passed** (API + light UI checks for LLM global vs course boundaries).

**Machine re-check (same agent session, after adding ``test_e2e_dev_api_hazard_tier.py``):** `python3 -m pytest tests/` on default SQLite reported **389 passed, 43 skipped** (~8m24s); `WAILEARNING_AUTO_PG_TESTS=1 python3 -m pytest tests/` reported **432 passed, 0 skipped** (~9m58s) when the throwaway Postgres from ``ops/scripts/dev/provision_postgres_pytest.sh`` was present and **`unrar`** was installed.

**Playwright CLI pitfall observed:** `npx playwright test ... -q` may fail with `error: unknown option '-q'` on some Playwright versions bundled with the repo. Prefer **no `-q`** flag, or use `PLAYWRIGHT_HTML_REPORT=0` / reporter flags documented upstream for your installed version.

##### 5b. Repository line-count inventory (agent-oriented methodology)

The following numbers were produced by a **repository-local Python walker** (not `cloc`, to avoid long `apt-get` installs in minimal cloud images). Treat them as **approximate physical line counts** (newline-delimited text lines; UTF-8 with replacement on decode errors; empty files dropped).

**Excluded directory names** (substring match on path components): `.git`, `node_modules`, `dist`, `.venv`, `venv`, `__pycache__`, `.pytest_cache`, `coverage`, `test-results`, `playwright-report`, `.e2e-run`, `.pytest_tmp`, `.cursor`.

**Document lines** (Markdown / RST / TXT / ADOC under `docs/`, `ops/**/*.md`, root README-style files; **excluding** `tests/**/*.md`):

- **~7,467 lines** across **~20 files** (exact integers are in the agent’s last inventory run; re-run the script if you need bit-identical reproducibility after large merges).

**Test code lines** (`tests/` only; extensions mapped as “code”: `.py`, `.js`, `.cjs`, `.mjs`, `.ts`, `.tsx`, `.vue`, `.json`, `.sql`, …):

- **~25,743 lines** across **~111 files** (same caveat: re-run after major edits).

**Product code lines** (everything not under `tests/` and not classified as “document” above):

- **~51,386 lines** in the same inventory pass.

**Grand total text lines** in that pass: **~85,222** (includes small “other” configuration files such as `.conf` under `ops/`).

If you need **official `cloc` parity** (language breakdown with comment/code separation), install `cloc` in your runner image and exclude the same directories; the methodology above is optimized for **fast agent answers**, not ISO reporting.

### Agent triage notes (incremental, May 2026): pitfalls, sample hygiene, residual risk

This subsection records lessons from a focused repair pass (pytest + Playwright + PostgreSQL smoke). It **adds** to earlier guidance; it does not replace [TEST_EXECUTION_PITFALLS.md](TEST_EXECUTION_PITFALLS.md) or [TEST_INFERRED_RISKS_AND_FOLLOWUPS.md](../architecture/TEST_INFERRED_RISKS_AND_FOLLOWUPS.md).

#### A. Pitfalls encountered (test-operator / harness side) and how to avoid them

- **Playwright `webServer` + Python:** Managed E2E must use the **repository `.venv`** (or `E2E_PYTHON`) so `uvicorn` sees project deps — see Pitfall 11 in [TEST_EXECUTION_PITFALLS.md](TEST_EXECUTION_PITFALLS.md).
- **Element Plus roster-enroll table:** Do not use `click({ force: true })` on **selection checkboxes** then `force` the primary button; selection may not update, the submit stays **disabled**, and `waitForResponse` times out with **no POST**. Prefer a normal checkbox click, then **`expect(btn-roster-enroll-submit).toBeEnabled()`** before pairing `waitForResponse` with submit — see Pitfall 40.
- **Concurrent discussion list assertions:** The API orders by **`(created_at, id)`**. On PostgreSQL, **serial `id` order can diverge** from insert wall-clock order under concurrent threads; asserting **sorted ids alone** can false-fail. Assert **lexicographic order of `(created_at, id)`** or match the API contract explicitly.
- **`metadata.drop_all()` on PostgreSQL:** FKs declared with SQLAlchemy **`use_alter=True`** may produce **unnamed** constraints and break `drop_all` during test resets. The suite uses **`tests/db_reset.py`** (`DROP SCHEMA public CASCADE` for non-SQLite) — keep new DB resets aligned with that helper when using Postgres.
- **Parallel pytest + single `TEST_DATABASE_URL`:** Two processes resetting the same Postgres schema cause **nondeterministic failures**. Run **one** full-suite Postgres job at a time per database.

**Preferred toolchain for serious regression (principle):** install **`unrar`** (for RAR attachment regression tests) and run **`pytest` with `TEST_DATABASE_URL` pointing at PostgreSQL** so dialect-specific guards (e.g. `information_schema`, transactional visibility, uniqueness behavior) execute instead of skipping. SQLite remains the default fast loop for everyday edits.

#### B. Guidance for future test samples; redundancy and refinement

- **Confirm HTTP contracts before scripting:** Path, verb, query vs body, and **`Query(..., le=)`** bounds must match routers — copy-pasting `page_size=200` across routes causes false reds when one route allows **1000** (students) and another **100** (logs). Prefer a **small shared table** `(path, max_page_size)` in specs or grep routers once.
- **Prefer stable hooks:** `data-testid`, seeded scenario helpers (`enterSeededRequiredCourse`), and API-first assertions before fragile UI copy.
- **Overlap without deleting:** `e2e-pitfall-guard-rails*.spec.js`, `e2e-cross-cutting-tier*.spec.js`, and `future-advanced-coverage*.spec.js` intentionally overlap on invariants (pagination, auth). Before adding a file, **grep for the same invariant**; extend or parameterize rather than fork a fourth parallel guard file unless the scenario is genuinely new.
- **Admin sidebar labels (LLM triage):** As of the `2026-05` navigation consolidation in `apps/web/admin/src/views/Layout.vue`, the student root entry **我的课程** was renamed **选课与进度** (route `/courses` unchanged). E2E that assert visible Chinese text for the old label may need to target **选课与进度** or rely on `page.goto('/courses')` / `data-testid` instead of menu title strings. See [HISTORICAL_CODE_CLEANUP.md](HISTORICAL_CODE_CLEANUP.md) §5.
- **Samples that deserve refinement when touched:** Very broad Playwright regexes (e.g. `/密码/` on settings), **`textarea:first()`** on homework submit (discussion vs submission — use `homework-submit-content`), and **unscoped `tr:has-text(course)`** on **我的课程** (catalog vs cards — scope to `.elective-catalog-card`).
- **Automated redundancy policy:** Deletions still go through [TEST_REDUNDANCY_AUDIT.md](TEST_REDUNDANCY_AUDIT.md) and `tests/TEST_PROTECTION_RULES.json`; overlap is a **review signal**, not an automatic delete list.

#### C. Residual product / architecture concerns (from tests, not a confirmed bug list)

- **Startup and lifespan coupling:** Heavy bootstrap (schema repair, reconciliation, optional worker) increases **order-dependent** and **environment-sensitive** failure modes; failures often present as **health/E2E boot** issues rather than the edited feature — see existing P1 items in [TEST_INFERRED_RISKS_AND_FOLLOWUPS.md](../architecture/TEST_INFERRED_RISKS_AND_FOLLOWUPS.md).
- **Notification read-state under concurrency:** Dual-tab mark-all-read remains a **high flake/risk** surface; distinguish **API truth** vs **UI convergence** under automation.
- **SQLite vs PostgreSQL semantics:** Transaction boundaries, uniqueness timing, and **`SERIAL`** vs SQLite autoincrement can diverge; Postgres-only paths deserve **periodic** CI or manual smoke with `TEST_DATABASE_URL`.
- **Large orchestration modules (`llm_grading`, heavy routers):** Fixes in one branch of grading or roster flows can **couple** unexpectedly — prefer **narrow pytest** for extracted helpers when refactoring.

**New focused suites (additive):**

- `tests/postgres/test_postgres_dialect_guards.py` — dialect and transactional guards that **skip on SQLite** unless `TEST_DATABASE_URL` is PostgreSQL (see `tests/postgres/conftest.py`).
- `tests/postgres/test_postgres_llm_schema_and_policy.py` — LLM **schema shape** guards (`information_schema`, FK `ON DELETE CASCADE`, nullable attribution columns).
- `tests/postgres/test_postgres_quota_api_and_constraints.py` — fifteen **HTTP + SQL** hazard checks for quota policy, course LLM boundaries, uniqueness, and FK violations.
- `tests/e2e/web-admin/e2e-agent-followup-batch.spec.js` — ten API/navigation checks complementary to pitfall rails.
- `tests/e2e/web-admin/e2e-postgres-hazard-tier.spec.js` — fifteen **API + UI** checks for global quota vs course LLM (see subsection **4** above for commands).
- `tests/e2e/web-admin/e2e-agent-hazard-tier-15.spec.js` — fifteen **API-only** Playwright checks (pagination `422` boundaries, LLM admin vs student, parallel `mark-all-read`, E2E seed header gates, `forgot-password` empty username, registration disabled). Same seed contract as other web-admin E2E; run **serially** (Pitfall 41).
- `tests/backend/e2e_dev/test_e2e_dev_api_hazard_tier.py` — fifteen **pytest + TestClient** checks against `/api/e2e/dev/*` and cross-actor HTTP edges using the same DB reset as `test_e2e_dev_seed.py` (no Playwright; fast in CI when `E2E_DEV_SEED_ENABLED` is toggled per test).
- `tests/security/test_security_regression.py` — twenty API security-boundary checks (admin vs teacher vs student, unauthenticated paths, invalid JWT).
- `ops/scripts/dev/provision_postgres_pytest.sh` — idempotent **throwaway PostgreSQL** role+database for zero-skip full `pytest` (see Cross-platform smoke expectations above and **Pitfall 45** in [TEST_EXECUTION_PITFALLS.md](TEST_EXECUTION_PITFALLS.md)).

#### D. Agent hazard pass (additive, May 2026): new tests, pitfalls observed, worries, coverage gaps

This subsection documents a follow-up **hazard-tier** pass that added **15 Playwright API tests** and **15 pytest E2E-dev API tests** (see file list under “New focused suites”). It is written primarily for LLM agents that need searchable, exhaustive context; humans may skim headings.

##### D1. Commands used to validate the new modules

```bash
# Fast pytest module (resets DB per test via e2e_dev fixtures; ~20s typical)
cd <REPO_ROOT>
python3 -m pytest tests/backend/e2e_dev/test_e2e_dev_api_hazard_tier.py -q

# Playwright file (requires globalSetup + E2E_DEV_SEED_TOKEN; run alone — Pitfall 41)
cd <REPO_ROOT>/apps/web/admin
CI=1 E2E_PYTHON=<REPO_ROOT>/.venv/bin/python npx playwright test e2e-agent-hazard-tier-15.spec.js --project=chromium
```

##### D2. Pitfalls encountered while authoring these tests (concrete)

1. **Discussion list `page_size` vs FastAPI `Query(le=...)`:** `GET /api/discussions` declares `page_size: Optional[int] = Query(None, ge=1, le=100)`. Values **above 100** therefore return **422** before the handler’s internal clamp (`_resolve_page_size` maps into `[MIN_PAGE_SIZE, MAX_PAGE_SIZE]`). A hazard test that expected “HTTP 200 + clamped page_size” for `page_size=200` would be **wrong** for this router — the correct high-difficulty assertion on the allowed branch is `page_size=100` → **200 OK** with `page_size <= 50` in the JSON body. This mirrors the general rule in subsection **B**: always grep the router for `Query(..., le=)` before scripting pagination edge cases.

2. **`httpx` / Starlette deprecation when using `TestClient.post(..., data=bytes)`:** Passing raw form bytes via the `data=` parameter on `TestClient` can trigger `DeprecationWarning: Use 'content=<...>' to upload raw bytes`. Prefer `content=body.encode("utf-8")` with `Content-Type: application/x-www-form-urlencoded` for OAuth2-style login in pytest (fixed in `test_e2e_dev_api_hazard_tier.py::_login_form`).

3. **E2E seed token header is mandatory for every `/api/e2e/dev/*` call:** Even when `E2E_DEV_SEED_ENABLED` is true in tests, omitting `X-E2E-Seed-Token` must yield **403** (not 404) on guarded dev routes — this is part of the contract validated by `test_hz03` and the Playwright case `08`.

4. **Student quota endpoints are student-only:** Teachers receive **403** on `/api/llm-settings/courses/student-quotas` and `/api/llm-settings/courses/student-quota/{subject_id}` — do not assume instructors can “inspect student quota for debugging” without an explicit admin/teacher API (the hazard tests encode the current contract).

5. **Parallel `mark-all-read`:** After the server-side upsert hardening (Round-4 continuation), issuing **two concurrent** `POST /api/notifications/mark-all-read` from the same student token should both return **200** and leave `sync-status.unread_count === 0`. If either request fails with `IntegrityError` in logs, that is a **regression** in the batch upsert path, not a flake.

6. **Playwright scripts must match real admin LLM quota routes:** An early draft of `e2e-agent-hazard-tier-15.spec.js` called `POST /api/llm-settings/admin/quota-overrides/students`, which **does not exist** (HTTP **404**). The repository exposes **`PUT /api/llm-settings/admin/students/{student_id}/quota-override`** for a single student and **`POST /api/llm-settings/admin/quota-overrides/bulk`** for scoped bulk updates (`LLMQuotaBulkOverrideRequest`). Before writing E2E against admin quota mutations, run `rg "quota-override" apps/backend/wailearning_backend/api/routers/llm_settings.py` and copy the exact path + verb from the router.

##### D3. “Worries” from this pass (planning signals, not confirmed defects)

- **Playwright-only API tests still depend on globalSetup:** If `E2E_DEV_SEED_TOKEN` is missing, the entire describe block skips — CI must export the token for hazard-tier Playwright files the same way as `e2e-postgres-hazard-tier.spec.js`.
- **pytest `TestClient` + full app import:** The `tests/backend/e2e_dev/*` modules import `main:app` after `tests/conftest.py` sets `DATABASE_URL`. If a future refactor moves engine creation **before** env setup, imports could fail with empty URL errors — keep `tests/conftest.py` at the top of the pytest plugin order (repository root `conftest.py` is Windows-only temp hacks; `tests/conftest.py` owns `DATABASE_URL`).
- **Public registration test (`hz10` Playwright):** When `ALLOW_PUBLIC_REGISTRATION` is false (default), `POST /api/auth/register` returns **403**. If an environment enables public registration for experiments, the same test accepts **400** (validation) as an alternate success class — agents should not treat “400 vs 403” as a product regression without reading `settings.ALLOW_PUBLIC_REGISTRATION`.

##### D4. Coverage gaps explicitly *not* closed by these 30 tests

- **Parent portal** and **mobile viewport** hazard coverage remain thin; new tests target admin/teacher/student API edges on the **admin-seeded** scenario only.
- **Real SMTP / password reset email** flows are not exercised (`forgot-password` only checks empty username returns a safe 200 message).
- **Multi-worker Gunicorn** LLM worker leader election, wall-clock stale reclaim, and cross-process file locking are not represented in Playwright or the 15-pytest dev module.
- **Production `APP_ENV`** cannot be covered by the dev-seed tests; production gating remains documented in subsection **2d** (`expose_e2e_dev_api`, router dependency).

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
