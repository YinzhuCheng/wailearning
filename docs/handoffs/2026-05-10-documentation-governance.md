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

## Verification

- `npm.cmd run build` in `apps/web/admin`
- `npm.cmd run build` in `apps/web/parent`
- `python ops/scripts/dev/run_validation_profile.py selector-recommended --worktree --max-risk static`
- `python ops/scripts/dev/check_repository_normalization.py`
- `git diff --check`

## Security And Robustness Follow-Ups

- Student identity and roster binding still deserve the highest hardening
  priority.
  The current contract is better guarded than before, but the same logical
  entity is still touched from `auth.py`, `users.py`, `students.py`,
  `domains/roster/*`, and `domains/courses/access.py`. Future work should
  reduce write-side surprise, especially around `prepare_student_course_context`
  and any path that can bind `users.student_id`, create `Student` rows, or
  repair `CourseEnrollment` during a read-driven flow.
- Reduce hidden write side-effects on read paths.
  The most important medium-term robustness improvement is to separate
  "resolve current identity" from "repair missing identity/enrollment state"
  wherever practical. Reads that currently repair or commit should be reviewed
  carefully because they expand the regression surface and make concurrency,
  auditability, and authorization debugging harder.
- Tighten audit/report semantics around occupied legacy matches.
  `audit_student_identity()` now distinguishes usable candidate counts from raw
  legacy match counts, but the broader lesson remains: audit output should keep
  "repairable", "ambiguous", and "occupied by another binding" as separate
  states. Future changes should preserve that distinction in both CLI helpers
  and UI/admin-facing maintenance flows.
- Keep validation registry and durable ledger rows in lockstep.
  The branch found real drift where targets had committed run history but
  missing or mismatched `ledger_id` wiring. `lint_validation_registry.py` now
  catches that class of problem, but future validation-target additions should
  treat "registry target exists, committed ledger row exists, selector can read
  it" as one atomic contract rather than three separate chores.
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
