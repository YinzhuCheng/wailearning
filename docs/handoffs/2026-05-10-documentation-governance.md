# Documentation Governance Handoff

## Branch And Scope

- Branch: `cursor/repository-normalization`
- Pushed baseline before this follow-up: `445e85f docs: normalize governance and fix backend access regressions`
- Follow-up prepared in this local round: small subject-scoped score/dashboard
  access fix plus this handoff update. Check the current branch tip with
  `git log -1 --oneline` after commit/push.
- Previous baseline before the documentation-governance/backend-fix round:
  `84a8bce095058929a6188b0cbe2fbd3f17ef3187`
- Main workstream in this round:
  - continue repository-normalization / docs-as-governance alignment;
  - fix the failing `Backend quick pytest` line that likely explains the GitHub `3/4` check state around the lightweight validation workflow.

This handoff intentionally replaces the earlier same-file content. The active
context is no longer the Playwright-selector cleanup pass; it is now:

1. documentation / ops / governance normalization, and
2. systematic `pytest --maxfail=1` bug fixing until the quick backend suite is green.

## Completed

### Documentation / governance alignment

- Normalized the tracked [`.env.production`](../../.env.production) template to
  current CourseEval names, domains, DB name, and production-oriented defaults.
- Updated [docs/architecture/CONFIGURATION_REFERENCE.md](../architecture/CONFIGURATION_REFERENCE.md)
  so `UPLOADS_DIR` and `FRONTEND_ADMIN_BASE_URL` match current runtime behavior.
- Updated [docs/operations/DEPLOYMENT_AND_OPERATIONS.md](../operations/DEPLOYMENT_AND_OPERATIONS.md)
  to describe:
  - current `.env.production` template expectations;
  - non-destructive legacy uploads sync in `deploy_backend.sh`;
  - `post_deploy_check.sh` public health behavior;
  - `setup_server.sh`, `redeploy.sh`, and `pull_and_deploy.sh` operational flags and repo-dir resolution.
- Updated [docs/development/GIT_WORKFLOW.md](../development/GIT_WORKFLOW.md) with
  server-side deploy notes for `redeploy.sh`, backup/reset flags, and the
  simpler `pull_and_deploy.sh` wrapper.
- Rewrote [docs/architecture/TROUBLESHOOTING.md](../architecture/TROUBLESHOOTING.md)
  into a cleaner current-state troubleshooting index and added deploy/static
  asset notes.
- Extended [docs/development/TEST_EXECUTION_PITFALLS.md](../development/TEST_EXECUTION_PITFALLS.md)
  with a new pitfall documenting the recurring regression pattern:
  subject-scoped teacher actions must not be denied just because a derived
  class-id set is empty before course access is checked.
- Follow-up governance update after `daec193`:
  - documented the subject-scoped route ordering rule in
    [docs/reference/PERMISSIONS_AND_SECURITY_BOUNDARIES.md](../reference/PERMISSIONS_AND_SECURITY_BOUNDARIES.md);
  - added `backend.scores.dashboard_course_scope` to
    [tests/TEST_SELECTION_TARGETS.json](../../tests/TEST_SELECTION_TARGETS.json)
    so bounded `scores.py` / `dashboard.py` router changes map to focused
    integration/score pytest before broad PostgreSQL fallback;
  - updated
    [tests/backend/manual/test_validation_selector.py](../../tests/backend/manual/test_validation_selector.py)
    to assert the new selector behavior.

### Governance tooling

- Extended `ops/scripts/dev/check_repository_normalization.py` so
  `.production` files are treated as text and therefore scanned for retired
  names.
- Extended `ops/scripts/dev/check_text_encoding.py` and
  `ops/scripts/dev/run_validation_target.py` so `.env.production` participates
  in `<changed-text-files>` expansion and encoding checks.
- Updated `tests/TEST_SELECTION_TARGETS.json` so `.env.production` and
  `ops/scripts/*.sh` diffs map to `static.encoding_text_tools`.
- Updated `tests/backend/manual/test_validation_selector.py` to cover the new
  `.env.production` placeholder-expansion behavior.

### Deploy script behavior

- Updated [ops/scripts/deploy_backend.sh](../../ops/scripts/deploy_backend.sh)
  so a legacy `${SOURCE_DIR}/uploads/` tree is copied into
  `${SHARED_DIR}/uploads/` when present, while the old tree is intentionally
  left in place for explicit later cleanup.

### Backend bug fixes found while chasing `pytest -q`

The following are real implementation fixes, not just test updates:

- [apps/backend/courseeval_backend/api/routers/files.py](../../apps/backend/courseeval_backend/api/routers/files.py)
  now treats subject-scoped attachment access as course-owned first, instead of
  failing early on class-id reachability.
- [apps/backend/courseeval_backend/api/routers/homework.py](../../apps/backend/courseeval_backend/api/routers/homework.py)
  now checks subject-owned teacher access before class-only gating in:
  - `_ensure_homework_access`
  - `batch_update_late_submission_policy`
  - `get_homeworks`
  - `create_homework`
- [apps/backend/courseeval_backend/api/routers/attendance.py](../../apps/backend/courseeval-repository-normalization/apps/backend/courseeval_backend/api/routers/attendance.py)
  now uses subject-or-class-aware write/read gating so teacher-owned course
  attendance routes are not blocked by an empty derived class-id set.
- [apps/backend/courseeval_backend/api/routers/notifications.py](../../apps/backend/courseeval-repository-normalization/apps/backend/courseeval_backend/api/routers/notifications.py)
  now allows teacher-owned subject notifications to be created/updated/read via
  course access before class-only filtering.
- [apps/backend/courseeval_backend/api/routers/materials.py](../../apps/backend/courseeval-repository-normalization/apps/backend/courseeval_backend/api/routers/materials.py)
  now treats subject-scoped teacher material access/list/create/update as
  course-owned first.
- [apps/backend/courseeval_backend/api/routers/discussions.py](../../apps/backend/courseeval-repository-normalization/apps/backend/courseeval_backend/api/routers/discussions.py)
  now:
  - returns `400` for homework/material `subject_id` mismatch before it tries
    to authorize the wrong subject;
  - allows teacher-owned course discussion access without requiring
    class-id visibility derived from `subject_class_links`.
- [apps/backend/courseeval_backend/api/routers/users.py](../../apps/backend/courseeval-repository-normalization/apps/backend/courseeval_backend/api/routers/users.py)
  now binds the canonical `Student` row before `batch-set-class` moves a
  student user, so the roster row is moved together even when the login account
  was not explicitly bound yet.

### Test contract repairs

Several tests were still asserting pre-normalization behavior. They were updated
to match the current implementation contract instead of reintroducing legacy
fallback logic:

- no automatic cross-class roster move by username/student-no guessing alone;
- required-course auto-enrollment requires `subject_class_links`;
- administrators may create unassigned student accounts;
- behavior/material/roster helpers now seed `SubjectClassLink` where required
  tests depend on required-course auto-enrollment.

## Changed Files

- `.env.production`
- `apps/backend/courseeval_backend/api/routers/attendance.py`
- `apps/backend/courseeval_backend/api/routers/discussions.py`
- `apps/backend/courseeval_backend/api/routers/files.py`
- `apps/backend/courseeval_backend/api/routers/homework.py`
- `apps/backend/courseeval_backend/api/routers/materials.py`
- `apps/backend/courseeval_backend/api/routers/notifications.py`
- `apps/backend/courseeval_backend/api/routers/users.py`
- `docs/architecture/CONFIGURATION_REFERENCE.md`
- `docs/architecture/TROUBLESHOOTING.md`
- `docs/development/GIT_WORKFLOW.md`
- `docs/development/TEST_EXECUTION_PITFALLS.md`
- `docs/handoffs/2026-05-10-documentation-governance.md`
- `docs/operations/DEPLOYMENT_AND_OPERATIONS.md`
- `docs/reference/PERMISSIONS_AND_SECURITY_BOUNDARIES.md`
- `ops/scripts/deploy_backend.sh`
- `ops/scripts/dev/check_repository_normalization.py`
- `ops/scripts/dev/check_text_encoding.py`
- `ops/scripts/dev/run_validation_target.py`
- `tests/TEST_SELECTION_TARGETS.json`
- `tests/backend/courses/test_course_access_student_enrollment.py`
- `tests/backend/courses/test_student_course_catalog_behavior.py`
- `tests/backend/courses/test_student_elective_catalog_and_quota.py`
- `tests/backend/courses/test_user_student_class_required.py`
- `tests/backend/manual/test_validation_selector.py`
- `tests/backend/roster/test_student_roster_user_sync.py`
- `tests/backend/roster/test_students_batch_import_behavior.py`
- `tests/behavior/test_complex_regression_roundtrip_behavior.py`
- `tests/scenarios/material_flow.py`

## Verification

### Governance / documentation checks

- `python ops/scripts/dev/check_repository_normalization.py`
  - passed repeatedly; latest observed result remained `stale=0 missing_required_paths=0`
- `python -m py_compile ops/scripts/dev/check_repository_normalization.py ops/scripts/dev/check_text_encoding.py ops/scripts/dev/select_validation_targets.py ops/scripts/dev/run_validation_target.py ops/scripts/dev/run_validation_profile.py ops/scripts/dev/validation_history.py ops/scripts/dev/lint_validation_registry.py tests/backend/manual/test_validation_selector.py`
  - passed
- `python -m unittest tests.backend.manual.test_validation_selector -v`
  - passed; `36 tests OK`
- `python ops/scripts/dev/select_validation_targets.py --worktree`
  - passed; changed paths matched and selector status became `acceptable`
- `python ops/scripts/dev/run_validation_target.py static.encoding_text_tools --timeout-seconds 120`
  - passed
  - latest observed summary after `.env.production` handling fix:
    `scanned=9 decode_errors=0 suspicious=0`
- `python ops/scripts/dev/run_validation_target.py static.validation_selector --timeout-seconds 120`
  - passed
- `git diff --check`
  - passed repeatedly; only CRLF warnings remain for tracked working-copy line-ending normalization on `.env.production` and `tests/TEST_SELECTION_TARGETS.json`

### Frontend build checks

- `npm.cmd run build` in `apps/web/admin`
  - passed
- `npm.cmd run build` in `apps/web/parent`
  - passed

### Targeted backend regressions fixed during this round

Passed after fixes:

- `.\.venv\Scripts\python.exe -m pytest tests\backend\courses\test_course_access_student_enrollment.py -q`
- `.\.venv\Scripts\python.exe -m pytest tests\backend\courses\test_student_course_catalog_behavior.py -q`
- `.\.venv\Scripts\python.exe -m pytest tests\backend\courses\test_student_elective_catalog_and_quota.py -q`
- `.\.venv\Scripts\python.exe -m pytest tests\backend\courses\test_user_student_class_required.py -q`
- `.\.venv\Scripts\python.exe -m pytest tests\backend\files\test_files_attachment_download.py -q`
- `.\.venv\Scripts\python.exe -m pytest tests\backend\homework\test_homework_batch_ops.py -q`
- `.\.venv\Scripts\python.exe -m pytest tests\backend\learning_notes\test_learning_notes_api.py -q`
- `.\.venv\Scripts\python.exe -m pytest tests\backend\roster\test_roster_enroll_and_batch_class.py -q`
- `.\.venv\Scripts\python.exe -m pytest tests\backend\roster\test_student_roster_user_sync.py -q`
- `.\.venv\Scripts\python.exe -m pytest tests\backend\roster\test_students_batch_import_behavior.py -q`
- `.\.venv\Scripts\python.exe -m pytest tests\behavior\test_complex_regression_roundtrip_behavior.py -q`
- `.\.venv\Scripts\python.exe -m pytest tests\behavior/test_material_chapters_notifications_homework_flow.py::test_ui14_class_teacher_sees_materials_but_not_chapter_mutations -q`
- `.\.venv\Scripts\python.exe -m pytest tests\behavior\test_material_chapters_notifications_homework_flow.py tests\behavior\test_multi_actor_timeline_behavior.py tests\behavior\test_notification_sync_api_edge_behavior.py tests\behavior\test_per_course_llm_quota_advanced_behavior.py tests\behavior\test_points_parent_semester_behavior.py tests\behavior\test_regression_llm_quota_behavior.py tests\behavior\test_student_llm_usage_behavior.py tests\behavior\test_teacher_course_llm_behavior.py -q`
  - passed; `79 passed, 1 skipped`
- `.\.venv\Scripts\python.exe -m pytest -q tests/postgres tests/security`
  - passed; postgres slice skipped locally as expected, security slice passed
- Follow-up on 2026-05-10 after remote CI was confirmed green:
  - local `.\.venv\Scripts\python.exe -m pytest -q` was stopped rather than
    chased further because the remote check was already green and the local run
    had created residual concurrent pytest processes against the shared SQLite
    file;
  - residual local pytest processes were identified and stopped before
    continuing;
  - quick subject-scoped teacher-route audit found remaining class-id-first
    filtering in score/dashboard reads;
  - fixed course-scoped reads in
    [apps/backend/courseeval_backend/api/routers/scores.py](../../apps/backend/courseeval_backend/api/routers/scores.py)
    and
    [apps/backend/courseeval_backend/api/routers/dashboard.py](../../apps/backend/courseeval_backend/api/routers/dashboard.py)
    so `subject_id` requests that pass `ensure_course_access_http(...)` are not
    reduced to class-id-only visibility;
  - added
    `tests/backend/integration/test_core_api_surface.py::test_teacher_course_scoped_scores_do_not_require_class_link_visibility`.
  - `python -m py_compile apps\backend\courseeval_backend\api\routers\scores.py apps\backend\courseeval_backend\api\routers\dashboard.py tests\backend\integration\test_core_api_surface.py`
    passed.
  - `.\.venv\Scripts\python.exe -m pytest tests\backend\integration\test_core_api_surface.py tests\backend\scores\test_score_composition.py -q`
    passed; `15 passed, 29 warnings`.
  - `python ops\scripts\dev\check_repository_normalization.py`
    passed; `scanned=382 stale=0 missing_required_paths=0`.
  - `python ops\scripts\dev\run_validation_target.py static.encoding_text_tools --timeout-seconds 120`
    passed; `scanned=4 decode_errors=0 suspicious=0`.
  - `python ops\scripts\dev\run_validation_target.py static.validation_selector --timeout-seconds 120`
    passed.
  - `git diff --check` passed.
  - `python ops\scripts\dev\select_validation_targets.py --worktree` passed
    and conservatively recommended `full.pytest.postgres` for backend router
    changes via fallback `backend-source-conservative`; that expensive local
    profile was not rerun because remote validation for the prior branch state
    had already been confirmed green and this follow-up was covered by targeted
    integration/score tests plus static checks.
- Follow-up selector governance after documenting the route-ordering rule:
  - `python -m json.tool tests\TEST_SELECTION_TARGETS.json` passed.
  - `python ops\scripts\dev\select_validation_targets.py --paths apps/backend/courseeval_backend/api/routers/scores.py --json`
    now recommends only `backend.scores.dashboard_course_scope`, with no
    `full.pytest.postgres` fallback and no unmatched paths.
  - `python ops\scripts\dev\select_validation_targets.py --paths apps/backend/courseeval_backend/api/routers/dashboard.py --json`
    now recommends only `backend.scores.dashboard_course_scope`, with no
    `full.pytest.postgres` fallback and no unmatched paths.
  - `python -m unittest tests.backend.manual.test_validation_selector -v`
    passed; `38 tests OK`.
  - `python ops\scripts\dev\run_validation_target.py static.validation_selector --timeout-seconds 120`
    passed.
  - `python ops\scripts\dev\check_repository_normalization.py`
    passed; `scanned=382 stale=0 missing_required_paths=0`.
  - `python ops\scripts\dev\run_validation_target.py static.encoding_text_tools --timeout-seconds 120`
    passed; `scanned=3 decode_errors=0 suspicious=0`.
  - `.\.venv\Scripts\python.exe -m pytest tests\backend\integration\test_core_api_surface.py tests\backend\scores\test_score_composition.py -q`
    passed; `16 passed, 29 warnings`.

### Full-suite progression evidence

This round did not yet end with one final clean `python -m pytest -q` from the
repository root, but the failing frontier was pushed far back:

- early in the round, `pytest -q` failed at the first few percent due to a mix
  of legacy test expectations and subject-scoped teacher access bugs;
- later runs advanced to:
  - `96 passed` before the next failure,
  - then `144 passed`,
  - then `279 passed`,
  - then `303 passed`,
  - then `358 passed`,
  - then `381 passed`,
  - then `401 passed`,
  - then `419 passed`
    before exposing the next regression;
- after the latest fixes, the last attempted full rerun was:
  - `.\.venv\Scripts\python.exe -m pytest -q`
  - no assertion failure was printed before the user aborted the command around
    `78%` progress;
- the latest full `.\.venv\Scripts\python.exe -m pytest -q --maxfail=1`
  before fixing the current tail issue reached:
  - `1 failed, 419 passed, 30 warnings in 1464.99s`
  - failure: `tests/behavior/test_material_chapters_notifications_homework_flow.py::test_ui14_class_teacher_sees_materials_but_not_chapter_mutations`
  - this specific failure was then fixed and the targeted node passed.

## Known Failures / Incomplete Verification

- Remote validation was confirmed green by the user after commit `445e85f`.
  Local full-suite reruns in this worktree were intentionally not pursued
  further after they were interrupted and left duplicate pytest processes
  sharing `.pytest_tmp/test.sqlite`; the local cleanup step stopped those
  residual processes.
- Running isolated discussion behavior files (`tests/behavior/test_discussion_api_behavior.py`
  and `tests/behavior/test_discussion_api_advanced_behavior.py`) can expose
  noisy SQLite reset/setup failures (`no such table ...`, intermittent FK/logging
  issues) that do **not** match the mainline full-suite frontier observed in the
  ordered full `pytest --maxfail=1` runs.
  Treat that as a separate test-reset stability problem unless it also appears
  in the ordered full suite.
- The documentation-governance and backend/test fixes from the prior round are
  now
  committed and pushed as
  `445e85f docs: normalize governance and fix backend access regressions`.

## Risks

- Remote validation is the current full-suite signal for the prior round. Local
  SQLite full-suite runs remain sensitive to concurrent pytest processes sharing
  `.pytest_tmp/test.sqlite`.
- The repeated pattern “teacher-owned subject-scoped route denied before
  `ensure_course_access_http(...)`” has now also been audited quickly across
  score/dashboard surfaces and fixed there. Remaining risk is lower, but future
  router changes should still preserve the rule: when a route is explicitly
  scoped by `subject_id`, validate course access before applying class-only
  filters.
- Several local line-ending warnings remain in `git diff --check` output as
  non-blocking CRLF/LF working-copy warnings, not semantic diff errors.
- Isolated SQLite reset noise around discussion behavior files suggests there
  may still be a fragile local test-reset path when only a subset of files is
  run repeatedly on Windows/Python 3.14.

## Recommended Next Steps

### Immediate next round

1. Rerun the selector/governance checks after this follow-up change:
   - `python ops/scripts/dev/check_repository_normalization.py`
   - `python ops/scripts/dev/run_validation_target.py static.encoding_text_tools --timeout-seconds 120`
   - `python ops/scripts/dev/run_validation_target.py static.validation_selector --timeout-seconds 120`
   - `git diff --check`
2. If broader confidence is required locally, run one pytest process only and
   delete `.pytest_tmp/test.sqlite` first if table-exists/no-such-table errors
   recur.
3. Return to the broader repository-normalization mainline and continue the
   docs/ops audit.

### Suggested next governance batch after the suite is green

1. Revisit [docs/reference/PERMISSIONS_AND_SECURITY_BOUNDARIES.md](../reference/PERMISSIONS_AND_SECURITY_BOUNDARIES.md)
   and add the same router-ordering rule currently only recorded in the pitfalls
   doc.
2. Recheck deployment governance alignment for:
   - `setup_server.sh`
   - `redeploy.sh`
   - `pull_and_deploy.sh`
   - `post_deploy_check.sh`
   - systemd/nginx/env docs
3. Consider whether the isolated discussion-file SQLite reset failures deserve a
   dedicated test-harness hardening batch.

## Long-Term Plan

Future agents should treat the following as the durable backlog for the
repository-normalization / docs-governance line.

### Code as documentation

- Keep README, AGENTS, docs, ops templates, config docs, tests, and scripts
  aligned with the real implementation, not the historical or aspirational one.
- Search code, tests, and configs before trusting any prose claim.
- Keep retired names confined to explicit history, migration warnings, or
  append-only records.
- When current behavior is uncertain, document the uncertainty explicitly
  instead of inventing a stable rule.

### Documentation as governance

- Turn repeated operational knowledge into:
  - explicit commands,
  - checklists,
  - failure handling,
  - repeatable scripts,
  - or repo-local skills.
- Keep important rules visible from `AGENTS.md` or `docs/README.md`; do not
  hide core agent/maintainer guidance in deep one-off notes.
- Every long-lived governance doc should say:
  - when to use it,
  - what commands to run,
  - what success looks like,
  - what failure means,
  - what to read next.

### Testing and validation governance

- Continue improving diff-based validation so docs, ops, backend, frontend, and
  governance-tooling changes all map to useful checks.
- Keep structured test history in CSV/JSON/YAML and use Markdown as the entry /
  interpretation layer.
- Prefer truthful validation reporting:
  - blocked is blocked,
  - failed is failed,
  - skipped is skipped,
  - do not label inference as green.
- Expand automated checks whenever a repeated rule can be machine-enforced.

### Deployment and upgrade governance

- Keep deployment docs, service templates, nginx templates, env examples, and
  scripts in lockstep.
- Document the no-Alembic / `ensure_schema_updates()` upgrade model honestly,
  including what is runtime repair, what is operator-preflight, and what remains
  risky.
- Keep backup / restore / rollback / health-check commands explicit.

### Permission and security governance

- Backend authorization remains the source of truth.
- Never rely on frontend-hidden buttons as permission enforcement.
- Continue auditing object-level permission slices separately:
  - course access
  - homework submission/review
  - notifications
  - file download/upload
  - LLM settings
  - parent flows
  - password reset
- Keep subject-scoped teacher routes from being accidentally reduced to
  class-id-only access.

### Skills and scriptability

- Keep `skills/repository-normalization` focused on executable governance work.
- Strong skill candidates still include:
  - UTF-8 / mojibake-safe editing
  - permission audit
  - deployment upgrade checks
  - data migration audit
  - API regression audit
  - docs/code consistency checks
- Prefer scripts over prose when a rule can be automatically checked.

## Do Not Revert

- Do not restore `wailearning_backend`, old service names, old domain examples,
  or `dd-class` / `ddclass` as current names.
- Do not reintroduce username/student-number guessing as the normal student
  identity contract.
- Do not reintroduce `Subject.class_id` as the effective fallback for required
  course visibility / auto-enrollment when `subject_class_links` are missing.
- Do not reintroduce teacher denials caused by checking an empty
  `get_accessible_class_ids(...)` result before `ensure_course_access_http(...)`
  on subject-owned routes.
- Do not flatten structured validation ledgers back into giant Markdown tables.
- Do not claim the backend quick pytest line is green until a full
  `.\.venv\Scripts\python.exe -m pytest -q` finishes successfully after the
  latest fixes.

## Useful Commands

```powershell
git status --short --branch
git diff --check
python ops/scripts/dev/check_repository_normalization.py
python ops/scripts/dev/select_validation_targets.py --worktree
python ops/scripts/dev/run_validation_target.py static.encoding_text_tools --timeout-seconds 120
python ops/scripts/dev/run_validation_target.py static.validation_selector --timeout-seconds 120
.\.venv\Scripts\python.exe -m pytest -q --maxfail=1
.\.venv\Scripts\python.exe -m pytest -q
```
