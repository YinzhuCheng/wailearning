# Playwright Block Failures Handoff (2026-05-18)

## Purpose

Hand off the failed `playwright-school-e2e` full-validation block so the next
 agent/session can continue from durable artifacts instead of re-running the
 entire 36-spec block blindly.

This handoff also records the current Windows WAI-VALID launcher state because
 the full Playwright block only started successfully after the launcher chain
 was hardened in this session.

## Branch

- `cursor/repository-normalization-schema-notifications`

## Current Full-Validation State

Completed earlier in this campaign:

- `backend-sqlite-compatible`
  - green
- `security`
  - green
- `backend-postgres-sensitive`
  - green

Latest block executed:

- `playwright-school-e2e`
  - run id:
    - `WAI-VALID-full-playwright-rerun3-20260518`
  - result:
    - `failed`
  - block summary:
    - `16 passed`
    - `20 failed`
    - `0 running`
    - `0 queued`
  - durable local artifact directory:
    - `.agent-run/logs/WAI-VALID-full-playwright-rerun3-20260518`

## What Was Fixed Before This Run

These launcher-chain fixes are in the current worktree/commit scope and should
 be preserved:

- `ops/scripts/dev/wai_valid_windows_launcher.py`
  - default detached supervisor startup no longer depends on the older
    PowerShell helper path
  - added `supervisor` subcommand with detached Python launch and
    `stdin/stdout/stderr` disconnected from the caller
  - added `--args-file` support so long Playwright block specs do not depend on
    one huge Windows command line
- `ops/scripts/windows/start-validation-supervisor.bat`
  - now captures raw args to JSON and launches the Python launcher with
    `--args-file`
- `ops/scripts/dev/wai_valid_capture_args.py`
  - new helper that preserves the original batch-file arg vector for long
    block launches

Interpretation:

- the previous issue "monitor opens but the new Playwright block never really
  starts" is no longer the primary problem for this run
- `WAI-VALID-full-playwright-rerun3-20260518` is a real supervisor run with
  real worker logs, not a stale-monitor illusion

## Primary Durable Evidence

Read these first:

- local block summary:
  - `.agent-run/logs/WAI-VALID-full-playwright-rerun3-20260518/summary.json`
- per-shard structured results:
  - `.agent-run/logs/WAI-VALID-full-playwright-rerun3-20260518/block-report.json`
- human summary:
  - `.agent-run/logs/WAI-VALID-full-playwright-rerun3-20260518/block-summary.txt`
- event chronology:
  - `.agent-run/logs/WAI-VALID-full-playwright-rerun3-20260518/events.log`
- worker stdout/stderr:
  - `.agent-run/logs/WAI-VALID-full-playwright-rerun3-20260518/WAI-VALID-worker-*.log`
  - `.agent-run/logs/WAI-VALID-full-playwright-rerun3-20260518/WAI-VALID-worker-*.err.log`

Important evidence rule:

- for this run, the WAI-VALID worker logs under `.agent-run/logs/...` are the
  most complete durable surface
- `apps/web/school/test-results/` is still useful when the referenced
  `error-context.md` remains present, but it is not a reliable full-history
  archive for the whole 36-spec block

## Failure Grouping

The 20 failed shards are **not** one uniform product regression. At least three
 distinct families appear in the durable artifacts.

### Group A: shared SQLite concurrency / lock failures

Concrete stderr evidence:

- `tests/e2e/web-school/e2e-cross-cutting-edge.spec.js`
- `tests/e2e/web-school/e2e-cross-cutting-tier2.spec.js`
- `tests/e2e/web-school/e2e-cross-cutting-tier3.spec.js`
- `tests/e2e/web-school/e2e-llm-hard-scenarios.spec.js`
- `tests/e2e/web-school/e2e-tier4-stress-backlog.spec.js`

Observed error shape:

- worker stderr contains `sqlite3.OperationalError: database is locked`
- examples include inserts into:
  - `operation_logs`
  - `homework_submissions`

Interpretation:

- these are strong evidence that `10` concurrent Playwright spec workers, each
  with its own API/UI port, still interact badly with SQLite-backed write
  paths under the current seed/reset + backend logging behavior
- this is consistent with existing repo guidance that full/default Playwright
  on shared SQLite should be treated carefully and that parallel default
  runners can lock the shared database

### Group B: login succeeds at the API but the browser never leaves `/login`

Concrete examples:

- `tests/e2e/web-school/e2e-core-flows-smoke.spec.js`
- `tests/e2e/web-school/e2e-course-ui-markdown-reader.spec.js`
- `tests/e2e/web-school/e2e-notification-sync-deep-tier.spec.js`
- `tests/e2e/web-school/e2e-scenario-resilience.spec.js`
- one failing case inside `tests/e2e/web-school/e2e-cross-cutting-edge.spec.js`

Observed log shape:

- backend logs show `POST /api/auth/login HTTP/1.1" 200 OK`
- then the Playwright assertion fails at:
  - `page.waitForURL(url => !url.pathname.includes('/login'), { timeout: ... })`

Interpretation:

- this is not a plain credential failure
- likely causes to test next:
  - session/token storage or route-bootstrap race under parallel stress
  - stale state after concurrent `reset-scenario`
  - a secondary backend/UI error after login success that prevents the route
    transition
- use the referenced `error-context.md` or the worker log around the failing
  case before changing login selectors blindly

### Group C: spec-specific assertion / selector issues that may be independent

Confirmed examples from worker stdout:

- `tests/e2e/web-school/e2e-scenario-resilience.spec.js`
  - strict-mode violation on `getByRole('dialog', { name: /LLM/ }).locator('.attachment-help')`
  - the locator resolves to two elements
- `tests/e2e/web-school/e2e-llm-hard-scenarios.spec.js`
  - assertions expected summary status `failed`
  - actual observed status stayed `retry_scheduled`
- `tests/e2e/web-school/e2e-cross-cutting-edge.spec.js`
  - one case timed out waiting for a row action button after a larger
    concurrency-heavy scenario

Interpretation:

- some failures are probably real test-contract or product-behavior mismatches
- do not assume all 20 failures disappear just by lowering concurrency

## Suggested Next-Agent Triage Order

1. Do **not** rerun the whole 36-spec block first.
2. Split the failures into:
   - SQLite-lock family
   - login-stuck family
   - assertion/selector family
3. For the SQLite-lock family:
   - decide whether the correct fix is:
     - lower concurrency for the Playwright block on SQLite,
     - move this block to isolated database files per worker,
     - or run the full block on PostgreSQL-backed E2E instead
4. For the login-stuck family:
   - rerun one or two representative specs serially through the supported
     external runner path to see whether the problem survives without 10-way
     orchestration
5. For the assertion/selector family:
   - inspect the exact referenced case and `error-context.md`
   - fix only after confirming it survives the lower-noise runner shape

## Existing Committed Test Records

This session verified that the durable committed ledgers already contain useful
 targeted Playwright history for several relevant suites:

- `docs/testing/test-execution-targets.csv`
  - already has target rows for:
    - `school.e2e.core_flows_smoke`
    - `school.e2e.course_ui_markdown_reader`
    - `school.e2e.learning_notes_attendance_cover_tier20`
    - `school.e2e.notification_sync_deep_tier`
    - `school.e2e.cross_cutting_edge`
    - `school.e2e.discussion_cover_llm_tier3`
    - `school.e2e.parent_portal_hardening`
    - `school.e2e.security_hardening_followup`
- `docs/testing/test-execution-runs.csv`
  - already contains earlier targeted pass/fail history for several of those
    suites
- `docs/testing/test-execution-summary.csv`
  - already contains rolling summary rows for earlier important Playwright
    runs

Coverage gap to note:

- several failed specs from this block do **not** currently have obvious
  dedicated target rows in `test-execution-targets.csv`, including:
  - `e2e-llm-hard-scenarios`
  - `e2e-scenario-resilience`
  - `homework-llm-routing`
  - `e2e-tier4-stress-backlog`
  - `future-advanced-coverage`
  - `future-advanced-coverage-2`
  - `e2e-pitfall-guard-rails`

If those become repeated repair surfaces, the next agent should consider adding
 durable target metadata instead of leaving them visible only through this block
 handoff plus local WAI-VALID artifacts.

## New Records Added In This Round

This round should keep the following committed record surfaces in sync:

- `docs/testing/test-execution-runs.csv`
  - one aggregate failed row for the full WAI-VALID Playwright block
- `docs/testing/test-execution-summary.csv`
  - one summary row pointing back to the detailed run ledger
- `docs/handoffs/2026-05-18-playwright-block-failures-handoff.md`
  - this document

## Concrete Files The Next Agent Should Open

Start with:

- `.agent-run/logs/WAI-VALID-full-playwright-rerun3-20260518/summary.json`
- `.agent-run/logs/WAI-VALID-full-playwright-rerun3-20260518/block-report.json`
- `.agent-run/logs/WAI-VALID-full-playwright-rerun3-20260518/block-summary.txt`

Then inspect representative failing workers:

- SQLite-lock family:
  - `WAI-VALID-worker-tests_e2e_web-school_e2e-cross-cutting-edge_spec_js__d49c6b616b05.err.log`
  - `WAI-VALID-worker-tests_e2e_web-school_e2e-cross-cutting-tier2_spec_js__5bb879d9d2a6.err.log`
  - `WAI-VALID-worker-tests_e2e_web-school_e2e-cross-cutting-tier3_spec_js__93a91dcbcd62.err.log`
  - `WAI-VALID-worker-tests_e2e_web-school_e2e-llm-hard-scenarios_spec_js__cd0f70689770.err.log`
  - `WAI-VALID-worker-tests_e2e_web-school_e2e-tier4-stress-backlog_spec_js__f6655ff7aa3e.err.log`
- login-stuck family:
  - `WAI-VALID-worker-tests_e2e_web-school_e2e-core-flows-smoke_spec_js__d2c416d11a42.log`
  - `WAI-VALID-worker-tests_e2e_web-school_e2e-course-ui-markdown-reader_spec_js__d3580f6b0a59.log`
  - `WAI-VALID-worker-tests_e2e_web-school_e2e-notification-sync-deep-tier_spec_js__ccf42d733bd9.log`
  - `WAI-VALID-worker-tests_e2e_web-school_e2e-scenario-resilience_spec_js__879edd87c7bc.log`

When available, also read the Playwright error contexts under:

- `apps/web/school/test-results/**/error-context.md`

## Related Files

- [AGENTS.md](../../AGENTS.md)
- [FULL_PLAYWRIGHT_E2E_RUNBOOK.md](../testing/FULL_PLAYWRIGHT_E2E_RUNBOOK.md)
- [TEST_EXECUTION_PITFALLS.md](../testing/TEST_EXECUTION_PITFALLS.md)
- [pitfalls-playwright-and-e2e.md](../testing/pitfalls-playwright-and-e2e.md)
- [test-execution-runs.csv](../testing/test-execution-runs.csv)
- [test-execution-summary.csv](../testing/test-execution-summary.csv)
- [test-execution-targets.csv](../testing/test-execution-targets.csv)
