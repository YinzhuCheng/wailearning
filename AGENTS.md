# AGENTS — CourseEval Agent Startup Contract

## Purpose

This file is the **startup contract and task router** for coding agents working
in this repository. Read it before editing code, docs, tests, scripts, or
repository structure.

Use this file to answer:

- what must be true before you start;
- which docs or skills to open next;
- which boundaries remain high-risk;
- where validation and CI entrypoints live.

For the full documentation hub, start at [`docs/README.md`](docs/README.md).

## Governance model

CourseEval treats **code as documentation** and **documentation as
governance**.

- Use code as the source of truth for current implementation behavior.
- Use committed docs, skills, and scripts for durable rules and repeated
  workflows.
- Use [`docs/governance/repository-governance.md`](docs/governance/repository-governance.md)
  for the full repository governance model.

## Non-negotiable operating rules

1. Use [`docs/README.md`](docs/README.md) as the task-scoped reading gate
   before editing.
2. Use the canonical backend import root
   `apps.backend.courseeval_backend`; keep package-boundary work aligned with
   [`docs/architecture/REPOSITORY_STRUCTURE.md`](docs/architecture/REPOSITORY_STRUCTURE.md).
3. Use backend authorization as the real permission boundary. Frontend hiding
   does not replace router or domain enforcement.
4. Use UTF-8-safe editing practices on Windows PowerShell; start with
   [`docs/contributing/ENCODING_AND_MOJIBAKE_SAFETY.md`](docs/contributing/ENCODING_AND_MOJIBAKE_SAFETY.md).
   The default Windows text-workflow entrypoint is
   `powershell.exe -NoProfile -ExecutionPolicy Bypass -File ops/scripts/windows/enter-safe-text-session.ps1`.
5. Use `.agent-run/` for local-only logs, private paths, and machine-specific
   continuation notes; keep durable repository context in committed docs. See
   [`docs/agents/local-agent-workspace.md`](docs/agents/local-agent-workspace.md).
   Use `.agent-run/plan/` for local private plan files and remove a plan file
   after the plan is fully executed or superseded.
   Use `pics/` for local image handoff from the user to the agent, including
   screenshots the agent creates during UI work.
   Treat files in `pics/` as local-only by default. Do not push them to any
   remote unless the user explicitly asks for that; screenshots in `pics/`
   should generally remain unpushed.
   Use `apps/web/school/scripts/capture-homework-layout-runner.cjs` plus
   `npm.cmd run capture:homework-layout` from `apps/web/school` for the
   maintained homework-layout simulation and screenshot workflow; default
   output is `pics/homework-layout-fixed.png`.
   Use committed handoff documents under [`docs/handoffs/`](docs/handoffs/README.md)
   when the user asks for cross-session continuation. The current appeal-notification
   system hardening handoff is
   [`docs/handoffs/APPEAL_NOTIFICATION_SYSTEM_HARDENING_HANDOFF_2026-05-14.md`](docs/handoffs/APPEAL_NOTIFICATION_SYSTEM_HARDENING_HANDOFF_2026-05-14.md).
6. Use the pitfall search before classifying local failures:
   `python ops/scripts/dev/search_pitfalls.py "<symptom>"`.
7. Use the diff-based validation selector before broad manual test selection:
   `python ops/scripts/dev/select_validation_targets.py --worktree`.
8. At the end of every round, clean local reproducible artifacts under
   `C:\Users\bloom\wailearning\.agent-run` and other safe cache locations with
   `python ops/scripts/dev/clean_local_artifacts.py`.
   Run a dry-run first, then apply the cleanup when the action list is limited
   to reproducible caches or local housekeeping/archival targets:
   `python ops/scripts/dev/clean_local_artifacts.py`
   `python ops/scripts/dev/clean_local_artifacts.py --apply`
9. After completing a repeated or failure-prone workflow, explicitly decide
   whether it should become a committed script or repo-local skill.
   Prefer scripts for stable executable workflows and skills for routing or
   multi-step agent procedure; do not leave frequently reused workflows as
   ad hoc terminal lore.

High-risk hard boundaries that stay explicit:

- Do not weaken `/api/e2e/dev/*` exposure gates without tracing the current E2E
  contract in [`docs/testing/DEVELOPMENT_AND_TESTING.md`](docs/testing/DEVELOPMENT_AND_TESTING.md).

## Startup workflow

1. Read this file.
2. Read [`docs/README.md`](docs/README.md).
3. Read [`docs/governance/repository-governance.md`](docs/governance/repository-governance.md).
4. Open the task-specific docs listed in `docs/README.md` under **Mandatory
   reading by task**.
5. If this machine already has local continuation artifacts, read the
   task-relevant files under `.agent-run/`, especially `.agent-run/plan/` when
   a local execution plan exists for the task.
6. If the task is non-trivial, route into the appropriate skill from
   [`skills/README.md`](skills/README.md) before planning edits.

Detailed operational defaults, tracing workflow, and documentation-maintenance
triggers live in [`docs/agents/agent-playbook.md`](docs/agents/agent-playbook.md).

## Task routing

Use the nearest authoritative doc or skill for the task type:

| Task type | Read first | Skill | Validate first |
|----------|------------|-------|----------------|
| Docs, links, entrypoint wording, or governance-doc edits | [`docs/governance/repository-governance.md`](docs/governance/repository-governance.md) | [`skills/docs-governance/SKILL.md`](skills/docs-governance/SKILL.md) | `static.docs_governance` |
| Module boundaries, permission/data-flow boundaries, or low-risk extractions | [`docs/reference/PERMISSIONS_AND_SECURITY_BOUNDARIES.md`](docs/reference/PERMISSIONS_AND_SECURITY_BOUNDARIES.md) | [`skills/boundary-governance/SKILL.md`](skills/boundary-governance/SKILL.md) | `static.boundary_governance` |
| Repository/path/layout changes | [`docs/architecture/REPOSITORY_STRUCTURE.md`](docs/architecture/REPOSITORY_STRUCTURE.md) | [`skills/structure-governance/SKILL.md`](skills/structure-governance/SKILL.md) | `static.structure_governance` |
| Repo-wide governance, naming/path drift, entrypoint cleanup | [`docs/governance/repository-governance.md`](docs/governance/repository-governance.md) | [`skills/repository-normalization/SKILL.md`](skills/repository-normalization/SKILL.md) | `check_repository_normalization.py` |
| Backend/API contract changes | [`docs/architecture/SYSTEM_OVERVIEW.md`](docs/architecture/SYSTEM_OVERVIEW.md) | [`skills/api-surface-audit/SKILL.md`](skills/api-surface-audit/SKILL.md) | `static.api_surface_governance` |
| Permissions/course access/sensitive role behavior | [`docs/reference/PERMISSIONS_AND_SECURITY_BOUNDARIES.md`](docs/reference/PERMISSIONS_AND_SECURITY_BOUNDARIES.md) | [`skills/permission-audit/SKILL.md`](skills/permission-audit/SKILL.md) | `security.api_regression` |
| Schema/bootstrap/student identity | [`docs/operations/ADMIN_BOOTSTRAP.md`](docs/operations/ADMIN_BOOTSTRAP.md) | [`skills/data-migration-audit/SKILL.md`](skills/data-migration-audit/SKILL.md) / [`skills/roster-identity-repair-playbook/SKILL.md`](skills/roster-identity-repair-playbook/SKILL.md) | `static.schema_governance` |
| School Playwright or browser-harness work | [`docs/testing/FULL_PLAYWRIGHT_E2E_RUNBOOK.md`](docs/testing/FULL_PLAYWRIGHT_E2E_RUNBOOK.md) | [`skills/school-playwright-e2e/SKILL.md`](skills/school-playwright-e2e/SKILL.md) | `frontend.school.build` plus the nearest `school.e2e.*` target |
| Local pytest/Playwright/SQLite/process failures | [`docs/testing/TEST_EXECUTION_PITFALLS.md`](docs/testing/TEST_EXECUTION_PITFALLS.md) or the matching topic route | [`skills/local-test-triage/SKILL.md`](skills/local-test-triage/SKILL.md) | `static.local_test_guardrails` when the issue is harness-shaped |
| Validation target choice and evidence | [`docs/testing/DEVELOPMENT_AND_TESTING.md`](docs/testing/DEVELOPMENT_AND_TESTING.md) | [`skills/validation-selection/SKILL.md`](skills/validation-selection/SKILL.md) / [`skills/validation-ledger-maintenance/SKILL.md`](skills/validation-ledger-maintenance/SKILL.md) | `static.validation_selector` |
| Deployment/ops/runtime config | [`docs/operations/DEPLOYMENT_AND_OPERATIONS.md`](docs/operations/DEPLOYMENT_AND_OPERATIONS.md) | [`skills/deployment-governance/SKILL.md`](skills/deployment-governance/SKILL.md) | `static.operator_scripts_governance` when operator scripts or templates move |
| Full skill catalog and layering | [`skills/README.md`](skills/README.md) | route from there | use the routed validation entrypoint |

## High-risk areas

Trace these with a focused plan before editing:

1. `apps/backend/courseeval_backend/llm_grading.py`
2. `apps/backend/courseeval_backend/domains/courses/access.py`
3. `apps/backend/courseeval_backend/bootstrap.py` and `apps/backend/courseeval_backend/main.py` lifespan
4. `apps/backend/courseeval_backend/api/routers/e2e_dev.py`
5. `apps/backend/courseeval_backend/api/routers/homework.py`

Use [`docs/architecture/HIGH_RISK_MODULES.md`](docs/architecture/HIGH_RISK_MODULES.md)
for the expanded explanations and related docs/skills.

## Fast grep map

Use this short map as the first jump only:

| Intent | Start grep |
|--------|------------|
| Course access and visibility | `get_accessible_courses_query`, `ensure_course_access_http`, `prepare_student_course_context` |
| Homework serialization and effective score | `_serialize_homework`, `_serialize_submission`, `resolve_effective_submission_score`, `effective_score_note_zh` |
| Grading queue and worker | `HomeworkGradingTask`, `queue_grading_task`, `process_next_grading_task`, `_WorkerManager`, `start_grading_worker` |
| Quota policy | `precheck_quota`, `reserve_quota_tokens`, `LLMGlobalQuotaPolicy` |
| Demo seed and E2E reset | `seed_demo_course_bundle`, `INIT_DEFAULT_DATA`, `expose_e2e_dev_api`, `E2E_DEV_SEED_ENABLED` |
| Schema repair | `ensure_schema_updates`, `bootstrap.py` |

Use [`docs/reference/CODE_MAP_AND_ENTRYPOINTS.md`](docs/reference/CODE_MAP_AND_ENTRYPOINTS.md)
for the full file-level map and extended grep surface.

## Failure triage entrypoint

Start every ambiguous local failure with:

```powershell
python ops/scripts/dev/search_pitfalls.py "<error text or symptom>"
```

Then route through:

- [`docs/testing/TEST_EXECUTION_PITFALLS.md`](docs/testing/TEST_EXECUTION_PITFALLS.md)
- [`docs/testing/pitfalls-windows-and-encoding.md`](docs/testing/pitfalls-windows-and-encoding.md)
- [`docs/testing/pitfalls-playwright-and-e2e.md`](docs/testing/pitfalls-playwright-and-e2e.md)
- [`docs/testing/pitfalls-postgres-and-pytest.md`](docs/testing/pitfalls-postgres-and-pytest.md)
- [`docs/testing/pitfalls-ledger-and-selector-tooling.md`](docs/testing/pitfalls-ledger-and-selector-tooling.md)
- [`docs/architecture/TROUBLESHOOTING.md`](docs/architecture/TROUBLESHOOTING.md)
- [`skills/local-test-triage/SKILL.md`](skills/local-test-triage/SKILL.md)

Use repository pitfall docs and tooling for repeatable execution traps; do not
guess whether a failure is product, harness, or environment shaped.

## Validation entrypoint

Use change-scoped validation by default unless the user explicitly asks for
full-suite, release-quality, or zero-skip validation.

Start with:

```powershell
python ops/scripts/dev/select_validation_targets.py --worktree
```

Use the repository default `strict` workflow unless the user explicitly asks
for a lighter guided route.

Strict mode means:

- start from `AGENTS.md`, `docs/README.md`,
  `docs/governance/repository-governance.md`,
  `docs/testing/DEVELOPMENT_AND_TESTING.md`,
  `docs/testing/CI_AND_VALIDATION.md`, and
  `docs/testing/TEST_EXECUTION_PITFALLS.md`;
- then read the task-scoped docs and skills already routed elsewhere in this
  file;
- if code behavior, permissions, config, validation flow, or workflow
  contracts change, update committed docs in the same round;
- use the pitfall search before classifying ambiguous failures;
- use selector output and observed validation honestly;
- update durable logs and ledgers when the round changed the repository.

Guided mode means:

- the user explicitly chose a lighter route;
- startup docs still matter, but task-specific reading is advisory rather than
  hard-locked;
- the agent may choose a narrower reading path first and expand if needed;
- guided evidence must never be reported as strict completion.

Then use the detailed workflow in:

- [`docs/testing/DEVELOPMENT_AND_TESTING.md`](docs/testing/DEVELOPMENT_AND_TESTING.md)
- [`skills/validation-selection/SKILL.md`](skills/validation-selection/SKILL.md)

Use repository-normalization guardrails for docs/governance/path work:

```powershell
python ops/scripts/dev/check_repository_normalization.py
```

## CI entrypoints

Use these as the current cloud validation entrypoints:

- [`.github/workflows/lightweight-validation.yml`](.github/workflows/lightweight-validation.yml)
- [`ops/ci/`](ops/ci/)

Use [`docs/testing/CI_AND_VALIDATION.md`](docs/testing/CI_AND_VALIDATION.md)
for current scope, non-goals, and how to report local versus remote validation
honestly.
