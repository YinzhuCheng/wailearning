# Red-Team Next Round Handoff (2026-05-18)

## Purpose

Hand off the next repository red-team round after one completed
`4 attacks + 1 concentrated repair` cycle on branch:

- `cursor/repository-normalization-schema-notifications`

This handoff is for the next agent to continue the red-team campaign using the
repo-local skill workflow instead of restarting from scratch or jumping
straight into broad regression.

## Required Skill

Start with:

- `skills/security-redteam-iteration/SKILL.md`

The skill was updated in this round and now explicitly requires:

1. obey `AGENTS.md` and task-scoped startup docs before editing;
2. treat one attack attempt as a default `5` minute wall-clock budget;
3. fix every confirmed product bug immediately in the same attack turn;
4. avoid broad regression after each immediate fix by default;
5. run attacks in batches of `4`;
6. do one concentrated hardening pass after every `4` attacks;
7. treat `4 attacks + 1 concentrated repair` as one repository round.

When the attack is browser-backed, also route through:

- `skills/school-playwright-e2e/SKILL.md`

When choosing validation scope, route through:

- `skills/validation-selection/SKILL.md`

## What This Round Did

This round deliberately followed the new repository-round contract:

### Attack 1

- Added student deep-link recovery coverage for:
  - `/materials/read/:id`
  - stale invalid `selected_course` cache on material-reader deep links
- Result:
  - targeted Playwright passed
  - no product bug found on that surface

### Attack 2

- Added one parallel cold-login deep-link attack for the same student across:
  - `/notifications`
  - `/student-scores`
  - `/homework/:id/submit`
  - `/materials/read/:id`
- Result:
  - targeted Playwright passed
  - no product bug found on that surface

### Attack 3

- Added a backend concurrency attack for single attendance creation
- Result:
  - exposed a real bug class:
    - bootstrap concurrency on `subject_class_links` backfill
    - duplicate concurrent `POST /api/attendance` writes

### Attack 4

- Added a backend concurrency attack for `POST /api/attendance/class-batch`
- Result:
  - exposed the same flaw class on the batch attendance write path
  - unique-constraint failure surfaced as a server error during concurrent
    batch creation

### Concentrated Repair

The repair intentionally targeted the underlying flaw class rather than only
the exact failing examples.

Changed surfaces:

- `apps/backend/courseeval_backend/bootstrap.py`
  - made `subject_class_links` bootstrap backfill concurrency-tolerant
  - SQLite path now uses an idempotent insert pattern instead of relying on a
    pre-insert check only
  - added attendance dedupe + unique-index bootstrap protection for both:
    - `(student_id, subject_id, date)` when `subject_id IS NOT NULL`
    - `(student_id, class_id, date)` when `subject_id IS NULL`

- `apps/backend/courseeval_backend/api/routers/attendance.py`
  - single-create now maps duplicate concurrent insert races to a stable
    business response instead of surfacing a raw DB failure
  - batch and class-batch attendance now use a shared upsert helper and retry
    after `IntegrityError`, so concurrent duplicate writes converge instead of
    failing mid-commit

- `tests/backend/learning_notes/test_learning_notes_api.py`
  - new `ln12` and `ln13` concurrent attendance regression tests

- `tests/e2e/web-school/e2e-scenario-resilience.spec.js`
  - new material-reader deep-link and parallel cold deep-link attacks

## Observed Validation This Round

Observed and passed:

- targeted Playwright:
  - `e2e-scenario-resilience.spec.js --grep "material reader"`
  - `e2e-scenario-resilience.spec.js --grep "parallel cold student deep-links"`
- targeted pytest:
  - `tests/backend/learning_notes/test_learning_notes_api.py -k "ln12 or ln13" -q`
  - `tests/backend/learning_notes/test_learning_notes_api.py -q`
- static checks:
  - `check_api_surface_governance.py`
  - `check_schema_governance.py`
  - `check_repo_skills.py`
  - `git diff --check`

Not run this round:

- `tests/security -q`
- `tests/postgres -q`
- full PostgreSQL-backed `pytest tests -q`
- full or broad Playwright regression

Selector status after the round still recommends review for:

- `security.api_regression`
- `postgres.pytest.package`
- `full.pytest.postgres`
- broad Playwright coverage for resilience / attendance-adjacent browser paths

Interpretation:

- the targeted red-team attack and concentrated repair are proven locally
- release-grade or full-suite confidence was intentionally not claimed

## How The Next Agent Should Start

Use this exact order:

1. Read `AGENTS.md`
2. Read `docs/README.md`
3. Read `docs/governance/repository-governance.md`
4. Read `skills/security-redteam-iteration/SKILL.md`
5. Re-read this handoff
6. Choose the next repository round as:
   - `attack 1/4`
   - `attack 2/4`
   - `attack 3/4`
   - `attack 4/4`
   - then one concentrated repair

## Recommended Next Round Targets

Do not start with broad regression.

The best next attack surfaces are the ones still closest to the concurrency /
bootstrap flaw class just repaired:

1. `notifications` API write/read storms
   - create, update, delete, mark-read, mark-all-read
   - look for:
     - duplicate rows
     - dropped read-state updates
     - inconsistent `sync-status`

2. `score appeals`
   - concurrent first-create / second-create / resolution transitions
   - check:
     - pending uniqueness
     - notification fanout consistency
     - no 500 on duplicate races

3. `homework submissions`
   - concurrent first submission writes
   - repeated same-student retries
   - transitions around review / appeal state after stale tabs

4. bootstrap / startup first-write surfaces beyond attendance
   - any code path that still does:
     - query-first
     - then insert
     - without DB-backed uniqueness recovery

## Attack Design Guidance For The Next Agent

For the next round, prefer this pattern:

1. Pick one narrow surface.
2. Add the attack test first.
3. If it fails, classify:
   - product bug
   - test-contract bug
   - harness / startup issue
4. Fix only confirmed product bugs immediately.
5. Re-run only the attack that proved the bug is fixed.
6. Do not broaden into regression until the concentrated repair step after
   attack `4/4`.

For backend concurrency attacks, prefer focused pytest over Playwright unless
browser state is part of the bug hypothesis.

For browser attacks, prefer:

- `node scripts/playwright-external-runner.cjs ...`

and keep default-port runs serial.

## Important Remaining Risk

This round proved one important repository fact:

- hidden concurrency assumptions still exist in startup/bootstrap and
  attendance write paths

The attendance fixes are now stronger, but the same bug shape may still exist
in other tables and routes that rely on:

- pre-insert existence checks,
- no unique index or partial unique index,
- or commit-time `IntegrityError` bubbling as 500.

The next agent should actively hunt for that pattern rather than assuming
attendance was the only affected surface.
