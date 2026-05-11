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
- Continue migrating local Playwright usage toward the repo-owned external
  runner.
  The external runner is now the preferred path for the key recorded admin
  Playwright targets and for the full `admin.e2e.full` command metadata.
  Future browser additions should avoid reintroducing fragile managed
  `webServer` assumptions unless there is a strong reason and matching docs.
- Expand CI evidence for high-value but still mostly local checks.
  Current lightweight CI is useful but does not yet cover PostgreSQL-backed
  pytest, the new admin Playwright external-runner path, or attachment/tooling
  environments that matter for release confidence. Security- and
  authorization-sensitive changes still benefit from broader automated
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

## Future Skill Candidates

These are good candidates for future repo-local skills, but this handoff does
not create them. Treat this as a backlog for later governance work when the
workflow becomes frequent enough to justify a durable skill.

- `roster-identity-repair-playbook`
  Use when auditing or repairing `users.student_id`, roster/user drift,
  ambiguous same-username cases, or class-move side effects across
  `auth.py`, `users.py`, `students.py`, and `domains/roster/*`.
  Why it is a skill candidate:
  this workflow now spans audit helpers, targeted pytest, selector rules, and
  "do not auto-rebind" safety constraints that are easy for future agents to
  partially remember.
- `postgres-release-validation`
  Use when a branch needs release-quality backend confidence rather than local
  SQLite convenience evidence.
  Why it is a skill candidate:
  PostgreSQL-backed validation still has more setup and interpretation nuance
  than ordinary targeted pytest, and the repository keeps treating it as the
  stronger signal for constraint, migration, and cross-session behavior.
- `validation-ledger-maintenance`
  Use when adding or revising validation targets, wiring `ledger_id`, updating
  `test-execution-targets.csv`, or checking selector/history consistency.
  Why it is a skill candidate:
  the branch found real registry/ledger drift, and the correct workflow now
  spans `TEST_SELECTION_TARGETS.json`, CSV target rows, lint checks, and
  selector/unit-test expectations.
- `frontend-backend-contract-audit`
  Use when reviewing pagination caps, timeout assumptions, bulk-input limits,
  or route/query parameter contracts between Vue pages and FastAPI endpoints.
  Why it is a skill candidate:
  a real UI regression surfaced because the admin students page exceeded the
  backend page-size limit, and similar shape/limit drift is likely to recur.
- `llm-worker-reliability-audit`
  Use when changing queue semantics, retry logic, task recovery, timeout
  behavior, or operational visibility for the in-process grading worker.
  Why it is a skill candidate:
  the architecture is intentionally not Celery/Redis-based, so agents need a
  repository-specific workflow for reasoning about stuck tasks, idempotency,
  and operational recovery.
- `seed-surface-hardening`
  Use when changing `/api/e2e/dev/*`, `INIT_DEFAULT_DATA`, first-admin
  bootstrap, seed tokens, or powerful local/demo routes that should stay out of
  production paths.
  Why it is a skill candidate:
  these surfaces are both operationally useful and security-sensitive, and
  future hardening work will likely need a repeatable checklist of guards,
  tests, and docs.
- `ci-gap-audit`
  Use when deciding which currently local-only validation paths should be moved
  into CI next, especially PostgreSQL pytest, admin Playwright external-runner
  flows, and attachment/tooling environments.
  Why it is a skill candidate:
  this is a recurring judgment workflow that combines registry coverage, cost,
  flake profile, and release risk rather than a one-off documentation task.

## Risks

- `docs/reports/` now holds dated audit / restructure / migration reports.
- `apps/web/admin/public/courseeval-mark.svg` and
  `apps/web/parent/public/courseeval-mark.svg` are the runtime favicon assets.
- `docs/known-issues-and-risks.md` now includes repository-normalization notes
  for future cleanup passes.
- The latest branch tip before this handoff refresh was
  `64f079e test: harden validation and roster identity flows`.

## Do Not Revert

- `docs/reports/` directory moves
- favicon wiring in both SPA `index.html` files
- `docs/reports/README.md`
