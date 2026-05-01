/**
 * Helpers for optional Playwright backlog suites (placeholder E2E scenarios).
 *
 * Default CI/local runs keep backlog describes skipped so `npm run test:e2e` does not
 * register ~30 placeholder cases. Set E2E_ENABLE_BACKLOG_SPECS=1 when iterating on them.
 *
 * Individual scenarios call backlogScenario() which reports.skip with a documented reason until implemented (see docs/development/E2E_BACKLOG_SCENARIOS.md).
 */

const { test } = require('@playwright/test')

const BACKLOG_SCENARIO_SKIP_REASON =
  'Backlog scenario: placeholder only; implement steps and assertions, then replace backlogScenario() with test(). See docs/development/E2E_BACKLOG_SCENARIOS.md.'

function isBacklogSuiteEnabled() {
  return ['1', 'true', 'yes', 'on'].includes(
    String(process.env.E2E_ENABLE_BACKLOG_SPECS || '').trim().toLowerCase()
  )
}

/**
 * Like test.describe, but the whole block is omitted from the default test run unless
 * E2E_ENABLE_BACKLOG_SPECS is truthy.
 */
function describeBacklogSuite(name, fn) {
  if (!isBacklogSuiteEnabled()) {
    test.describe.skip(name, fn)
  } else {
    test.describe(name, fn)
  }
}

/**
 * Registers a placeholder case that reports as skipped with a stable reason (no scenario body runs).
 * Replace with `test(...)` when the scenario is implemented end-to-end.
 */
function backlogScenario(title) {
  test(title, async ({}, testInfo) => {
    testInfo.skip(true, BACKLOG_SCENARIO_SKIP_REASON)
  })
}

module.exports = {
  BACKLOG_SCENARIO_SKIP_REASON,
  backlogScenario,
  describeBacklogSuite,
  isBacklogSuiteEnabled
}
