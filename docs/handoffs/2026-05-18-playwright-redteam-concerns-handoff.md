# Playwright Red-Team Concerns Handoff (2026-05-18)

## Purpose

This handoff does **not** ask the next agent to run another blind full
regression first.

The intent is to preserve the deeper concerns exposed while repairing the
school Playwright failures so the next round can focus on:

1. targeted red-team testing,
2. structural fixes,
3. then a deliberate full regression only after the main concerns are either
   disproven or fixed.

## Branch

- `cursor/repository-normalization-schema-notifications`

## Skill / Validation Contract Change

The repository skill contract was updated so the default concurrency assumption
is now:

- `10` for **every** validation block by default

This is a planning default, not proof that every block is actually healthy at
that concurrency today.

In practice, this session intentionally avoided treating that default as a
truth claim for the repaired Playwright block. The next agent should treat the
default as the operator baseline, then red-team the system until either:

- `10`-way concurrency is shown to be sound for the relevant surfaces, or
- the repository records a principled reason to override that default for a
  specific block.

## What Was Repaired In This Session

The following changes were made to get previously failing Playwright surfaces
back to a targeted-green state:

- `apps/web/school/scripts/playwright-external-runner.cjs`
  - backend API port is now dynamically selected instead of assuming one fixed
    default
  - runner environment wiring now passes the resolved backend/frontend ports
    through to the worker process
- `apps/backend/courseeval_backend/api/routers/semesters.py`
  - default semester initialization now tolerates concurrent first-time insert
    races by rolling back on `IntegrityError`
- `apps/web/school/src/views/Materials.vue`
  - materials page now refreshes selected-course context on mount so
    server-side course-cover changes are more likely to surface to the student
    view
- shared Playwright helpers and multiple school E2E specs
  - login helpers were hardened away from raw `waitForURL(!/login/)`
  - recent-post menu interaction was narrowed to the active visible menu
  - MessageBox confirmation handling was hardened for the current Element Plus
    behavior
  - several stale selectors and stale status expectations were updated to the
    current UI / backend contract

Targeted reruns that were exercised during repair reached green for the
previously failing spec group, but this handoff intentionally stops short of
calling the entire block proven.

## Primary Concerns For The Next Round

These concerns are the most important output of the session.

### 1. The system still has multiple hidden concurrency assumptions

The repaired specs exposed several places where the repository behaves as if
state is serialized even though the validation contract wants a default of
`10`-way concurrency.

Concrete evidence from this repair round:

- the earlier full Playwright block failed with real SQLite lock pressure
- `semesters.py` still needed a defensive rollback for duplicate first-insert
  races
- many E2E helpers historically assumed one stable UI state transition at a
  time
- recent-post and student-action interactions were sensitive to duplicated
  teleported menus

Concern:

- there are probably more first-write or read-modify-write paths that only
  survive because targeted reruns were serialized
- a green serial rerun should not be mistaken for proof that the product is
  healthy under the new default concurrency contract

Recommended red-team focus:

- hit uniqueness-constrained bootstrap/init routes in parallel
- hit teacher/student mixed-write routes in parallel
- hit multi-tab UI paths where teleported menus, dialogs, or route changes can
  overlap

### 2. Login success and route-bootstrap remain suspicious under stress

A major failure family from the original block was:

- backend `POST /api/auth/login` succeeded,
- but the browser remained on `/login`

The helper hardening masks part of that by checking client storage and then
falling back to an explicit route.

That was the correct tactical repair for test progress, but it does **not**
prove the product bootstrap is fully healthy.

Concern:

- there may still be a race between token storage, user bootstrap,
  selected-course bootstrap, route guards, and page hydration
- the product may rely on eventual UI recovery rather than deterministic first
  navigation correctness

Recommended red-team focus:

- repeated cold logins across multiple roles in parallel
- login followed immediately by deep links to:
  - `/notifications`
  - `/student-scores`
  - `/homework/<id>/submit`
  - `/materials`
- stress with stale `localStorage.selected_course` plus immediate route changes
- verify whether the UI truly self-heals without the test helper's fallback
  route jump

### 3. Shared SQLite remains a likely structural bottleneck, not just a flaky test substrate

The original block already showed `database is locked` failures. The session
fixed one initialization race, but it did **not** eliminate the underlying
risk of shared SQLite writes under high Playwright concurrency.

Concern:

- even when lock failures disappear, lost-update or inconsistent-read behavior
  may still survive silently
- atomicity may differ across:
  - notification creation/read state
  - score appeals
  - discussion creation
  - homework submission attempts
  - attendance
  - counters or summary rows

Recommended red-team focus:

- API-only write storms for:
  - notifications
  - homework submissions
  - score appeals
  - attendance
  - roster enrollment
- compare raw row counts and state transitions after storms, not just HTTP
  status codes
- explicitly distinguish:
  - lock failures,
  - duplicate rows,
  - silent dropped updates,
  - inconsistent read models

### 4. Element Plus interaction surfaces are still fragile

This round needed tactical hardening for:

- teleported dropdown menus
- teleported confirmation dialogs
- collapsed discussion composers

Concern:

- many other specs may still depend on page-global selectors that accidentally
  match the wrong active popper/dialog
- future UI refactors could re-break helper assumptions without changing
  product behavior

Recommended red-team focus:

- pages with more than one visible menu trigger
- menus reopened after reload / route roundtrip
- dialogs and confirmation overlays while background notifications or loading
  masks are present
- selector audits for `:visible`, `.last()`, and broad page-global locators

### 5. Some current “repairs” are test-contract alignments, not product proof

Examples:

- LLM transient-failure expectations were aligned from `failed` to
  `retry_scheduled`
- several assertions now accept the current state machine rather than an older
  visible-string contract
- some flows now navigate directly to target routes instead of reproducing the
  original clickable path

Concern:

- these were justified to match the current product contract, but a later agent
  should still ask whether the product behavior is correct for users, not only
  for tests
- a helper can hide a regression by driving the UI around a broken route
  transition or menu interaction

Recommended red-team focus:

- re-run key user-critical flows with less helper intervention
- compare:
  - “through the exact visible UI path”
  - versus “deep-link / helper-assisted path”
- if only the assisted path survives, treat that as a product concern, not a
  closed test issue

### 6. Course-context healing may conceal deeper selected-course model drift

`Materials.vue` now explicitly refreshes selected-course context on mount.
That repaired one visible course-cover case, but the wider repository has many
views reading `userStore.selectedCourse`.

Concern:

- selected-course staleness may still exist in other views
- the product may have no single authoritative policy for when cached course
  metadata should be refreshed versus trusted

Recommended red-team focus:

- stale course metadata after:
  - server-side cover change
  - teacher reassignment
  - enrollment change
  - semester change
  - course deletion or deactivation
- verify consistency across:
  - `/courses`
  - `/materials`
  - `/homework`
  - `/notifications`
  - `/scores`

### 7. The WAI-VALID default of 10 creates a policy-vs-reality gap that must be tested explicitly

You asked to set the skill default to `10` for all blocks. That is now the
documented default.

Concern:

- the repository policy may now overstate what the browser block can sustain
  today
- if the next agent simply runs a full `10`-way block and gets failures, it
  will still be unclear which failures are:
  - genuine product races,
  - orchestration defects,
  - infrastructure limits,
  - or invalid assumptions in the tests

Recommended red-team approach:

1. keep the default documented as `10`
2. do **targeted** concurrency red-team passes first
3. explicitly record which surfaces fail only at higher concurrency
4. decide whether each failure means:
   - lower the block concurrency in practice, or
   - fix the product/infrastructure until `10` is honest

## Red-Team Plan For The Next Agent

The next agent should not start with a 36-spec all-up rerun.

Recommended order:

1. Stress login/bootstrap with multi-role and deep-link scenarios.
2. Stress SQLite-backed write paths with API-only concurrency storms.
3. Stress teleported UI surfaces:
   - dropdown menus
   - confirmation dialogs
   - discussion composer open/submit flows
4. Stress selected-course staleness across multiple views after server-side
   mutations.
5. Re-test the repaired Playwright paths with reduced helper assistance where
   possible.
6. Only after the above, decide whether to run:
   - a partial Playwright shard set at `10`,
   - or the full Playwright block.

## Important Artifacts Still Worth Reading

- previous failed full-block handoff:
  - `docs/handoffs/2026-05-18-playwright-block-failures-handoff.md`
- earlier failed full-block artifacts:
  - `.agent-run/logs/WAI-VALID-full-playwright-rerun3-20260518/summary.json`
  - `.agent-run/logs/WAI-VALID-full-playwright-rerun3-20260518/block-report.json`
  - `.agent-run/logs/WAI-VALID-full-playwright-rerun3-20260518/block-summary.txt`
- targeted repair specs exercised in this round:
  - `tests/e2e/web-school/e2e-cross-cutting-edge.spec.js`
  - `tests/e2e/web-school/e2e-cross-cutting-tier2.spec.js`
  - `tests/e2e/web-school/e2e-homework-comment-cover-tier4.spec.js`
  - `tests/e2e/web-school/e2e-pitfall-guard-rails.spec.js`
  - `tests/e2e/web-school/e2e-recent-posts-student-actions.spec.js`
  - `tests/e2e/web-school/future-advanced-coverage.spec.js`

## Handoff Bottom Line

The repository is in a better state than when this repair round started, but
the important takeaway is **not** “Playwright is done.”

The important takeaway is:

- the immediate failing specs were repaired,
- the validation skill default is now `10` concurrency for every block,
- and the next serious work item should be **red-team validation of the hidden
  concurrency, bootstrap, selector, and course-context assumptions** before
  trusting another full browser regression run.
