# E2E advanced coverage specs (`future-advanced-coverage*.spec.js`)

## Current status

In this branch, the following files are already implemented as normal Playwright coverage:

- `tests/e2e/web-admin/future-advanced-coverage.spec.js` (cases 1-15)
- `tests/e2e/web-admin/future-advanced-coverage-2.spec.js` (cases 16-30)

Shared helpers live in:

- `tests/e2e/web-admin/future-advanced-coverage-helpers.cjs`

They run under the same default admin E2E contract as the other browser specs:

- `apps/web/admin/playwright.config.cjs`
- `tests/e2e/web-admin/global-setup.cjs`
- `/api/e2e/dev/reset-scenario`
- `E2E_DEV_SEED_TOKEN`

Operational meaning for this branch:

- these files are part of the active browser regression corpus
- they do not require `E2E_ENABLE_BACKLOG_SPECS`
- failures in these files should be triaged as real test failures, not as optional placeholder debt

## Why this document still exists

Older repository states used the same filenames for a skipped placeholder backlog. That older workflow matters when:

- reading old commits,
- interpreting historical notes in other docs,
- comparing branches that were cut before the scenarios were fully implemented.

This document therefore keeps both:

- the current interpretation for this branch,
- the historical interpretation for older branches.

## Current verification

From `apps/web/admin`:

```bash
npx playwright test future-advanced-coverage.spec.js future-advanced-coverage-2.spec.js
```

Use the same environment precautions documented in:

- [DEVELOPMENT_AND_TESTING.md](DEVELOPMENT_AND_TESTING.md)
- [TEST_EXECUTION_PITFALLS.md](TEST_EXECUTION_PITFALLS.md)

In particular, keep the Playwright runtime contract aligned with `apps/web/admin/playwright.config.cjs`:

- managed API port default: `8012`
- managed UI port default: `3012`
- optional external-server override: `PLAYWRIGHT_USE_EXTERNAL_SERVERS=1`
- optional backend interpreter override: `E2E_PYTHON`
- optional worker-mode override: `E2E_USE_REAL_WORKER`

## Scenario index

### Part I (`future-advanced-coverage.spec.js`)

1. Student stale-tab homework resubmit after teacher hard review - one authoritative attempt history.
2. Teacher concurrent material chapter reorder from two tabs - one final chapter sequence.
3. Admin delete-class blocked while roster/course references exist.
4. Teacher LLM endpoint failover during async grading - one completed task, no orphan queue rows.
5. Student dual-tab score appeal - one pending appeal and one notification chain.
6. Admin batch user activation with stale filters - final active state matches API.
7. Student notification deep-link with corrupted `selected_course` - rebind to accessible course only.
8. Teacher concurrent max-submission edit vs student submit - cap enforcement after race.
9. Parent portal vs student web-admin notification read-state isolation (per policy).
10. Teacher duplicate attendance save retries - one row per student/date.
11. Admin semester switch plus stale score composition tab - one valid composition.
12. Teacher points award vs student redemption race - consistent balance and ranking.
13. Student attachment replace after flaky upload - one surviving attachment reference.
14. Admin dual-tab system settings save - final branding consistent, no mixed fields.
15. Teacher targeted notification - privacy across student, classmate, admin, parent.

### Part II (`future-advanced-coverage-2.spec.js`)

16. Teacher dual-tab material publish vs delete - one surviving material record.
17. Student stale homework detail after teacher unpublish - safe recovery.
18. Admin class rename during teacher session - labels update, course identity stable.
19. Per-course LLM policy change while worker processing - old vs new task config separation.
20. Student plus parent concurrent visibility after appeal reopen - permissions consistent.
21. Teacher rapid notification create/edit/delete - no duplicate unread counters on student dashboard.
22. Admin orphan user plus roster sync race - no duplicate student rows after reconcile.
23. Teacher score composition formula change while student scores open - one computed total everywhere.
24. Teacher materials attachment replace under flaky network - one downloadable file, no stale section ref.
25. Student stale elective selection after backend block - self-enroll affordance correct.
26. Teacher bulk attendance plus notification from parallel tabs - one batch, correct fanout.
27. Admin repeated demo-seed reset during session - safe re-login, no cross-scenario bleed.
28. Student avatar replace plus logout/login across tabs - one final avatar URL.
29. Teacher pinned notification reorder/unpin race - deterministic student list order.
30. Teacher stale grade-candidate page after manual override - obsolete candidate not resurrected.

## Historical appendix: placeholder-backlog workflow

This section is intentionally preserved for older branches and old discussion context.

### Historical purpose

Originally, the repository kept the same two files as a scenario backlog rather than as validated runnable coverage. Each entry named a high-difficulty workflow, often:

- multi-tab,
- race-prone,
- cross-role,
- or dependent on careful state convergence.

### Historical default behavior

Older branches used:

- `E2E_ENABLE_BACKLOG_SPECS`
- `tests/e2e/web-admin/backlog-e2e.cjs`

Typical historical semantics:

- falsy or unset `E2E_ENABLE_BACKLOG_SPECS`: backlog suites were skipped at the describe level
- truthy `E2E_ENABLE_BACKLOG_SPECS`: scenarios registered and reported skipped with a stable reason until implemented

### Historical implementation workflow

On those older branches, the usual sequence was:

1. Enable the backlog gate.
2. Pick one scenario title.
3. Replace the placeholder registration with a real `test(...)`.
4. Implement steps and assertions.
5. Promote the scenario into the normal runnable E2E corpus once stable.

### Historical interpretation rule

A skipped placeholder never meant the product feature was necessarily missing. It meant only that repository-side browser automation for that narrative had not yet been checked in.
