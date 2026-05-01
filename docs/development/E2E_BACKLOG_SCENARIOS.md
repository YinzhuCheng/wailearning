# E2E advanced coverage specs (`future-advanced-coverage*.spec.js`)

## Current status

As implemented in this repository, **`tests/e2e/web-admin/future-advanced-coverage.spec.js`** (cases 1–15) and **`tests/e2e/web-admin/future-advanced-coverage-2.spec.js`** (cases 16–30) contain **real Playwright `test(...)` implementations** that run under the default admin E2E configuration (same `globalSetup`, `E2E_DEV_SEED_TOKEN`, and Playwright `webServer` contract as other specs under `tests/e2e/web-admin/`).

Shared fetch/login/API helpers used by these files live in **`tests/e2e/web-admin/future-advanced-coverage-helpers.cjs`**.

Older documentation below described a **skipped placeholder backlog** gated by **`E2E_ENABLE_BACKLOG_SPECS`** and **`backlog-e2e.cjs`**; that mechanism was **removed** once the scenarios were implemented end-to-end. The historical sections remain for traceability.

---

# E2E backlog scenarios (historical note: placeholder Playwright specs)

## Purpose

This repository keeps two Playwright files as a **scenario backlog**, not as validated regression coverage:

- `tests/e2e/web-admin/future-advanced-coverage.spec.js` (cases 1–15)
- `tests/e2e/web-admin/future-advanced-coverage-2.spec.js` (cases 16–30)

Each entry names a **high-difficulty** admin-SPA workflow (often multi-tab, race-prone, or cross-role). Implementing one means adding real UI/API steps and assertions, then replacing the placeholder registration with a normal `test(...)`.

## Default behavior (recommended for CI and routine runs)

By default, the backlog **describe blocks are not loaded as runnable tests**:

- Control flag: **`E2E_ENABLE_BACKLOG_SPECS`**  
  When unset or falsy, the backlog suites use `test.describe.skip(...)` so **`npm run test:e2e` does not register ~30 placeholder rows**.
- When **`E2E_ENABLE_BACKLOG_SPECS`** is truthy (`1`, `true`, `yes`, `on`), the backlog describes run and each scenario reports as **skipped** with a stable reason until implemented.

Helpers live in:

- `tests/e2e/web-admin/backlog-e2e.cjs` (`describeBacklogSuite`, `backlogScenario`)

Skip reason string for placeholders:

- see **`BACKLOG_SCENARIO_SKIP_REASON`** in `backlog-e2e.cjs` (also echoed in Playwright output when backlog is enabled).

## Enabling the backlog while iterating

Example (repository root, after `cd apps/web/admin`):

```bash
E2E_ENABLE_BACKLOG_SPECS=1 npm run test:e2e
```

You should still satisfy the usual E2E prerequisites (`globalSetup`, `E2E_DEV_SEED_TOKEN`, servers or Playwright `webServer`, etc.) as documented in [DEVELOPMENT_AND_TESTING.md](DEVELOPMENT_AND_TESTING.md) and [TEST_EXECUTION_PITFALLS.md](TEST_EXECUTION_PITFALLS.md).

## Implementing a scenario

1. Set **`E2E_ENABLE_BACKLOG_SPECS=1`** so the describe block is active.
2. Pick one case title.
3. Replace **`backlogScenario('...')`** with a normal **`test('...', async ({ page, browser }) => { ... })`** (or browser fixture as needed).
4. Implement steps and assertions; prefer API verification where the product contract matters (see practical rules in [DEVELOPMENT_AND_TESTING.md](DEVELOPMENT_AND_TESTING.md)).
5. Once the scenario is fully implemented and stable, consider **moving it** into a non-backlog spec file so it runs under default `npm run test:e2e` without the backlog flag.

## Relationship to “skip” and product completeness

Placeholder skips **do not mean** the product necessarily lacks the feature. They mean **automated E2E coverage for that narrative is not yet checked in**. Overlap with existing suites (`e2e-scenario-resilience.spec.js`, LLM hard scenarios, etc.) is possible; when implementing, deduplicate or consolidate rather than copying.

## Verification

From `apps/web/admin`, with default Playwright `webServer` and `E2E_DEV_SEED_TOKEN` (see [DEVELOPMENT_AND_TESTING.md](DEVELOPMENT_AND_TESTING.md)):

```bash
npx playwright test future-advanced-coverage.spec.js future-advanced-coverage-2.spec.js
```

In the environment used for the implementation of this document, the above command completed with **30 passed** (chromium, 1 worker).

**Part I (`future-advanced-coverage.spec.js`):**

1. Student stale-tab homework resubmit after teacher hard review — one authoritative attempt history.
2. Teacher concurrent material chapter reorder from two tabs — one final chapter sequence.
3. Admin delete-class blocked while roster/course references exist.
4. Teacher LLM endpoint failover during async grading — one completed task, no orphan queue rows.
5. Student dual-tab score appeal — one pending appeal and one notification chain.
6. Admin batch user activation with stale filters — final active state matches API.
7. Student notification deep-link with corrupted `selected_course` — rebind to accessible course only.
8. Teacher concurrent max-submission edit vs student submit — cap enforcement after race.
9. Parent portal vs student web-admin notification read-state isolation (per policy).
10. Teacher duplicate attendance save retries — one row per student/date.
11. Admin semester switch + stale score composition tab — one valid composition.
12. Teacher points award vs student redemption race — consistent balance and ranking.
13. Student attachment replace after flaky upload — one surviving attachment reference.
14. Admin dual-tab system settings save — final branding consistent, no mixed fields.
15. Teacher targeted notification — privacy across student, classmate, admin, parent.

**Part II (`future-advanced-coverage-2.spec.js`):**

16. Teacher dual-tab material publish vs delete — one surviving material record.
17. Student stale homework detail after teacher unpublish — safe recovery.
18. Admin class rename during teacher session — labels update, course identity stable.
19. Per-course LLM policy change while worker processing — old vs new task config separation.
20. Student + parent concurrent visibility after appeal reopen — permissions consistent.
21. Teacher rapid notification create/edit/delete — no duplicate unread counters on student dashboard.
22. Admin orphan user + roster sync race — no duplicate student rows after reconcile.
23. Teacher score composition formula change while student scores open — one computed total everywhere.
24. Teacher materials attachment replace under flaky network — one downloadable file, no stale section ref.
25. Student stale elective selection after backend block — self-enroll affordance correct.
26. Teacher bulk attendance + notification from parallel tabs — one batch, correct fanout.
27. Admin repeated demo-seed reset during session — safe re-login, no cross-scenario bleed.
28. Student avatar replace + logout/login across tabs — one final avatar URL.
29. Teacher pinned notification reorder/unpin race — deterministic student list order.
30. Teacher stale grade-candidate page after manual override — obsolete candidate not resurrected.

These titles match the Playwright test titles in the two spec files (exact wording may wrap in code).
