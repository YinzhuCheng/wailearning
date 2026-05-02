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

Those files are intentionally checked in as a bank of higher-difficulty E2E scenarios. They are **not** treated as validated regression coverage until individually implemented.

Revision note: once **`future-advanced-coverage*.spec.js`** contains **`test(...)` bodies** (with **`future-advanced-coverage-helpers.cjs`** support), they participate in normal **`npm run test:e2e`** runs alongside other specs in **`tests/e2e/web-admin/`**; the **`E2E_ENABLE_BACKLOG_SPECS`** gate described below is legacy for branches that still carried skipped placeholders.

Those files are intentionally checked in as a bank of higher-difficulty E2E scenarios and are currently marked `skip` so the cases exist in the repository without being treated as already-validated regression coverage. Default Playwright runs still skip the backlog describes unless **`E2E_ENABLE_BACKLOG_SPECS`** is truthy; see [E2E_BACKLOG_SCENARIOS.md](E2E_BACKLOG_SCENARIOS.md) for the updated mechanism.

Operational summary:

- **`E2E_ENABLE_BACKLOG_SPECS`** — When unset/falsy, the backlog suite describes are registered as skipped so default Playwright runs match only implemented specs (~60 tests instead of ~90 placeholder rows). When truthy, the backlog describes run and each scenario reports skipped with a documented placeholder reason until replaced by real `test(...)` implementations.
- Helpers: **`tests/e2e/web-admin/future-advanced-coverage-helpers.cjs`** (when scenarios are implemented); legacy helper **`tests/e2e/web-admin/backlog-e2e.cjs`** applied only to older skipped-placeholder revisions.
- Full scenario index and workflow: [E2E_BACKLOG_SCENARIOS.md](E2E_BACKLOG_SCENARIOS.md).

### `tests/scenarios/`

This directory contains reusable helper modules rather than primary pytest discovery targets.

Current examples:

- `llm_scenario.py`
  - common login helpers
  - grading-course setup helpers
  - scenario factories reused by many backend and behavior tests
- `material_flow.py`
  - helper setup for material, chapter, and notification flows
- `llm_pressures.py`
  - heavier stress-style scenarios and reusable workload patterns

Compatibility re-export modules remain at:

- `tests/llm_scenario.py`
- `tests/material_flow.py`
- `tests/llm_pressures.py`

These stubs exist so older imports keep working while the actual helper code lives under `tests/scenarios/`.

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
- `tests/scenarios/llm_pressures.py`

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

## Operational Advice

When a change is small, do not start with the hardest suites.

Prefer this escalation order:

1. relevant `tests/backend/<domain>/`
2. relevant `tests/behavior/`
3. one targeted Playwright spec
4. broader Playwright coverage if needed

If Playwright fails first, read [TEST_EXECUTION_PITFALLS.md](TEST_EXECUTION_PITFALLS.md) before assuming the product is broken.

### Linux / CI agents

The same escalation order applies. Additional traps that showed up outside the original Windows-focused validation—managed Playwright `webServer` using a system Python without `uvicorn`, Element Plus message-box locale vs Chinese labels, strict-mode duplicate text matches, homework submit vs discussion `textarea` ordering, materials list `page_size` vs API `le=` limits—are recorded as Pitfalls 11–16 in [TEST_EXECUTION_PITFALLS.md](TEST_EXECUTION_PITFALLS.md). Suspected product or structural weaknesses inferred during full-suite repair are accumulated in [../architecture/TEST_INFERRED_RISKS_AND_FOLLOWUPS.md](../architecture/TEST_INFERRED_RISKS_AND_FOLLOWUPS.md), including a short **next regression pass** checklist.
