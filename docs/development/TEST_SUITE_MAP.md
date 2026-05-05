# Test Suite Map

## Purpose

This document explains how the repository test suites are organized after the domain-oriented cleanup of the `tests/` tree.

It is intended for contributors and LLM coding agents who need to answer questions such as:

- which tests should be read first for a given feature,
- which suites are fast versus operationally fragile,
- which files are reusable helpers versus actual pytest entrypoints,
- which categories are most likely to fail because of environment issues rather than product regressions.

## Top-Level Test Layout

  ```text
  tests/
    backend/                  focused backend pytest modules grouped by domain
    behavior/                 high-level multi-actor and workflow pytest suites
    postgres/                 PostgreSQL-only guards (skip unless Postgres: TEST_DATABASE_URL or WAILEARNING_AUTO_PG_TESTS=1 after provision script)
    security/                 API authorization / abuse-edge regression (roles, tokens)
    e2e/web-admin/            Playwright browser coverage for the admin SPA
  fixtures/                 static files used by tests
  scenarios/                shared scenario builders and stress helpers
  conftest.py               repository test environment defaults
```

## Category Overview

### `tests/backend/`

This directory contains focused backend pytest modules. These tests usually exercise one domain at a time and are the best first stop when a code change is narrow.

Subgroups:

- `tests/backend/llm/`
  - LLM grading worker behavior
  - endpoint routing
  - quota logic
  - payload normalization
  - attachment format extraction
- `tests/backend/homework/`
  - homework lifecycle rules
  - submission limits
  - grading and appeal flows
  - markdown visibility behavior
- `tests/backend/courses/`
  - course access
  - roster versus course enrollment behavior
  - required versus elective rules
- `tests/backend/roster/`
  - roster enroll operations
  - batch class changes
  - student-user synchronization
  - import behavior
- `tests/backend/files/`
  - attachment serving and download authorization
  - upload compliance allow-list and sniffing (`test_attachment_upload_compliance.py`)
- `tests/backend/content_format/`
  - optional `content_format` / `body_format` persistence on homework, submissions, discussions, notifications

### HTTP client UX (admin SPA)

See [HTTP client slow-response busy hint](HTTP_CLIENT_SLOW_RESPONSE_BUSY_HINT.md) for the 3s “系统正忙，请等待。” message on `http` / `httpQuiet` / `httpPublic`.
- `tests/backend/scores/`
  - score composition and derived grading behavior
- `tests/backend/points/`
  - points routes and points-related permissions
- `tests/backend/system/`
  - production settings and environment constraints
- `tests/backend/e2e_dev/`
  - E2E seed helpers
  - demo course bootstrap behavior
  - LLM mock/reset support used by browser flows
- `tests/backend/manual/`
  - smoke-style API coverage that preserves behavior previously exercised by manual scripts
- `tests/backend/user_profile/`
  - profile and avatar flows

### `tests/behavior/`

This directory contains higher-level pytest suites that combine multiple features, roles, or temporal phases in one scenario.

Typical characteristics:

- longer setup than focused backend tests,
- more cross-feature coupling,
- better at catching regressions in state convergence,
- harder to triage when they fail because one bug can surface deep into the scenario.

### `tests/e2e/web-admin/`

This directory contains Playwright browser coverage for the admin frontend.

These tests are the closest to a user-visible workflow because they exercise:

- backend startup,
- frontend startup,
- E2E seed/reset helpers,
- browser automation,
- UI-to-API convergence.

Additional targeted suite: **`e2e-discussion-cover-llm-tier3.spec.js`** — discussion LLM (`invoke_llm`), long reply preview (3 logical lines + expand), and course cover (API + UI). Run only that file with `npx playwright test e2e-discussion-cover-llm-tier3.spec.js` from `apps/web/admin` when iterating on those features.

Another targeted suite: **`e2e-homework-comment-cover-tier4.spec.js`** (15 cases) — homework submission table **content/comment preview** truncation, **LLM grading** long comments + regrade + 429 recovery, **multi-role** API guards, and **course cover** flows (teacher/admin UI + API). Run alone with `npx playwright test e2e-homework-comment-cover-tier4.spec.js` from `apps/web/admin`.

They also have the highest dependence on the local execution environment.

This directory also contains a future-coverage expansion file pair:

- `tests/e2e/web-admin/future-advanced-coverage.spec.js`
- `tests/e2e/web-admin/future-advanced-coverage-2.spec.js`

In this branch, those files are no longer placeholders. They contain real `test(...)` bodies and participate in normal `npm run test:e2e` runs.

How to interpret them correctly:

- they still function as a bank of higher-difficulty scenarios
- they are now part of actual runnable regression coverage, not a skipped queue
- historical references to `E2E_ENABLE_BACKLOG_SPECS` apply only when reading older branches that still carried skipped placeholders

Operational summary:

- Helpers: `tests/e2e/web-admin/future-advanced-coverage-helpers.cjs`
- Runtime contract: same Playwright config, same `globalSetup`, and the same `/api/e2e/dev/reset-scenario` seed/reset flow as the other admin E2E specs
- Historical workflow and old placeholder interpretation: [E2E_BACKLOG_SCENARIOS.md](E2E_BACKLOG_SCENARIOS.md)

### `tests/scenarios/`

This directory contains reusable helper modules rather than primary pytest discovery targets.

Current examples:

- `llm_scenario.py`
  - common login helpers
  - grading-course setup helpers
  - scenario factories reused by many backend and behavior tests
- `material_flow.py`
  - helper setup for material, chapter, and notification flows

Historical note (cleanup `2026-05-05`):

- `tests/scenarios/llm_pressures.py` was removed after verification that **nothing imported it**
  (no test module, script, or documentation referenced its symbols). The repository already
  exercises heavy LLM scenarios through `tests/backend/llm/test_llm_stress_scenarios.py`,
  `test_llm_concurrency_scenarios.py`, and related behavior suites. If a future maintainer
  needs a dedicated pressure harness again, reintroduce it as an imported module with at least
  one pytest entrypoint or an explicit import from an existing test file so it cannot rot unseen.

Import paths:

- Prefer **`from tests.scenarios.llm_scenario import ...`** and
  **`from tests.scenarios.material_flow import ...`** in new code.
- Root-level compatibility stubs **`tests/llm_scenario.py`**, **`tests/material_flow.py`**,
  and **`tests/llm_pressures.py`** were removed in the same cleanup; older branches that still
  reference those paths must be updated when merged forward.

RAR attachment regression assets:

- Binary fixtures under **`tests/fixtures/llm_rar/`** (`unencrypted_nested_zip.rar`,
  `password_protected.rar`) supply archives for `tests/backend/llm/test_llm_attachment_formats.py`
  so those tests run **without** shelling out to the **`rar`** CLI at test time. Regeneration
  requires **`rar`** on `PATH` (same commands historically embedded in the test body); keep
  committed bytes UTF-8-clean and treat the directory as test assets, not runtime product data.

Another targeted suite: **`e2e-agent-followup-batch.spec.js`** (10 cases) — additive API/navigation checks (pagination boundaries, health, settings public, course entry). Run alone with `npx playwright test e2e-agent-followup-batch.spec.js` from `apps/web/admin`.

Another additive hazard file: **`e2e-agent-hazard-tier-15.spec.js`** (15 cases) — API-only checks for authz edges, LLM admin vs student boundaries, parallel `mark-all-read`, and E2E dev seed header gates. Same globalSetup contract as `e2e-postgres-hazard-tier.spec.js`; run serially (Pitfall 41).

### Coverage gap addressed in May 2026 (notification header badge + sync-status)

Earlier Playwright suites exercised **`POST /api/notifications`** and list/mark-read flows extensively, but **did not systematically assert** the admin SPA header surfaces documented in [NOTIFICATION_HEADER_AND_REALTIME_SYNC.md](NOTIFICATION_HEADER_AND_REALTIME_SYNC.md):

- `data-testid="header-notification-badge"` (Element Plus badge content vs `sync-status.unread_count`),
- course-scoped unread when **`header-course-switch`** changes `selectedCourse` (maps to `subject_id` on `syncStatus`),
- convergence after **`window.dispatchEvent(new Event('focus'))`** (same hook as user returning to the tab — exercises `pollNotificationSync` without waiting `DEFAULT_NOTIFICATION_POLL_INTERVAL_MS`).

**New Playwright module (10 cases):** `tests/e2e/web-admin/e2e-notification-header-sync-tier.spec.js`

**Deeper follow-up (15 cases):** `tests/e2e/web-admin/e2e-notification-sync-deep-tier.spec.js` — admin global totals vs list, teacher explicit course switch before badge asserts, corrupt `selected_course` healing, concurrent publishes, cross-teacher isolation, mobile viewport, reload-based cold poll, delete race on `/notifications`. Run alone:

```bash
cd <REPO_ROOT>/apps/web/admin
CI=1 E2E_PYTHON=<python-with-requirements> E2E_DEV_SEED_TOKEN=<seed> \
  npx playwright test e2e-notification-sync-deep-tier.spec.js --project=chromium
```

- Run from `<REPO_ROOT>/apps/web/admin` (same `playwright.config.cjs` as other admin E2E):

```bash
cd <REPO_ROOT>/apps/web/admin
CI=1 E2E_PYTHON=<python-with-requirements> E2E_DEV_SEED_TOKEN=<seed> \
  npx playwright test e2e-notification-header-sync-tier.spec.js --project=chromium
```

**New behavior pytest module (10 cases):** `tests/behavior/test_notification_sync_api_edge_behavior.py`

- Stresses **HTTP contract alignment** between `GET /api/notifications` aggregates and `GET /api/notifications/sync-status`, plus concurrent writers/readers and **403** when a student passes a **foreign** `subject_id`.
- Uses the standard `tests/behavior/conftest.py` reset (SQLite by default); run:

```bash
cd <REPO_ROOT>
python3 -m pytest tests/behavior/test_notification_sync_api_edge_behavior.py -q
```

Operational notes for agents authoring similar specs live under **“Pitfall 50”** in [TEST_EXECUTION_PITFALLS.md](TEST_EXECUTION_PITFALLS.md) (secondary-browser-tab login, disabled course-card affordances after `/courses`, badge vs API race windows).

### `tests/postgres/`

Small pytest package gated by dialect: when the effective engine is **not** PostgreSQL, tests **skip** at module level (set `TEST_DATABASE_URL`, or on Linux/macOS after `ops/scripts/dev/provision_postgres_pytest.sh` set **`WAILEARNING_AUTO_PG_TESTS=1`** so `tests/conftest.py` auto-selects the standard throwaway URL). Use for `information_schema`, transactional visibility, and uniqueness smoke that SQLite does not model the same way. See `tests/postgres/conftest.py` and `docs/development/DEVELOPMENT_AND_TESTING.md` (agent triage subsection).

Files:

- `test_postgres_dialect_guards.py` — broad dialect and API smoke guards.
- `test_postgres_llm_schema_and_policy.py` — **LLM quota schema** guards (`llm_global_quota_policies`, `course_llm_configs` column set, preset FK `ON DELETE CASCADE`, `get_or_create_global_quota_policy` ORM read).
- `test_postgres_quota_api_and_constraints.py` — **HTTP + SQL hazard** module (admin `422` paths, auth edges, duplicate `course_llm_config_endpoints`, enrollment uniqueness, orphan FK attempts). Uses the shared `client` fixture from `tests/postgres/conftest.py` (PostgreSQL-only autouse reset).

### `tests/security/`

API-level **authorization and abuse-edge** regression tests (unauthenticated vs role boundaries, admin-only routes, cross-tenant homework/parent-code actions, invalid tokens). Uses the same DB reset contract as `tests/behavior/`. Run targeted: `python -m pytest tests/security/ -q`.

## Recommended Reading Order By Task

### If you are changing LLM logic

Read and run in this order:

1. `tests/scenarios/llm_scenario.py`
2. `tests/backend/llm/`
3. `tests/backend/homework/test_homework_llm_grading.py`
4. `tests/behavior/test_*llm*`
5. `tests/e2e/web-admin/homework-llm-routing.spec.js`

### If you are changing course or roster behavior

Read and run in this order:

1. `tests/backend/courses/`
2. `tests/backend/roster/`
3. `tests/behavior/test_multi_actor_timeline_behavior.py`
4. `tests/e2e/web-admin/roster-and-users.spec.js`

### If you are changing homework, notifications, or materials

Read and run in this order:

1. `tests/backend/homework/`
2. `tests/scenarios/material_flow.py`
3. `tests/behavior/test_material_chapters_notifications_homework_flow.py`
4. `tests/e2e/web-admin/ui-homework-student-actions.spec.js`

## Which Tests Are Usually Easier To Pass

The easiest suites to keep green are usually the narrowly scoped backend tests in:

- `tests/backend/system/`
- `tests/backend/files/`
- `tests/backend/points/`
- smaller parts of `tests/backend/courses/`

Reasons:

- limited concurrency,
- fewer moving pieces,
- little or no browser/runtime orchestration,
- less dependence on long scenario setup.

## Which Tests Are Harder To Pass

The more difficult or fragile categories are usually:

### 1. Playwright browser E2E

Files under `tests/e2e/web-admin/` are the hardest operationally because they depend on:

- backend boot,
- frontend boot,
- port availability,
- Playwright worker startup,
- seed/reset endpoints,
- browser-driver availability,
- timing across UI and API layers.

These tests are often the first place where Windows + PowerShell environment issues appear.

### 2. Behavior suites with multi-actor timelines

Examples from `tests/behavior/` are hard because they combine:

- multiple roles,
- staged mutations over time,
- read-state convergence,
- deduplication or reconciliation rules,
- a larger blast radius when one prerequisite silently diverges.

### 3. LLM concurrency and stress tests

Representative files include:

- `tests/backend/llm/test_llm_concurrency_scenarios.py`
- `tests/backend/llm/test_llm_stress_scenarios.py`

These are harder because they depend on:

- async or queue-backed behavior,
- retries and quota boundaries,
- ordering assumptions,
- state convergence after concurrent operations.

### 4. Seed/bootstrap-coupled backend tests

Files under `tests/backend/e2e_dev/` can be harder than normal unit-style backend tests because they touch:

- reset endpoints,
- demo seed data,
- startup assumptions,
- test-environment feature flags.

The module **`test_e2e_dev_api_hazard_tier.py`** adds fifteen **TestClient** checks that chain `reset-scenario` with cross-role HTTP calls (seed token gates, teacher vs student LLM quota routes, parallel `mark-all-read`, homework delete authz). It shares the same per-test DB reset pattern as `test_e2e_dev_seed.py`.

## Operational Advice

When a change is small, do not start with the hardest suites.

Prefer this escalation order:

1. relevant `tests/backend/<domain>/`
2. relevant `tests/behavior/`
3. one targeted Playwright spec
4. broader Playwright coverage if needed

If Playwright fails first, read [TEST_EXECUTION_PITFALLS.md](TEST_EXECUTION_PITFALLS.md) before assuming the product is broken.

### Linux / CI agents

The same escalation order applies. Additional traps that showed up outside the original Windows-focused validation — managed Playwright `webServer` using a system Python without `uvicorn`, Element Plus message-box locale vs Chinese labels, strict-mode duplicate text matches, homework submit vs discussion `textarea` ordering, materials list `page_size` vs API `le=` limits — are recorded as Pitfalls 11–16 in [TEST_EXECUTION_PITFALLS.md](TEST_EXECUTION_PITFALLS.md). Suspected product or structural weaknesses inferred during full-suite repair are accumulated in [../architecture/TEST_INFERRED_RISKS_AND_FOLLOWUPS.md](../architecture/TEST_INFERRED_RISKS_AND_FOLLOWUPS.md), including a short next-regression-pass checklist.
