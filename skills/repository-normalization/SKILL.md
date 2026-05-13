---
name: repository-normalization
description: Top-level CourseEval governance orchestrator for repository normalization, three-line governance, skill taxonomy, docs-as-governance, package/path/name drift, and deciding when to route into docs-governance, boundary-governance, structure-governance, validation-selection, validation-ledger-maintenance, or specialized audit skills.
---

# Repository Normalization

## Purpose

Coordinate CourseEval repository governance without becoming a duplicate of
specialized skills. Use this as the top-level entrypoint for code-as-docs,
docs-as-governance, package/name drift, three-line governance, skill taxonomy,
and handoff preparation.

## Skill Layers

1. Top-level orchestrator: this skill.
2. Horizontal governance: `skills/docs-governance/SKILL.md`,
   `skills/boundary-governance/SKILL.md`, and
   `skills/structure-governance/SKILL.md`.
3. Specialized audit skills:
   - permissions: `skills/permission-audit/SKILL.md`;
   - API contracts: `skills/api-surface-audit/SKILL.md`;
   - frontend/backend request contracts:
     `skills/frontend-backend-contract-audit/SKILL.md`;
   - schema/bootstrap/data repair: `skills/data-migration-audit/SKILL.md`;
   - deployment/ops: `skills/deployment-governance/SKILL.md`;
   - seed/E2E dev surface: `skills/seed-surface-hardening/SKILL.md`;
   - Playwright: `skills/admin-playwright-e2e/SKILL.md`;
   - PostgreSQL release gates: `skills/postgres-release-validation/SKILL.md`;
   - UTF-8 editing: `skills/utf8-safe-editing/SKILL.md`;
   - local failures: `skills/local-test-triage/SKILL.md`.
4. Validation and evidence:
   `skills/validation-selection/SKILL.md` and
   `skills/validation-ledger-maintenance/SKILL.md`.

## Workflow

1. Read `AGENTS.md`, `docs/README.md`, and task-scoped docs.
2. Decide whether this is a three-line governance task:
   - docs or process: use `docs-governance`;
   - module/import/ownership boundary: use `boundary-governance`;
   - root layout, moves, or directory hierarchy: use `structure-governance`.
3. Route any high-risk domain to the specialized skill instead of copying its
   rules here.
4. Search code and tests before trusting documentation claims.
5. Classify old names as historical records or active drift.
6. Update docs in the same change set as behavior, config, path, or service
   changes.
7. Prefer CSV/JSON/YAML for append-only structured ledgers; keep Markdown as
   the interpretation layer.
8. Add or update executable checks when a repeated rule can be automated.
9. Use `validation-selection` for target choice and
   `validation-ledger-maintenance` for durable evidence.

## Closeout Conditions

Before ending a repository-normalization sequence, make the state durable:

- classify each touched boundary as accepted, active follow-up, or explicitly
  deferred;
- sync `AGENTS.md`, `docs/README.md`, architecture/reference docs, the active
  handoff, and `docs/testing/agent-update-log.csv` when they are
  part of the task surface;
- record selector output and the static/runtime validation actually run;
- keep private planning notes, `.agent-run/`, `.pytest_cache/`, `.pytest_tmp/`,
  and other generated artifacts out of commits.

Treat `check_boundary_governance.py --details` warnings as candidates, not as
automatic refactor orders. A warning is closed only when the code is split with
focused validation or when durable docs explain why the current boundary is
accepted or deferred.

## De-Duplication Rule

Keep the most precise, executable skill or script as the source of truth. Do
not preserve a simple, broad checklist when a richer specialized skill or guard
script covers the same behavior. If a broad skill is still useful, reduce it to
routing, scope control, and validation coordination.

## Commands

```powershell
git status --short --branch
python ops/scripts/dev/check_repo_skills.py
python ops/scripts/dev/select_validation_targets.py --worktree
python ops/scripts/dev/check_repository_normalization.py
python ops/scripts/dev/check_docs_governance.py
python ops/scripts/dev/check_boundary_governance.py --details
python ops/scripts/dev/check_structure_governance.py --details
python ops/scripts/dev/check_text_encoding.py --fail-on-suspicious <changed-file>
git diff --check
```

For multilingual files:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ops\scripts\windows\safe-text-workflow.ps1 -Path <repo-relative-path>
```

## Checks

- Current names remain `CourseEval`, `apps.backend.courseeval_backend`,
  `courseeval-backend.service`, and `ops/nginx/courseeval.example*.conf`.
- Retired names appear only in historical notes, append-only ledgers, or
  explicit "do not restore" warnings.
- Documentation claims cite current code paths, config, tests, or scripts.
- Skill references use existing `skills/<name>/SKILL.md` paths.
- Validation failures are recorded with command, symptom, likely cause, and next step.

## Failure Handling

If a script reports stale names, classify each hit:

- historical record: preserve and document why it is allowed;
- active drift: update the doc/code/template;
- uncertain behavior: mark as `待验证` or "needs audit" and add a follow-up.

If tests cannot run, record the environment blocker rather than claiming the
change is verified.

## Related Files

- `AGENTS.md`
- `docs/README.md`
- `docs/contributing/ENCODING_AND_MOJIBAKE_SAFETY.md`
- `docs/testing/README.md`
- `docs/operations/DEPLOYMENT_AND_OPERATIONS.md`
- `skills/docs-governance/SKILL.md`
- `skills/boundary-governance/SKILL.md`
- `skills/structure-governance/SKILL.md`
- `ops/scripts/dev/check_repo_skills.py`
- `ops/scripts/dev/check_repository_normalization.py`
- `ops/scripts/dev/check_text_encoding.py`
