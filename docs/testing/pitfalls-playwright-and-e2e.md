# Playwright And E2E Pitfalls

## Purpose

Use this route when the failure shape suggests:

- Playwright worker, browser, or webServer startup issues;
- Vite / backend managed-server problems;
- E2E port collisions;
- brittle selectors, overlay targeting, dropdown timing, or badge/UI race
  assertions;
- seeded browser-scenario setup drift.

This file is a **router and summary**, not the canonical pitfall ledger. The
full historical narratives remain in
[TEST_EXECUTION_PITFALLS.md](TEST_EXECUTION_PITFALLS.md).

## Start Here

1. Run:

   ```powershell
   python ops\scripts\dev\search_pitfalls.py "<exact Playwright error or UI symptom>"
   ```

2. Open:
   [FULL_PLAYWRIGHT_E2E_RUNBOOK.md](FULL_PLAYWRIGHT_E2E_RUNBOOK.md)
3. If the failure may still be local-environment shaped, route through:
   [../../skills/local-test-triage/SKILL.md](../../skills/local-test-triage/SKILL.md)

## Primary Pitfall Clusters

| Cluster | Start with |
|---------|------------|
| managed webServer, wrong Python, project discovery | Pitfalls 4, 11, 41, frontend/playwright invocation directory pitfalls |
| browser/runtime bootstrap | Pitfalls 48 and 75 |
| selector strict mode / duplicate UI affordances | Pitfalls 13, 18, 29, 32-40 |
| notification / course-switcher / mobile race behavior | Pitfalls 49-50, 63-71 |
| parent portal E2E contract | parent SPA truncation pitfall, Pitfall 127 in `pitfall-index.csv` |
| external runner / readiness timing | Pitfalls 88 and Playwright external-runner readiness sections |

## Key Pitfalls

- **Pitfall 11**: Playwright `webServer` on Linux may use `python3` without
  project dependencies.
- **Pitfall 41**: `read ECONNRESET` / `fetch failed` on default E2E ports is
  usually harness contention, not remote provider failure.
- **Pitfalls 13 / 18 / 32-40**: strict-mode duplication, wrong dialog target,
  disabled controls, and route/query expectation drift are frequent UI
  authoring traps.
- **Pitfall 48**: `npm: command not found` blocks Playwright even when pytest
  is green.
- **Pitfall 50**: notification header badge tests are especially sensitive to
  disabled course-card clicks, hover-only dropdowns, and badge/API race
  windows.
- **Pitfalls 63-75**: stale listeners, hover dropdowns, mock cursor drift,
  chapter reorder contracts, responsive timeout patterns, and missing browser
  binaries dominate long-suite browser failures.

## Recommended Commands

```bash
cd <repo>/apps/web/school
npm ci
npx playwright install chromium
npx playwright test --list
```

For routing or selector drift, also inspect:

- [TEST_SUITE_MAP.md](TEST_SUITE_MAP.md)
- [../frontend/NOTIFICATION_HEADER_AND_REALTIME_SYNC.md](../frontend/NOTIFICATION_HEADER_AND_REALTIME_SYNC.md)

## Related Files

- [TEST_EXECUTION_PITFALLS.md](TEST_EXECUTION_PITFALLS.md)
- [FULL_PLAYWRIGHT_E2E_RUNBOOK.md](FULL_PLAYWRIGHT_E2E_RUNBOOK.md)
- [TEST_SUITE_MAP.md](TEST_SUITE_MAP.md)
- [../../skills/school-playwright-e2e/SKILL.md](../../skills/school-playwright-e2e/SKILL.md)

## Detailed migrated entries

### Additional session (Linux / cloud agent, May 2026)

This session used Linux bash, the repository `.venv` for pytest,
system-packaged Node/npm where needed, and Playwright driven from
`apps/web/school` (`npm run test:e2e`). Pitfalls 11–16 below come from that
pass. They complement, rather than contradict, the Windows-focused items.

### Pitfall 11: Playwright `webServer` on Linux uses `python3` without project packages

#### Symptom

Playwright fails immediately when starting the API, with stderr similar to:

- `No module named uvicorn`

#### Why it happens

The Playwright config may spawn the backend with the system `python3`. That
interpreter often does not have `requirements.txt` installed, while the
repository expects a local virtual environment.

#### What worked

- Point the API command at `.venv/bin/python` when that path exists, or set
  `E2E_PYTHON` to an interpreter that has backend dependencies installed.

#### Relationship to other guidance

This is the same operational idea as checklist item 1 ("use the repository
`.venv`"), but it applies specifically to who starts uvicorn when tests use
managed `webServer`.

### Pitfall 12: Element Plus default locale vs Chinese button labels in tests

#### Symptom

A test waits for `getByRole('button', { name: '确定' })` or `关闭`, but
Playwright reports strict-mode violations or timeouts. The dialog may show
**OK** / **Cancel**, or the header close button may expose a different
accessible name.

#### Why it matters

Without registering a Chinese locale for Element Plus, `ElMessageBox.confirm`
and similar components follow English defaults even when surrounding UI copy is
Chinese.

#### Safe handling strategy

- Register Element Plus `zh-cn` (or match tests to the actual accessible names
  rendered in your locale), or use narrow selectors.

### Pitfall 13: Playwright strict mode and duplicate text matches

#### Symptom

`expect(locator).toBeVisible()` fails with strict-mode violation: one locator
resolved to two or more elements.

#### Recommendation

Prefer:

- role-based locators
- scoped locators
- or `data-testid` hooks

#### Extensions

- duplicate `data-testid` values inside one overlay
- Element Plus `el-radio-button` intercepting clicks on the native radio input
- `MaterialRead` title vs chapter navigation ordering
- sidebar `default-active` vs nested routes
- homework detail page is a full route, not a dialog
- teacher dashboard route removal and redirect expectations

### Pitfall 14: `textarea:first()` on the homework submit page is often the wrong control

#### Symptom

Submission-related E2E polls the API forever: attempt count stays `0`, or
`POST /api/homeworks/{id}/submission` never fires as expected.

#### Why it happens

The homework submit view renders `CourseDiscussionPanel` above the homework
submission form. `page.locator('textarea').first()` fills the discussion draft,
not `homework-submit-content`.

#### Recommendation

Target the homework body field explicitly, for example
`getByTestId('homework-submit-content')`.

### Pitfall 15: client `page_size` larger than the API allows

#### Symptom

The materials UI shows an empty table even though seeded data exists, or E2E
cannot find a known material title.

#### Why it happens

List endpoints validate `page_size` with an upper bound (for example `le=100`).
A client request with `page_size=200` may return `422`; the UI may not surface
the validation error clearly.

#### Recommendation

Keep client requests aligned with FastAPI/Pydantic limits. When debugging empty
lists, inspect network responses for 422 before assuming seed or routing bugs.

### Pitfall 16: duplicate `course_enrollments` rows during startup reconciliation (often seen with SQLite)

#### Symptom

Backend crashes during application lifespan or pytest/E2E startup with unique
constraint failures on `course_enrollments.subject_id, student_id`.

#### Interpretation

Multiple reconciliation paths can attempt to insert the same enrollment for the
same student and course. SQLite may surface the race more readily during
startup batches.

#### What worked in practice

Defensive idempotency at insert time so startup reconciliation does not abort
the whole process.
