---
name: admin-playwright-e2e
description: Use this when running, debugging, or documenting CourseEval admin Playwright E2E. Triggers include targeted spec runs, full admin browser validation, external-runner usage, seed/reset troubleshooting, port/process cleanup, and converting a repeatable browser workflow into durable repo guidance.
---

# Admin Playwright E2E

## Purpose

Run CourseEval admin Playwright with the repository's supported workflow instead
of ad hoc browser commands. Prefer the repo's external runner for real runs so
API/UI startup and teardown stay owned by one process.

## Workflow

1. Read `docs/testing/FULL_PLAYWRIGHT_E2E_RUNBOOK.md`,
   `docs/testing/TEST_EXECUTION_PITFALLS.md`, and
   `docs/testing/DEVELOPMENT_AND_TESTING.md`.
2. Confirm admin package dependencies and browsers exist in
   `apps/web/admin/`.
3. For a real targeted run, prefer the external runner from the admin package:
   `node scripts/playwright-external-runner.cjs <spec>.spec.js --project=chromium`
4. Use `tests/e2e/web-admin/fixtures.cjs` and
   `future-advanced-coverage-helpers.cjs` patterns before inventing new seed,
   login, or API helper flows.
5. If the browser scenario needs complex state, create it through seeded API
   helpers first, then assert the browser-visible outcome.
6. Record whether a failure came from product behavior, seed/reset, browser
   startup, stale ports, or teardown/cleanup.
7. Run external-runner commands serially when using the default ports/database.
   Parallel default runners can make Vite switch away from port 3012 while
   Playwright still navigates to 3012, and can lock the shared SQLite database.

## Commands

```powershell
cd apps/web/admin
npm.cmd ci
npx.cmd playwright install chromium
cd ..\..
python ops/scripts/dev/playwright_preflight.py --json
cd apps/web/admin
node scripts/playwright-external-runner.cjs roster-and-users.spec.js --project=chromium
node scripts/playwright-external-runner.cjs
```

## Guardrails

- Prefer `node scripts/playwright-external-runner.cjs ...` over managed
  `npx playwright test ...` for non-trivial local runs.
- Keep `E2E_DEV_SEED_TOKEN`, `E2E_API_URL`, and `PLAYWRIGHT_BASE_URL`
  consistent with the runner flow; do not hand-roll mixed startup modes.
- Do not start two `npm.cmd run test:e2e:external -- ...` commands in parallel
  on the default ports. If parallelism is required, assign distinct
  `E2E_API_PORT`, `E2E_UI_PORT`, and database paths per process.
- Reuse fixture helpers before adding bespoke login or seed code.
- For API-heavy browser scenarios, assert the API-side precondition before
  blaming a missing UI row.
- Treat spawn errors, missing browsers, stale ports, or teardown timeouts as
  harness signals first.

## Related Files

- `apps/web/admin/scripts/playwright-external-runner.cjs`
- `apps/web/admin/playwright.config.cjs`
- `tests/e2e/web-admin/fixtures.cjs`
- `tests/e2e/web-admin/future-advanced-coverage-helpers.cjs`
- `docs/testing/FULL_PLAYWRIGHT_E2E_RUNBOOK.md`
- `docs/testing/TEST_EXECUTION_PITFALLS.md`
