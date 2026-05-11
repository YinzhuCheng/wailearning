# Documentation Governance Handoff

## Branch

- `cursor/repository-normalization`

## Completed

- Repository normalization and documentation-governance pass completed for the
  current scope.
- The worktree is expected to be clean after commit; verify push status
  separately.
- Validation governance, roster identity guardrails, and admin Playwright E2E
  workflow hardening were extended on the same branch after the original docs
  consolidation pass.
- Student profile resolution now separates read-only lookup from repair-capable
  binding cleanup: ordinary `get_student_profile_for_user()` calls no longer
  silently repair a mismatched `User.class_id`, while explicit repair/enrollment
  preparation paths still retain their existing behavior.
- Validation target governance now rejects implicit ledger aliases. A target's
  `ledger_id` must match its own id unless a future explicit alias mechanism is
  designed, and the CSV target ledger now includes the score/dashboard,
  notification sync API edge, and course/roster/homework behavior targets that
  were actually run on this branch.
- Admin Playwright target metadata is now consistently routed through the
  repo-owned external runner. Registry lint/unit coverage rejects regressions by
  checking every `admin-playwright` target command starts with
  `node scripts/playwright-external-runner.cjs`.

## Verification

- `npm.cmd run build` in `apps/web/admin`
- `npm.cmd run build` in `apps/web/parent`
- `python ops/scripts/dev/run_validation_profile.py selector-recommended --worktree --max-risk static`
- `python ops/scripts/dev/check_repository_normalization.py`
- `git diff --check`
- `.venv\Scripts\python.exe -m pytest tests\backend\roster\test_student_identity_guardrails.py -q`
- `.venv\Scripts\python.exe -m pytest tests\backend\roster\test_student_roster_user_sync.py tests\backend\courses\test_course_access_student_enrollment.py -q`
- `.venv\Scripts\python.exe -m pytest tests\backend\roster\test_student_identity_audit.py tests\backend\roster\test_student_identity_repair.py tests\backend\roster\test_student_user_api_roster_sync.py -q`
- `.venv\Scripts\python.exe -m pytest tests\backend\courses\test_student_course_roster_behavior.py -q`
- `.venv\Scripts\python.exe -m pytest tests\backend\integration\test_core_api_surface.py tests\backend\scores\test_score_composition.py -q`
- `.venv\Scripts\python.exe -m pytest tests\behavior\test_course_roster_homework_edge_behavior.py -q`
- `.venv\Scripts\python.exe -m pytest tests\behavior\test_notification_sync_api_edge_behavior.py -q`
- `.venv\Scripts\python.exe -m pytest tests\security -q`
- `.venv\Scripts\python.exe -m unittest tests.backend.manual.test_validation_selector -v`
- `.venv\Scripts\python.exe ops\scripts\dev\lint_validation_registry.py`
- `.venv\Scripts\python.exe ops\scripts\dev\select_validation_targets.py --worktree --json`

## Security And Robustness Follow-Ups

- Student identity and roster binding still deserve high hardening priority.
  The read-only profile lookup split removes one hidden write side effect, but
  the same logical entity is still touched from `auth.py`, `users.py`,
  `students.py`, `domains/roster/*`, and `domains/courses/access.py`. Future
  work should keep reducing write-side surprise, especially around
  `prepare_student_course_context` and any path that can bind
  `users.student_id`, create `Student` rows, or repair `CourseEnrollment`
  during a read-driven flow.
- Continue separating resolve and repair flows.
  `resolve_bound_student_for_user()` is now the read-only resolver and
  `get_bound_student_for_user()` remains repair-capable for explicit repair
  paths. Future reads that still repair or commit should be reviewed carefully
  because they expand the regression surface and make concurrency, auditability,
  and authorization debugging harder.
- Tighten audit/report semantics around occupied legacy matches.
  `audit_student_identity()` now distinguishes usable candidate counts from raw
  legacy match counts, but the broader lesson remains: audit output should keep
  "repairable", "ambiguous", and "occupied by another binding" as separate
  states. Future changes should preserve that distinction in both CLI helpers
  and UI/admin-facing maintenance flows.
- Keep validation registry and durable ledger rows in lockstep.
  The branch found real drift where targets had missing or mismatched
  `ledger_id` wiring, including accidental pointers from behavior pytest
  targets to unrelated Playwright/security ledger rows. `lint_validation_registry.py`
  now catches implicit aliases even when the target does not yet have its own
  committed row. Future validation-target additions should treat "registry
  target exists, committed ledger row exists, selector can read it" as one
  atomic contract rather than three separate chores.
- Keep admin Playwright target metadata on the repo-owned external runner.
  All current `admin-playwright` registry targets now use
  `node scripts/playwright-external-runner.cjs`, and selector unit coverage
  enforces that repository-wide. Future browser additions should avoid
  reintroducing fragile managed `webServer` assumptions unless there is a strong
  reason, matching docs, and an intentional test update.
- Expand CI evidence for high-value but still mostly local checks.
  Current lightweight CI is useful but does not yet cover PostgreSQL-backed
  pytest, a real admin Playwright external-runner execution, or
  attachment/tooling environments that matter for release confidence. Security-
  and authorization-sensitive changes still benefit from broader automated
  coverage.
- Continue reviewing frontend request bounds against backend validation limits.
  A real admin UI issue surfaced because the students page requested
  `page_size=2000` while the backend capped that endpoint lower. Similar
  front/back contract mismatches should be expected around pagination, timeout,
  and bulk-operation inputs.
- Treat the in-process LLM worker as an explicit reliability boundary.
  This repository still uses DB-backed queue rows plus an in-process worker
  rather than a separate broker/worker system. Future robustness work should
  keep focusing on visibility into stuck tasks, retry semantics, idempotent
  processing, and operational recovery rather than assuming distributed-worker
  guarantees that do not exist here.
- Improve production-hardening around first-run and seed surfaces.
  Demo/e2e seed capabilities are intentionally powerful. Continue keeping
  `/api/e2e/dev/*`, `INIT_DEFAULT_DATA`, seed tokens, and first-admin bootstrap
  rules explicit in code and docs, and prefer additional guardrails over softer
  documentation language when a rule can be machine-enforced.
- Keep local SQLite as a convenience path, not a source of false confidence.
  Per-process `.pytest_tmp/test_<pid>.sqlite` reduces accidental sharing, but
  PostgreSQL-backed validation remains the more trustworthy signal for
  cross-session consistency, constraint behavior, and release-quality claims.

## Repo-Local Skill Status

The recurring workflows that were concrete enough to encode have been promoted
from handoff backlog into repo-local skills:

- [`skills/roster-identity-repair-playbook/SKILL.md`](../../skills/roster-identity-repair-playbook/SKILL.md)
  covers `users.student_id`, roster/user drift, ambiguous legacy matches,
  class moves, and student-course enrollment repair.
- [`skills/postgres-release-validation/SKILL.md`](../../skills/postgres-release-validation/SKILL.md)
  covers PostgreSQL-backed and release-quality backend validation.
- [`skills/validation-ledger-maintenance/SKILL.md`](../../skills/validation-ledger-maintenance/SKILL.md)
  covers `TEST_SELECTION_TARGETS.json`, `ledger_id`, CSV target rows, and
  selector/history consistency.
- [`skills/frontend-backend-contract-audit/SKILL.md`](../../skills/frontend-backend-contract-audit/SKILL.md)
  covers pagination caps, route/query contracts, request bounds, bulk limits,
  and Vue/FastAPI contract drift.
- [`skills/seed-surface-hardening/SKILL.md`](../../skills/seed-surface-hardening/SKILL.md)
  covers `/api/e2e/dev/*`, `INIT_DEFAULT_DATA`, first-admin bootstrap, seed
  tokens, public registration, and powerful local/demo surfaces.

Still candidate-only:

- `llm-worker-reliability-audit`
  The architectural facts are already captured in
  [`docs/architecture/ASYNC_TASKS_AND_WORKERS.md`](../architecture/ASYNC_TASKS_AND_WORKERS.md)
  and LLM/product docs. Promote this to a skill when the next worker change
  adds a concrete repeatable checklist for queue semantics, stale-task recovery,
  retry idempotency, or operational visibility.
- `ci-gap-audit`
  Keep this as a future skill candidate until the repository starts actively
  moving PostgreSQL pytest, admin Playwright external-runner flows, or
  attachment/tooling environments into CI. The current actionable state remains
  the CI gap note above.

## Risks

- `docs/reports/` now holds dated audit / restructure / migration reports.
- `apps/web/admin/public/courseeval-mark.svg` and
  `apps/web/parent/public/courseeval-mark.svg` are the runtime favicon assets.
- `docs/known-issues-and-risks.md` now includes repository-normalization notes
  for future cleanup passes.
- The latest branch tip before this handoff refresh was
  `5f1eeee chore: tighten repository governance guardrails`.

## Do Not Revert

- `docs/reports/` directory moves
- favicon wiring in both SPA `index.html` files
- `docs/reports/README.md`
