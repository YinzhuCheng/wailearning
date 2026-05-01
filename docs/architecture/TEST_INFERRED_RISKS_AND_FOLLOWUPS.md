# Test-Inferred Risks And Follow-Ups

## Purpose

This document records repository weaknesses, suspected bugs, and structural risks inferred during the May 1, 2026 repository-refactor validation pass.

A later full-suite repair pass (May 2026, Linux/CI-style execution with Playwright + pytest) added a few more items: same schema as below—`Observed`, `Strong inference`, or `Structural risk`—and the same disclaimer: not a confirmed defect list.

This is not a list of confirmed product defects. It is a focused backlog of areas that felt risky under real test pressure and therefore deserve deliberate follow-up.

Where possible, each item is labeled as one of:

- `Observed`: directly seen in tests or runtime behavior
- `Strong inference`: not proven in isolation, but strongly suggested by behavior or structure
- `Structural risk`: maintainability or correctness risk implied by current code shape

## Priority Interpretation

- `P1`: likely user-facing correctness risk or important flake source
- `P2`: meaningful technical risk that can hide future bugs
- `P3`: structural debt worth scheduling but not necessarily urgent

## P1: notification mark-all-read dual-tab convergence remains suspicious

### Type

`Observed`

### Evidence

During the full Playwright validation after the repository restructure, exactly one scenario failed:

- `tests/e2e/web-admin/e2e-scenario-resilience.spec.js`
- scenario: `dual-tab student mark-all-read leaves every fresh course notification read`

The failure mode was:

- the expected read/mark button remained disabled long enough to hit the test timeout

The same scenario passed immediately when rerun in isolation on a fresh isolated stack.

### Interpretation

This looks like one of the following:

- a genuine race in notification read-state convergence,
- UI state derived from stale store/cache state,
- insufficient server-side idempotency under concurrent read operations,
- or a flaky test that is exposing a real timing sensitivity in the product.

### Why this matters

This scenario is exactly the kind of state-convergence bug that real users hit in multiple tabs.

### Follow-up

- instrument notification mark-all-read server responses under concurrent access
- inspect frontend disabled/enabled state transitions around the read action
- verify whether the authoritative backend state was actually correct when the UI timed out
- run this scenario repeatedly in isolation and in-suite to measure flake rate

## P1: backend import/startup path is too side-effect-heavy

### Type

`Strong inference`

### Evidence

The backend still depends on `uvicorn app.main:app`, but importing `app.main` is not a cheap or purely declarative step:

- database setup behavior exists at module import time
- startup-related code paths are tightly coupled to database availability
- compatibility shims were needed to preserve the old import path after moving the backend package

### Why this matters

Heavy import-time side effects make all of these harder:

- testing
- scripting
- background worker separation
- migration to cleaner package layouts
- isolated imports for tooling

### Follow-up

- remove nontrivial side effects from module import paths
- ensure app construction is separate from schema/bootstrap activity
- make `app.main` import-safe without requiring environment assumptions

## P1: backend startup and bootstrap concerns are too intertwined

### Type

`Structural risk`

### Evidence

From the code shape and startup behavior:

- schema updates
- normalization jobs
- data backfills
- roster reconciliation
- optional demo seed
- optional LLM worker startup

are all clustered around startup/bootstrap flow.

### Why this matters

This increases the chance of:

- startup regressions that are hard to isolate
- order-dependent bugs
- environment-sensitive behavior differences between tests, local dev, and production
- one-off fixes being added to startup until it becomes unreasonably fragile

### Follow-up

- split bootstrap responsibilities into explicit phases
- separate one-time repair tasks from every-startup tasks
- define which startup behaviors are safe in production, in tests, and in seed-only flows

## P1: the LLM subsystem is functionally rich but structurally too concentrated

### Type

`Structural risk`

### Evidence

`apps/backend/app/llm_grading.py` is very large and sits in the middle of:

- grading execution
- attachment handling integration
- retry behavior
- routing
- quota interactions
- worker behavior
- persistence/state transitions

### Why this matters

Large central modules tend to accumulate hidden coupling and make bug isolation expensive.

### Likely symptom class

- fixes in one branch of grading logic accidentally affecting another
- recovery/retry paths diverging from first-pass grading behavior
- hard-to-predict behavior under concurrent or partial-failure conditions

### Follow-up

- identify coherent submodules such as worker orchestration, grading normalization, endpoint execution, and persistence transitions
- shrink the public surface of the central grading module
- add narrower unit tests around extracted sub-behaviors

## P2: Windows test stability currently depends on repository-side pytest workarounds

### Type

`Observed`

### Evidence

The full backend suite only became stable on this machine after adding Windows-specific temp-directory handling in repository-level test bootstrap.

### Interpretation

Even if these workarounds are acceptable for this environment, they are a signal that the current test harness is sensitive to platform-specific runner behavior.

### Why this matters

Fragile test infrastructure can mask real regressions by flooding maintainers with environmental failures.

### Follow-up

- decide whether these Windows test bootstrap workarounds should remain long-term
- document the intended Windows support level explicitly
- consider whether CI should exercise Windows regularly if Windows remains a first-class development environment

## P2: frontend and E2E coupling is still operationally complex

### Type

`Strong inference`

### Evidence

To get reliable Playwright runs, the current setup needs careful control of:

- backend process startup
- Vite startup
- browser cache path
- API URL
- base URL
- worker mode
- external-server mode

### Why this matters

The more fragile the boot choreography is, the easier it is for real regressions to be hidden by harness noise.

### Follow-up

- simplify the browser-test startup contract
- reduce hidden assumptions in Playwright config
- consider a documented "known-good" local E2E launcher script for Windows

## P2: notification and appeal concurrency should remain a dedicated audit area

### Type

`Strong inference`

### Evidence

The test suite spends notable effort on:

- duplicate appeal creation
- read-state convergence
- concurrent actions from stale pages
- eventual authoritative state after retries/failures

That concentration usually means the codebase has already had to defend itself against concurrency-sensitive edge cases.

### Interpretation

Even where tests pass, these areas are likely to remain fragile and deserve ongoing regression attention.

### Follow-up

- keep concurrency scenarios in every serious regression pass
- inspect whether frontend optimistic state and backend authoritative state can temporarily diverge in user-visible ways
- audit whether conflict responses are consistently meaningful across related endpoints

## P2: route files still look too heavy in some domains

### Type

`Structural risk`

### Evidence

Several route modules remain large after the directory restructure, for example:

- homework
- scores
- subjects
- users

### Why this matters

Large route files often indicate mixed concerns:

- request validation
- authorization
- business rules
- persistence orchestration
- response shaping

### Follow-up

- keep moving business logic out of route modules
- use the new directory layout as an opportunity to continue domain extraction instead of stopping at filesystem renaming

## P2: the current `app` compatibility shim is practical but should not become permanent architecture

### Type

`Observed`

### Evidence

The repository now uses a thin root-level `app` package shim to preserve existing import paths while the real backend package lives under `apps/backend/app/`.

### Interpretation

This was the right move for a safe migration, but it is transitional architecture.

### Why this matters

If left indefinitely:

- packaging intent remains ambiguous
- import ownership stays conceptually split
- future tooling may continue to assume the old layout

### Follow-up

- decide whether the long-term import namespace stays `app`
- if yes, formalize it cleanly
- if no, plan a staged import-path migration instead of letting the shim quietly ossify

## P3: documentation and script path correctness will drift unless enforced

### Type

`Observed`

### Evidence

The repository reorganization required touching many docs and scripts because paths were hardcoded in:

- README content
- deployment docs
- git workflow docs
- Playwright config
- deploy scripts
- CI files

### Why this matters

The next layout change will create similar drift unless path assumptions are centralized or verified.

### Follow-up

- prefer shared variables or clearer conventions in scripts
- consider lightweight doc/script path checks in CI

## P2: Element Plus default locale can disagree with Chinese UI copy and tests

### Type

`Observed`

### Evidence

On a stock `app.use(ElementPlus)` setup without an explicit `locale`, `ElMessageBox` confirm/cancel may render English **OK** / **Cancel** while the rest of the app uses Chinese copy. E2E tests that target `确定` or disambiguate `关闭` can then fail for locale reasons, not product logic.

### Why this matters

- false failures in message-box flows (delete, confirm, etc.)
- dual close affordances in dialogs (header "close this dialog" vs footer primary button) already complicate `getByRole` matching

### Follow-up

- register a single application-wide Element Plus locale consistent with the product language, or
- make E2E match `aria` names from the active locale, or
- add `data-testid` on critical dialog actions if copy-based matching remains brittle

## P2: `course_enrollments` duplicate inserts can surface under startup reconciliation (especially SQLite)

### Type

`Observed` (during a May 2026 full-suite pass, fixed defensively in code) / `Strong inference` for long-term data model

### Evidence

Application lifespan runs `reconcile_student_users_and_roster`, which can invoke `prepare_student_course_context` / enrollment sync from multiple directions close together. In SQLite-heavy runs this produced `UNIQUE constraint failed: course_enrollments.subject_id, course_enrollments.student_id` during startup.

### Interpretation

Insertion paths were not all mutually aware of in-flight rows in the same session; relying on application-level "already enrolled" checks alone is brittle under parallel reconciliation.

### Why this matters

- startup failure blocks every endpoint including health checks and Playwright boot
- Postgres might mask different races than SQLite

### Follow-up

- consider DB-level idempotency (`INSERT OR IGNORE` semantics / upserts) where appropriate for enrollments
- audit all callers of enrollment sync for redundant work in one transaction
- keep SQLite in CI or smoke paths if it remains a supported dev/test database

## P2: client request `page_size` can drift above FastAPI validation limits

### Type

`Strong inference`

### Evidence

The materials list UI requested `page_size` larger than the route allows (`Query(..., le=100)` pattern). The failure mode was an empty UI table rather than an obvious inline validation message—easy to misread as "seed broken".

### Follow-up

- share numeric bounds between OpenAPI schema and frontend constants where feasible
- surface list API errors in UI dev flows when responses are 422

## P3: homework submit page places discussion textarea above submission textarea

### Type

`Structural risk`

### Evidence

Automations using `textarea:first()` targeted the discussion draft control instead of the homework submission body (`homework-submit-content`), producing confusing outcomes (no submission recorded).

### Follow-up

- treat `data-testid="homework-submit-content"` (and related submit affordances) as the stable contract for E2E
- consider a short note in teacher/student UI docs that two text areas exist on the same view

## Next full regression pass — extra focus (May 2026 addendum)

When re-running the full stack after changes to enrollment, materials, or internationalization:

1. **Startup / SQLite**: cold start or fresh E2E DB file after many `reset-scenario` cycles; watch for duplicate enrollment during `reconcile_student_users_and_roster`.
2. **Playwright + `webServer` on Linux/CI**: confirm the backend process uses the same Python environment as `pytest` (see [../development/TEST_EXECUTION_PITFALLS.md](../development/TEST_EXECUTION_PITFALLS.md) Pitfall 11).
3. **Message-box flows**: any change to Element Plus upgrade or locale config—re-smoke delete/confirm paths in admin.
4. **Homework + discussion**: any change to `HomeworkSubmission` layout—re-run a small E2E that both posts a discussion line and submits homework text.
5. **Materials list**: any change to list API limits or `Materials.vue` list parameters—verify a non-empty table with >0 materials for a seeded course.
6. **PostgreSQL-only pytest**: if schema columns are in scope, run with `TEST_DATABASE_URL` (or project Postgres) so `test_r3` in `test_regression_llm_quota_behavior` is not skipped by accident.

## P3: CI definitions were previously stale enough to reference invalid startup behavior

### Type

`Observed`

### Evidence

The previous pipeline files were not aligned with the current project shape and had to be rewritten during the restructure.

### Interpretation

CI drift had already accumulated before this change.

### Follow-up

- verify the rewritten CI definitions on the actual target CI platform
- ensure CI runs reflect the same entrypoints developers actually use

## Suggested Follow-Up Order

1. Investigate the dual-tab notification mark-all-read scenario until it is clearly classified as either a product race or a flaky test.
2. Reduce import-time and startup-time backend side effects.
3. Break down the LLM subsystem and heavy route modules into smaller, more testable pieces.
4. Decide the long-term fate of the root `app` compatibility layer.
5. Simplify the Playwright boot contract for Windows and document the canonical execution path.
6. Harden course enrollment creation so reconciliation cannot double-insert the same row (see P2 `course_enrollments` item above); re-validate on SQLite and Postgres.
7. Lock Element Plus locale (or E2E strategy) to avoid English message-box affordances in a Chinese UI.
8. After any API pagination limit change, grep the admin SPA for `page_size` and align client requests with server `le=` constraints.

## What This Document Is Not

- It is not a confirmed bug list.
- It is not a substitute for issue tracking.
- It is not a claim that every listed item currently causes user-visible failure.

It is a high-signal memory of where the system felt weakest while subjected to real validation pressure.
