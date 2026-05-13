# Three-Line Governance And Skills Handoff

Date: 2026-05-13

Branch: `cursor/repository-normalization`

## Current User Direction

The user asked to continue the repository-normalization branch, finish the
three-line governance round, structure the repo-local skills hierarchy, remove
redundant simple skills/scripts only when a richer precise version already
covers the behavior, and commit/push the result.

Latest continuation request: proceed with the next planned repository
normalization round from this handoff. The completed continuation focused on a
low-risk `api/schemas.py` boundary split while preserving the public
`apps.backend.courseeval_backend.api.schemas` import surface.

Important preference for future agents: when two skills or scripts overlap,
prefer preserving the more complex, precise, executable, and battle-tested
workflow. Delete or shrink only the simple/vague duplicate. Do not remove a
mature specialized skill just because a broader governance skill routes to it.

## Baseline From Previous Mainline Work

This branch already contained the broader CourseEval cleanup documented in
[`2026-05-12-repository-normalization-postgres-handoff.md`](2026-05-12-repository-normalization-postgres-handoff.md):

- course schedule handling was normalized around `course_times`;
- old top-level subject schedule fields were removed from active behavior;
- CourseEval naming drift was checked;
- Markdown demo and student sidebar UI issues were fixed;
- PostgreSQL local validation was repaired for this Windows host;
- `tests/postgres` passed under PostgreSQL with `42 passed`;
- Python 3.14-compatible backend dependency pins were updated.

That prior handoff remains the source for PostgreSQL setup details and
release-validation caveats.

## Three-Line Governance Completed

The current round is recorded in
[`../reports/THREE_LINE_GOVERNANCE_REPORT_2026-05-13.md`](../reports/THREE_LINE_GOVERNANCE_REPORT_2026-05-13.md).

Added or refined these repo-local governance skills:

- [`../../skills/repository-normalization/SKILL.md`](../../skills/repository-normalization/SKILL.md):
  top-level governance orchestrator and skill taxonomy router.
- [`../../skills/docs-governance/SKILL.md`](../../skills/docs-governance/SKILL.md):
  README, AGENTS, docs, reports, links, and repeated-pitfall governance.
- [`../../skills/boundary-governance/SKILL.md`](../../skills/boundary-governance/SKILL.md):
  module/function/permission/data-flow boundary discovery and safe extraction
  rules.
- [`../../skills/structure-governance/SKILL.md`](../../skills/structure-governance/SKILL.md):
  root-file policy, directory hierarchy, structural moves, and reference
  updates.

Added deterministic guard scripts under `ops/scripts/dev/`:

- `governance_common.py`
- `check_docs_governance.py`
- `check_boundary_governance.py`
- `check_structure_governance.py`
- `inventory_api_schemas.py`

Updated `check_repo_skills.py` so skill bodies cannot reference missing
`skills/<name>/SKILL.md` paths and every repo-local skill must have
`agents/openai.yaml`.

## Skills Hierarchy Decision

`AGENTS.md` now documents the skill hierarchy explicitly:

1. `repository-normalization` is the top-level router for repo-wide governance,
   skill taxonomy, package/path/name drift, and three-line governance.
2. `docs-governance`, `boundary-governance`, and `structure-governance` are
   horizontal governance skills.
3. Specialized skills own narrow risk domains:
   permissions, API surface, frontend/backend contracts, schema/data repair,
   deployment, seed/E2E dev surfaces, PostgreSQL validation, Playwright,
   UTF-8 editing, local test triage, and related execution workflows.
4. `validation-selection` and `validation-ledger-maintenance` own target choice,
   validation evidence, and ledger updates.

Layered calling rule for future agents:

- start broad only long enough to define scope;
- call the richer specialized skill for domain-specific risk;
- finish with validation-selection and ledger maintenance when checks or
  evidence are part of the task;
- if overlap appears, keep the richer precise executable skill/script and
  reduce the broader artifact to routing guidance.

No mature specialized skill was deleted in this round. The existing set is not
currently redundant enough to justify removal without losing domain-specific
rules.

## Structural And Boundary Changes

Low-risk boundary extraction:

- Added `apps/backend/courseeval_backend/domains/courses/class_scope.py`.
- Moved shared class-scope helpers out of the `classes` router ownership.
- Updated class-adjacent routers to import
  `get_accessible_class_ids` and `apply_class_id_filter` from the domain module
  instead of importing `api.routers.classes`.

Low-risk structure cleanup:

- Deleted the obsolete tracked root `error.txt` after user confirmation that it
  was an old pytest error artifact and no longer useful.
- Root raw-log policy is now documented: committed raw logs must be deliberate,
  dated, secret-free evidence under `docs/reports/artifacts/`; fresh local logs
  belong under ignored `.agent-run/`.

Latest continuation boundary split:

- Added `apps/backend/courseeval_backend/api/schema_defs/`.
- Moved low-coupling API DTO groups for appearance, attendance,
  operations/settings, and points into `schema_defs` modules.
- Latest follow-up moved notification request/response/sync DTOs into
  `api/schema_defs/notifications.py` and kept all `api.schemas`
  compatibility imports intact, including `NotificationBase`.
- Current follow-up moved the file upload response DTO
  `AttachmentUploadResponse` into `api/schema_defs/files.py` and kept
  `api.schemas` compatibility imports intact for `files` and `subjects`
  routers.
- Current follow-up moved dashboard DTOs `ClassRanking`, `DashboardStats`,
  and `StudentRanking` into `api/schema_defs/dashboard.py`. `DashboardStats`
  keeps its `ScoreResponse` relationship through a forward reference rebuilt
  from the compatibility barrel after `ScoreResponse` is defined.
- Current follow-up moved roster DTOs `CourseEnrollmentResponse`,
  `CourseRosterStudentInput`, and `CourseEnrollmentTypeUpdate` into
  `api/schema_defs/roster.py`. `CourseRosterStudentInput` keeps its `Gender`
  relationship through a forward reference rebuilt from the compatibility
  barrel after `Gender` is defined.
- Kept `apps/backend/courseeval_backend/api/schemas.py` as the compatibility
  barrel for existing router, domain-helper, and test imports.
- Updated `ops/scripts/dev/inventory_api_schemas.py` so inventory checks count
  explicit `api.schema_defs` re-exports as public `api.schemas` names.
- Updated `tests/TEST_SELECTION_TARGETS.json` and selector tests so
  `api/schema_defs/*.py` changes select schema/API-specific static and targeted
  checks instead of falling through to the broad backend-source conservative
  PostgreSQL recommendation.
- Added `backend.files.attachment_api` so file schema/router changes select the
  focused `tests/backend/files` API regression instead of relying on the LLM
  attachment-format target.

## Validation State

The three-line governance report lists the full validation already performed
for this round. Key checks that passed include:

- `python -m py_compile` for new governance scripts and class-scope helper;
- `python ops/scripts/dev/inventory_api_schemas.py --fail-on-missing-imports`;
- `python -m json.tool tests/TEST_SELECTION_TARGETS.json`;
- `python ops/scripts/dev/lint_validation_registry.py`;
- `python ops/scripts/dev/check_docs_governance.py`;
- `python ops/scripts/dev/check_boundary_governance.py --details`;
- `python ops/scripts/dev/check_structure_governance.py --details`;
- `python ops/scripts/dev/check_repo_skills.py`;
- `python ops/scripts/dev/check_repository_normalization.py`;
- `python ops/scripts/dev/check_api_surface_governance.py`;
- `python -m unittest tests.backend.manual.test_validation_selector -v`;
- `.venv` pytest for manual-script API coverage;
- `.venv` pytest for targeted course roster and core API surface tests;
- `git diff --check`.

Latest continuation validation:

- `python -m py_compile` for `api/schemas.py`, the new `api/schema_defs`
  modules, and `ops/scripts/dev/inventory_api_schemas.py` passed.
- `python ops/scripts/dev/inventory_api_schemas.py --fail-on-missing-imports`
  passed with 155 local schema classes/enums, 31 compatibility re-exports, 186
  public schema names, 24 importers, and 0 missing imports.
- `python -m json.tool tests/TEST_SELECTION_TARGETS.json` passed.
- `python ops/scripts/dev/lint_validation_registry.py` passed.
- `python ops/scripts/dev/check_api_surface_governance.py` passed.
- `python ops/scripts/dev/check_boundary_governance.py --details` passed with
  existing large-file warnings; `api/schemas.py` is now 1762 lines, down from
  the prior 2040-line inventory.
- `python ops/scripts/dev/select_validation_targets.py --worktree --json`
  reported targeted/static validation as acceptable and no unmatched paths
  after `api/schema_defs/` selector rules were added.
- `python -m unittest tests.backend.manual.test_validation_selector -v` passed
  71 tests.
- Initial `python -m pytest ...` attempts failed because PowerShell resolved
  `python` to system Python without pytest; pitfall memory matched Pitfall 81,
  and the tests were rerun with `.venv\Scripts\python.exe`.
- `.venv\Scripts\python.exe -m pytest tests/backend/user_profile/test_appearance_styles.py -q`
  passed 3 tests.
- `.venv\Scripts\python.exe -m pytest tests/backend/manual/test_manual_script_api_coverage.py -q`
  passed 7 tests.
- `.venv\Scripts\python.exe -m pytest tests/backend/learning_notes/test_learning_notes_api.py -q`
  passed 15 tests.
- `.venv\Scripts\python.exe -m pytest tests/behavior/test_notification_sync_api_edge_behavior.py -q`
  passed 10 tests.
- `.venv\Scripts\python.exe -m pytest tests/backend/homework/test_homework_llm_grading.py -q`
  passed 16 tests.
- `.venv\Scripts\python.exe -m pytest tests/backend/roster/test_student_user_api_roster_sync.py -q`
  passed 11 tests.

Latest notification schema split validation:

- `python -m py_compile apps\backend\courseeval_backend\api\schemas.py apps\backend\courseeval_backend\api\schema_defs\notifications.py ops\scripts\dev\inventory_api_schemas.py`
  passed.
- `python ops/scripts/dev/inventory_api_schemas.py --fail-on-missing-imports`
  passed with 149 local schema classes/enums, 37 compatibility re-exports, 186
  public schema names, 24 importers, and 0 missing imports.
- `python -m json.tool tests\TEST_SELECTION_TARGETS.json` passed.
- `python ops/scripts/dev/lint_validation_registry.py` passed.
- `python ops/scripts/dev/check_api_surface_governance.py` passed.
- `python ops/scripts/dev/check_boundary_governance.py --details` passed with
  existing large-file warnings; `api/schemas.py` is now 1685 lines.
- `python ops/scripts/dev/check_schema_governance.py` passed.
- `python ops/scripts/dev/select_validation_targets.py --worktree --json`
  reported targeted/static validation as acceptable and no unmatched paths.
- `python -m unittest tests.backend.manual.test_validation_selector -v` passed
  72 tests after adding a notification schema selector regression.
- `.venv\Scripts\python.exe -m pytest tests/behavior/test_notification_sync_api_edge_behavior.py -q`
  passed 10 tests.
- `.venv\Scripts\python.exe -m pytest tests/backend/homework/test_homework_llm_grading.py -q`
  passed 16 tests.
- `.venv\Scripts\python.exe -m pytest tests/backend/learning_notes/test_learning_notes_api.py -q`
  passed 15 tests.
- `.venv\Scripts\python.exe -m pytest tests/backend/roster/test_student_user_api_roster_sync.py -q`
  passed 11 tests.
- `python ops/scripts/dev/check_docs_governance.py` passed with existing
  historical missing-path warnings.
- `python ops/scripts/dev/check_repo_skills.py`,
  `python ops/scripts/dev/check_repository_normalization.py`, and
  `python ops/scripts/dev/check_structure_governance.py --details` passed.
- `python ops/scripts/dev/check_text_encoding.py --skip-if-empty ...` scanned
  8 changed text files with 0 decode errors and 0 suspicious files.
- `git diff --check` passed with only Windows line-ending normalization
  warnings for CSV/JSON files.

Latest files schema split validation:

- `python -m py_compile apps\backend\courseeval_backend\api\schemas.py apps\backend\courseeval_backend\api\schema_defs\files.py`
  passed.
- `python ops/scripts/dev/inventory_api_schemas.py --fail-on-missing-imports`
  passed with 148 local schema classes/enums, 38 compatibility re-exports, 186
  public schema names, 24 importers, and 0 missing imports.
- `python -m json.tool tests\TEST_SELECTION_TARGETS.json` passed.
- `python ops/scripts/dev/lint_validation_registry.py` passed.
- `python ops/scripts/dev/check_api_surface_governance.py` passed.
- `python ops/scripts/dev/check_boundary_governance.py --details` passed with
  existing large-file warnings; `api/schemas.py` is now 1679 lines.
- `python ops/scripts/dev/check_schema_governance.py` passed.
- `python ops/scripts/dev/select_validation_targets.py --worktree --json`
  reported targeted/static validation as acceptable and no unmatched paths.
- `python -m unittest tests.backend.manual.test_validation_selector -v` passed
  73 tests after adding a files schema selector regression.
- `.venv\Scripts\python.exe -m pytest tests\backend\files -q` passed 5 tests.
- `.venv\Scripts\python.exe -m pytest tests\backend\homework\test_homework_llm_grading.py -q`
  passed 16 tests.
- `.venv\Scripts\python.exe -m pytest tests\backend\learning_notes\test_learning_notes_api.py -q`
  passed 15 tests.
- `.venv\Scripts\python.exe -m pytest tests\backend\roster\test_student_user_api_roster_sync.py -q`
  passed 11 tests.
- `.venv\Scripts\python.exe -m pytest tests\behavior\test_notification_sync_api_edge_behavior.py -q`
  passed 10 tests.

Latest dashboard schema split validation:

- `python -m py_compile apps\backend\courseeval_backend\api\schemas.py apps\backend\courseeval_backend\api\schema_defs\dashboard.py`
  passed.
- `python ops/scripts/dev/inventory_api_schemas.py --fail-on-missing-imports`
  passed with 145 local schema classes/enums, 41 compatibility re-exports, 186
  public schema names, 24 importers, and 0 missing imports.
- `python -m json.tool tests\TEST_SELECTION_TARGETS.json` passed.
- `python ops/scripts/dev/lint_validation_registry.py` passed.
- `python ops/scripts/dev/check_api_surface_governance.py` passed.
- `python ops/scripts/dev/check_boundary_governance.py --details` passed with
  existing large-file warnings; `api/schemas.py` is now 1656 lines.
- `python ops/scripts/dev/check_schema_governance.py` passed.
- `python ops/scripts/dev/select_validation_targets.py --worktree --json`
  reported targeted/static validation as acceptable and no unmatched paths.
- `python -m unittest tests.backend.manual.test_validation_selector -v` passed
  74 tests after adding a dashboard schema selector regression.
- `.venv\Scripts\python.exe -m pytest tests\backend\integration\test_core_api_surface.py tests\backend\scores\test_score_composition.py -q`
  passed 17 tests.
- `.venv\Scripts\python.exe -m pytest tests\backend\homework\test_homework_llm_grading.py -q`
  passed 16 tests.
- `.venv\Scripts\python.exe -m pytest tests\backend\learning_notes\test_learning_notes_api.py -q`
  passed 15 tests.
- `.venv\Scripts\python.exe -m pytest tests\backend\roster\test_student_user_api_roster_sync.py -q`
  passed 11 tests.
- `.venv\Scripts\python.exe -m pytest tests\behavior\test_notification_sync_api_edge_behavior.py -q`
  passed 10 tests.

Latest roster schema split validation:

- `python -m py_compile apps\backend\courseeval_backend\api\schemas.py apps\backend\courseeval_backend\api\schema_defs\roster.py`
  passed.
- `python ops/scripts/dev/inventory_api_schemas.py --fail-on-missing-imports`
  passed with 142 local schema classes/enums, 44 compatibility re-exports, 186
  public schema names, 24 importers, and 0 missing imports.
- `python -m json.tool tests\TEST_SELECTION_TARGETS.json` passed.
- `python ops/scripts/dev/lint_validation_registry.py` passed.
- `python ops/scripts/dev/check_api_surface_governance.py` passed.
- `python ops/scripts/dev/check_boundary_governance.py --details` passed with
  existing large-file warnings; `api/schemas.py` is now 1631 lines.
- `python ops/scripts/dev/check_schema_governance.py` passed.
- `python ops/scripts/dev/select_validation_targets.py --worktree --json`
  reported targeted/static validation as acceptable and no unmatched paths.
- `python -m unittest tests.backend.manual.test_validation_selector -v` passed
  75 tests after adding a roster schema selector regression.
- `.venv\Scripts\python.exe -m pytest tests\backend\roster\test_student_user_api_roster_sync.py -q`
  passed 11 tests.
- `.venv\Scripts\python.exe -m pytest tests\backend\homework\test_homework_llm_grading.py -q`
  passed 16 tests.
- `.venv\Scripts\python.exe -m pytest tests\backend\learning_notes\test_learning_notes_api.py -q`
  passed 15 tests.
- `.venv\Scripts\python.exe -m pytest tests\behavior\test_notification_sync_api_edge_behavior.py -q`
  passed 10 tests.

For future handoff-only edits in this branch, the minimal governance rerun is:

```powershell
python ops/scripts/dev/check_docs_governance.py
python ops/scripts/dev/check_repo_skills.py
python ops/scripts/dev/check_repository_normalization.py
python ops/scripts/dev/check_structure_governance.py --details
python ops/scripts/dev/select_validation_targets.py --worktree --json
git diff --check
```

## Deferred Risks

The broad selector recommended release/security-level targets because many
router imports changed and high-blast-radius fallbacks fired. Those broad
targets were intentionally deferred for this governance round:

- `full.pytest.postgres`
- admin Playwright tiers
- `security.api_regression`

Do not claim release-quality or full security-regression coverage until those
targets are run or a maintainer explicitly accepts the narrower validation
scope.

Large files still intentionally not split or only partially split:

- `apps/backend/courseeval_backend/api/schemas.py` is partially split; continue
  moving cohesive DTO groups behind the same compatibility barrel only with
  inventory and selector-backed validation.
- `apps/backend/courseeval_backend/llm_grading.py`
- `apps/backend/courseeval_backend/domains/seed/demo.py`
- `apps/backend/courseeval_backend/api/routers/homework.py`
- large admin SPA views listed in the three-line governance report

## Next Round Targets

Recommended next work, in order:

1. Run `repository-normalization` first, then route through
   `boundary-governance` for one focused large-file split.
2. Continue `api/schemas.py` only as small DTO-group moves into
   `api/schema_defs/`, beginning with
   `python ops/scripts/dev/inventory_api_schemas.py --fail-on-missing-imports`
   and preserving the `api.schemas` compatibility barrel. Notifications, files,
   dashboard, and roster have already been split; prefer another cohesive
   low-coupling group next and avoid moving `ScoreResponse` in the same round
   as unrelated DTOs.
3. Consider extracting cohesive builders from `domains/seed/demo.py`, but only
   with seed/E2E and bootstrap-focused tests selected first.
4. Consider splitting `llm_grading.py` only under a dedicated LLM/homework
   validation matrix.
5. For frontend structure work, split large admin views by presentational
   subcomponents and run build plus targeted Playwright smoke.
6. Continue skill de-duplication only when the richer executable skill/script
   clearly covers the same workflow. Prefer shrinking broad skills into routers
   over deleting specialized ones.
