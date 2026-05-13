# Three-Line Governance Report — 2026-05-13

## Purpose

This report records the first three-line governance pass requested for the
`cursor/repository-normalization` branch:

1. docs governance,
2. boundary governance,
3. structure governance.

The pass intentionally favored low-risk, high-signal changes over broad
behavioral refactors. High-risk findings are recorded here for a later,
dedicated task with focused tests.

## Skills Added

| Skill | Purpose |
|-------|---------|
| [`../../skills/docs-governance/SKILL.md`](../../skills/docs-governance/SKILL.md) | Refine README, AGENTS.md, docs, testing/development/deployment guidance, documentation links, and repeated-pitfall rules. |
| [`../../skills/boundary-governance/SKILL.md`](../../skills/boundary-governance/SKILL.md) | Identify large files, mixed responsibilities, cross-layer imports, module ownership drift, and safe low-risk boundary extractions. |
| [`../../skills/structure-governance/SKILL.md`](../../skills/structure-governance/SKILL.md) | Enforce root-file and directory hierarchy contracts, safe file moves, path reference updates, and structural cleanup rules. |

## Skill Taxonomy Cleanup

After the first pass, the governance skills were refined into a layered model
instead of a flat list:

1. [`../../skills/repository-normalization/SKILL.md`](../../skills/repository-normalization/SKILL.md)
   is the top-level orchestrator for repository normalization, skill taxonomy,
   and three-line governance routing.
2. `docs-governance`, `boundary-governance`, and `structure-governance` are
   horizontal governance entrypoints.
3. Specialized skills such as `permission-audit`, `api-surface-audit`,
   `frontend-backend-contract-audit`, `data-migration-audit`,
   `deployment-governance`, `seed-surface-hardening`, `admin-playwright-e2e`,
   `postgres-release-validation`, `local-test-triage`, and
   `utf8-safe-editing` remain the richer sources of truth for their domains.
4. `validation-selection` and `validation-ledger-maintenance` remain the
   validation/evidence layer.

No mature specialized skill was deleted. The de-duplication rule is now: keep
the more precise, executable skill or script as the source of truth; reduce
broader overlapping skills to orchestration, routing, and scope control. The
previously missing `agents/openai.yaml` metadata for
`repository-normalization` was added, and `check_repo_skills.py` now validates
`skills/<name>/SKILL.md` references in skill bodies.

## Scripts Added

| Script | Purpose |
|--------|---------|
| [`../../ops/scripts/dev/governance_common.py`](../../ops/scripts/dev/governance_common.py) | Shared tracked-file, text-file, line-count, and finding helpers for governance checks. |
| [`../../ops/scripts/dev/check_docs_governance.py`](../../ops/scripts/dev/check_docs_governance.py) | Checks required doc entrypoints, new governance-skill indexing, Markdown links, and likely stale bare path mentions. |
| [`../../ops/scripts/dev/check_boundary_governance.py`](../../ops/scripts/dev/check_boundary_governance.py) | Reports large implementation files and suspicious backend import edges such as router-to-router imports. |
| [`../../ops/scripts/dev/inventory_api_schemas.py`](../../ops/scripts/dev/inventory_api_schemas.py) | Inventories `api/schemas.py` schema classes, domain buckets, direct importers, references, and `model_rebuild()` calls before any schema split. |
| [`../../ops/scripts/dev/check_structure_governance.py`](../../ops/scripts/dev/check_structure_governance.py) | Checks tracked root entries, unexpected root files/directories, duplicate root semantics, and tiny docs. |
| [`../../ops/scripts/dev/check_repo_skills.py`](../../ops/scripts/dev/check_repo_skills.py) | Updated to reject missing skill-to-skill references and require `agents/openai.yaml` for every repo-local skill. |

The governance checks walk the working tree while skipping ignored local
artifacts, so newly created skills, reports, and scripts are checked before
they are staged.

## Low-Risk Changes Applied

### Docs governance

- Added the three governance skills to `AGENTS.md` and `docs/README.md`.
- Added this report to the docs hub.
- Fixed relative Markdown links in historical reports that became invalid after
  those reports moved under `docs/reports/`.
- Added a report rule that committed raw logs must live under
  `docs/reports/artifacts/`, have dated descriptive names, and contain no
  private paths or secrets.

### Boundary governance

- Moved class-scope helper ownership out of the `classes` router into
  [`../../apps/backend/courseeval_backend/domains/courses/class_scope.py`](../../apps/backend/courseeval_backend/domains/courses/class_scope.py).
- Updated all class-adjacent routers to import
  `get_accessible_class_ids` / `apply_class_id_filter` from the domain module
  instead of importing `api.routers.classes`.
- Added a read-only `api/schemas.py` inventory script instead of splitting that
  large barrel during this broad governance pass. Current inventory: 189
  schema classes/enums, 24 direct importers, 163 imported schema names, 3
  `model_rebuild()` calls, and 0 missing imported names.
- Updated backend package and code-map docs with the new helper location.

### Structure governance

- Removed the tracked root log `error.txt` after user confirmation that it was
  obsolete historical pytest output and no longer needed as committed evidence.
- Before removal, the file was checked for in-repo references and obvious
  private Windows paths, secrets, tokens, and the local proxy string.

## File Moves / Splits

| Change | Reason | Risk |
|--------|--------|------|
| Deleted `error.txt` | Root directory should contain only repository-level contract files; user confirmed the historical pytest log was no longer useful. | Low; no in-repo references existed. |
| New `domains/courses/class_scope.py` extracted from `api/routers/classes.py` | Avoid router-to-router imports and clarify that class-scope filtering is shared domain logic, not class-router ownership. | Low; pure helper move with unchanged function bodies and targeted import updates. |

## Boundary Findings Deferred

`check_boundary_governance.py --details` identified large files that deserve
dedicated follow-up. They were not split in this pass because each one owns
user-visible behavior and needs focused tests.

| Area | Current finding |
|------|-----------------|
| Backend | `domains/seed/demo.py`, `llm_grading.py`, `api/schemas.py`, `api/routers/homework.py`, `bootstrap.py`, `api/routers/subjects.py` exceed governance thresholds. |
| Admin SPA | `Materials.vue`, `Subjects.vue`, `LearningNotes.vue`, `MyCourses.vue`, `Layout.vue`, `Students.vue`, `CourseDiscussionPanel.vue`, and related views exceed governance thresholds. |

Recommended next boundary work:

1. Split `api/schemas.py` by response/request domain only after running
   `python ops/scripts/dev/inventory_api_schemas.py --fail-on-missing-imports`
   and preserving compatibility imports or a deliberate export barrel. The
   current hard forward-reference points are `SubjectCreate.model_rebuild()`,
   `CourseMaterialChapterNode.model_rebuild()`, and
   `LearningNoteChapterNode.model_rebuild()`.
2. Extract cohesive demo-seed builders from `domains/seed/demo.py`.
3. Split `llm_grading.py` only with LLM/homework queue tests selected first.
4. Split large admin views by presentational subcomponents after a frontend
   build and targeted Playwright smoke are available.

## Validation Performed

This pass introduced governance scripts and a low-risk helper extraction. The
following checks were run from the repository root.

| Command | Result |
|---------|--------|
| `python -m py_compile ops/scripts/dev/governance_common.py ops/scripts/dev/check_docs_governance.py ops/scripts/dev/check_boundary_governance.py ops/scripts/dev/check_structure_governance.py apps/backend/courseeval_backend/domains/courses/class_scope.py` | Passed. |
| `python -m py_compile ops/scripts/dev/inventory_api_schemas.py` | Passed. |
| `python ops/scripts/dev/inventory_api_schemas.py --fail-on-missing-imports` | Passed: 189 schema classes/enums, 24 direct importers, 0 missing imported names. |
| `python -m json.tool tests/TEST_SELECTION_TARGETS.json` | Passed. |
| `python ops/scripts/dev/lint_validation_registry.py` | Passed. |
| `python ops/scripts/dev/check_docs_governance.py` | Passed with warnings only for historical/migration notes that mention removed paths. No broken Markdown-link errors remained. |
| `python ops/scripts/dev/check_boundary_governance.py --details` | Passed with large-file warnings only; router-to-router imports were eliminated. |
| `python ops/scripts/dev/check_structure_governance.py --details` | Passed with no findings after deleting the obsolete root log artifact. |
| `python ops/scripts/dev/check_repo_skills.py` | Passed. |
| `python ops/scripts/dev/check_repository_normalization.py` | Passed: `stale=0`, `missing_required_paths=0`. |
| `python ops/scripts/dev/check_api_surface_governance.py` | Passed. |
| `python -m unittest tests.backend.manual.test_validation_selector -v` | Passed: 70 tests after adding governance, manual-script selector coverage, and skill-reference integrity coverage. |
| `python ops/scripts/dev/select_validation_targets.py --worktree --json` | Passed selector execution with `unmatched_paths: []`; status remained `not_sufficient` because broad fallback targets were recommended. |
| `.\.venv\Scripts\python.exe -m pytest tests\backend\manual\test_manual_script_api_coverage.py -q` | Passed: 7 tests. |
| `.\.venv\Scripts\python.exe -m pytest tests\backend\courses\test_student_course_roster_behavior.py tests\behavior\test_course_roster_homework_edge_behavior.py tests\backend\integration\test_core_api_surface.py -q` | Passed: 40 tests. |
| `git diff --check` | Passed. |

The first attempt to run pytest through bare `python` failed because that
interpreter lacked `pytest`. The pitfall memory already documents this class of
environment failure; rerunning the same targets with the repository `.venv`
interpreter passed.

## Deferred Validation

```powershell
python ops/scripts/dev/select_validation_targets.py --worktree
```

The selector recommended broad/full targets because many routers changed import
lines and the fallback high-blast-radius rule fired:

- `full.pytest.postgres`
- several admin Playwright tiers
- `security.api_regression`

Those were not run in this governance round. The code change was a pure helper
move with unchanged function bodies and targeted import updates, so this pass
used static checks plus focused backend tests. Run the deferred targets before
claiming release-quality or security-regression coverage for this branch.
