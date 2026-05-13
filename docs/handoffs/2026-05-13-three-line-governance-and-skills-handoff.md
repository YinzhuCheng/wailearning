# Three-Line Governance And Skills Handoff

Date: 2026-05-13

Branch: `cursor/repository-normalization`

## Current User Direction

The user asked to continue the repository-normalization branch, finish the
three-line governance round, structure the repo-local skills hierarchy, remove
redundant simple skills/scripts only when a richer precise version already
covers the behavior, and commit/push the result.

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

Before final commit/push, rerun the current minimal governance checks after
this handoff edit:

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

Large files intentionally not split in this pass:

- `apps/backend/courseeval_backend/api/schemas.py`
- `apps/backend/courseeval_backend/llm_grading.py`
- `apps/backend/courseeval_backend/domains/seed/demo.py`
- `apps/backend/courseeval_backend/api/routers/homework.py`
- large admin SPA views listed in the three-line governance report

## Next Round Targets

Recommended next work, in order:

1. Run `repository-normalization` first, then route through
   `boundary-governance` for one focused large-file split.
2. If splitting `api/schemas.py`, begin with
   `python ops/scripts/dev/inventory_api_schemas.py --fail-on-missing-imports`
   and preserve compatibility imports or an explicit export barrel.
3. Consider extracting cohesive builders from `domains/seed/demo.py`, but only
   with seed/E2E and bootstrap-focused tests selected first.
4. Consider splitting `llm_grading.py` only under a dedicated LLM/homework
   validation matrix.
5. For frontend structure work, split large admin views by presentational
   subcomponents and run build plus targeted Playwright smoke.
6. Continue skill de-duplication only when the richer executable skill/script
   clearly covers the same workflow. Prefer shrinking broad skills into routers
   over deleting specialized ones.
