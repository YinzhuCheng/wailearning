# Documentation Hub

This directory is the authoritative documentation home for the repository. The root [`README.md`](../README.md) is the public entry point; everything else lives here.

---

## Directory map

Every subdirectory under `docs/` has its own `README.md` that defines its
scope. Keep new documents in the most specific topic folder first.

| Directory | Use for |
|-----------|---------|
| [agents/](agents/README.md) | LLM-agent playbooks and autonomous-workflow guidance |
| [architecture/](architecture/README.md) | System structure, package boundaries, configuration maps, troubleshooting |
| [assets/](assets/README.md) | Committed documentation assets only |
| [contributing/](contributing/README.md) | Git, encoding, and contributor workflow |
| [development/](development/README.md) | Sparse compatibility bucket; prefer a specific topic folder |
| [frontend/](frontend/README.md) | Browser/UI-state behavior and frontend interaction contracts |
| [governance/](governance/README.md) | Active risks, ownership ambiguity, durable repository rules |
| [handoffs/](handoffs/README.md) | Explicit user-requested committed handoffs |
| [operations/](operations/README.md) | Deployment, bootstrap, runtime operations |
| [product/](product/README.md) | Product behavior and domain concepts |
| [reference/](reference/README.md) | Lookup maps, permissions, and data model references |
| [reports/](reports/README.md) | Dated reports that remain useful historical evidence |
| [testing/](testing/README.md) | Test runbooks, pitfalls, validation maps, CSV ledgers |

---

## 0. LLM agent bundle (read before autonomous edits)

These files intentionally overlap with human-oriented docs — **verbosity is a feature** for coding agents.

| Document | Role |
|----------|------|
| [`AGENTS.md`](../AGENTS.md) (repository root) | Primary agent gate: boundaries, grep keywords, risky modules |
| [`agents/agent-playbook.md`](agents/agent-playbook.md) | Procedural workflows: tracing features, bootstrap order, verification |
| [`reference/CODE_MAP_AND_ENTRYPOINTS.md`](reference/CODE_MAP_AND_ENTRYPOINTS.md) | File-level map of routers, SPAs, tests, CI YAML |
| [`reference/PERMISSIONS_AND_SECURITY_BOUNDARIES.md`](reference/PERMISSIONS_AND_SECURITY_BOUNDARIES.md) | Roles, course access helpers, JWT vs parent-code |
| [`reference/DATA_MODEL_ESSENTIALS.md`](reference/DATA_MODEL_ESSENTIALS.md) | ORM tables grouped by domain |
| [`architecture/ASYNC_TASKS_AND_WORKERS.md`](architecture/ASYNC_TASKS_AND_WORKERS.md) | LLM grading worker (DB queue + thread pool) |
| [`governance/known-issues-and-risks.md`](governance/known-issues-and-risks.md) | Open risks, “待人工确认”, CI location honesty |
| [`../skills/repository-normalization/SKILL.md`](../skills/repository-normalization/SKILL.md) | Top-level governance orchestrator for repo normalization, skill taxonomy, and three-line routing |
| [`../skills/docs-governance/SKILL.md`](../skills/docs-governance/SKILL.md) | Horizontal docs governance: documentation truth, link checks, reports, and repeated-pitfall-to-rule workflow |
| [`../skills/boundary-governance/SKILL.md`](../skills/boundary-governance/SKILL.md) | Horizontal boundary governance: functional/module/permission/data-flow boundary discovery and low-risk extraction workflow |
| [`../skills/structure-governance/SKILL.md`](../skills/structure-governance/SKILL.md) | Horizontal structure governance: root-file, directory hierarchy, file-move, and structural reference workflow |
| [`../skills/security-redteam-iteration/SKILL.md`](../skills/security-redteam-iteration/SKILL.md) | Iterative red-team hardening workflow with dense tests, fixes, docs, ledgers, pitfalls, validation, and commit discipline |
| [`../skills/validation-selection/SKILL.md`](../skills/validation-selection/SKILL.md) | Change-scoped validation selection and honest validation reporting |
| [`../skills/validation-ledger-maintenance/SKILL.md`](../skills/validation-ledger-maintenance/SKILL.md) | Validation registry, `ledger_id`, CSV target/run history, and selector-history maintenance |
| [`../skills/utf8-safe-editing/SKILL.md`](../skills/utf8-safe-editing/SKILL.md) | UTF-8-safe editing for multilingual / PowerShell-sensitive files |
| [`../skills/permission-audit/SKILL.md`](../skills/permission-audit/SKILL.md) | Backend authorization, role-boundary, and course-access audit workflow |
| [`../skills/deployment-governance/SKILL.md`](../skills/deployment-governance/SKILL.md) | Deployment script, env template, nginx/systemd, and ops-doc governance |
| [`../skills/local-test-triage/SKILL.md`](../skills/local-test-triage/SKILL.md) | Local pytest / SQLite / Playwright / process hazard triage |
| [`../skills/admin-playwright-e2e/SKILL.md`](../skills/admin-playwright-e2e/SKILL.md) | Repo-supported admin Playwright E2E execution, external-runner usage, and browser-harness triage |
| [`../skills/data-migration-audit/SKILL.md`](../skills/data-migration-audit/SKILL.md) | Schema repair, migration audit, and no-Alembic data-governance workflow |
| [`../skills/api-surface-audit/SKILL.md`](../skills/api-surface-audit/SKILL.md) | FastAPI router, frontend API client, API-doc, and route-contract audit workflow |
| [`../skills/frontend-backend-contract-audit/SKILL.md`](../skills/frontend-backend-contract-audit/SKILL.md) | Vue/FastAPI request contract, pagination, bounds, and response-shape audit workflow |
| [`../skills/roster-identity-repair-playbook/SKILL.md`](../skills/roster-identity-repair-playbook/SKILL.md) | Student identity, `users.student_id`, roster drift, and repair workflow |
| [`../skills/postgres-release-validation/SKILL.md`](../skills/postgres-release-validation/SKILL.md) | PostgreSQL-backed package/full-suite validation workflow |
| [`../skills/seed-surface-hardening/SKILL.md`](../skills/seed-surface-hardening/SKILL.md) | E2E dev, default seed, first-admin, public registration, and local/demo surface hardening |

---

## 1. Start here (architecture + operations)

| Document | Purpose |
|----------|---------|
| [architecture/SYSTEM_OVERVIEW.md](architecture/SYSTEM_OVERVIEW.md) | Capabilities, components, route families |
| [architecture/CORE_BUSINESS_FLOWS.md](architecture/CORE_BUSINESS_FLOWS.md) | **Vertical slices** — how homework grading, notifications, and E2E gates actually run (code anchors) |
| [architecture/CONFIGURATION_REFERENCE.md](architecture/CONFIGURATION_REFERENCE.md) | **Single env var index** — maps to `core/config.py` and Vite dev vars |
| [architecture/MAINTAINER_AGENT_GUIDE.md](architecture/MAINTAINER_AGENT_GUIDE.md) | **Grep keywords**, risky modules, test expectations for agents |
| [architecture/TROUBLESHOOTING.md](architecture/TROUBLESHOOTING.md) | Symptom-first links into pitfalls and ops docs |
| [architecture/REPOSITORY_STRUCTURE.md](architecture/REPOSITORY_STRUCTURE.md) | Source vs artifact; import namespace contract |
| [architecture/BACKEND_PACKAGE_STRUCTURE.md](architecture/BACKEND_PACKAGE_STRUCTURE.md) | Layer model inside `courseeval_backend` |
| [reports/README.md](reports/README.md) | Boundary rules for dated audits and remediation reports |
| [operations/DEPLOYMENT_AND_OPERATIONS.md](operations/DEPLOYMENT_AND_OPERATIONS.md) | Production layout, nginx, systemd, env templates |
| [operations/ADMIN_BOOTSTRAP.md](operations/ADMIN_BOOTSTRAP.md) | Startup ordering, seed behavior |

---

## 2. Product features

| Document | Purpose |
|----------|---------|
| [product/LLM_HOMEWORK_GUIDE.md](product/LLM_HOMEWORK_GUIDE.md) | LLM entities, quotas, async worker behavior |
| [product/PARENT_PORTAL.md](product/PARENT_PORTAL.md) | Parent-code flows vs staff JWT accounts |

---

## 3. Contributing, frontend, testing, and quality

| Document | Purpose |
|----------|---------|
| [testing/TEST_COVERAGE_MATRIX_AND_RUN_REPORT_2026-05.md](testing/TEST_COVERAGE_MATRIX_AND_RUN_REPORT_2026-05.md) | Matrix + command log for the 2026-05 full-stack test remediation pass |
| [testing/README.md](testing/README.md) | **Structured execution tables:** CSV target metadata, append-only run history, and recent summary rows for incremental-test decisions |
| [testing/TEST_EXECUTION_LEDGER.md](testing/TEST_EXECUTION_LEDGER.md) | Stable human entry point for the CSV execution ledger |
| [testing/TEST_EXECUTION_SUMMARY.md](testing/TEST_EXECUTION_SUMMARY.md) | Stable human entry point for the CSV recent validation summary |
| [testing/DEVELOPMENT_AND_TESTING.md](testing/DEVELOPMENT_AND_TESTING.md) | Local workflow, pytest/Playwright layers, E2E dual gate |
| [testing/TEST_SUITE_MAP.md](testing/TEST_SUITE_MAP.md) | What lives where in `tests/` |
| [testing/TEST_EXECUTION_PITFALLS.md](testing/TEST_EXECUTION_PITFALLS.md) | **Large** — Windows/PowerShell, ports, Element Plus, SQLite vs PG |
| [testing/FULL_PLAYWRIGHT_E2E_RUNBOOK.md](testing/FULL_PLAYWRIGHT_E2E_RUNBOOK.md) | Full admin E2E environment contract |
| [frontend/NOTIFICATION_HEADER_AND_REALTIME_SYNC.md](frontend/NOTIFICATION_HEADER_AND_REALTIME_SYNC.md) | Header badge, sync API, sidebar navigation notes |
| [contributing/ENCODING_AND_MOJIBAKE_SAFETY.md](contributing/ENCODING_AND_MOJIBAKE_SAFETY.md) | UTF-8 / PowerShell display traps |
| [product/CONTENT_FORMAT_MARKDOWN_AND_PLAIN_TEXT.md](product/CONTENT_FORMAT_MARKDOWN_AND_PLAIN_TEXT.md) | Homework/submission `content_format` |
| [contributing/GIT_WORKFLOW.md](contributing/GIT_WORKFLOW.md) | Branch and contribution conventions |
| [frontend/HTTP_CLIENT_SLOW_RESPONSE_BUSY_HINT.md](frontend/HTTP_CLIENT_SLOW_RESPONSE_BUSY_HINT.md) | HTTP client UX hint behavior |
| [testing/TEST_REDUNDANCY_AUDIT.md](testing/TEST_REDUNDANCY_AUDIT.md) | Test merge/delete policy |

---

## 4. Documentation principles

- These files describe the **current implementation** in this repository.
- CourseEval treats **code as documentation** and **documentation as
  governance**: implementation usually wins when docs conflict with code, while
  durable rules and repeated workflows should be written into docs, scripts, or
  repo-local skills.
- Whenever a workflow becomes common, fragile, or repeatedly useful, create or
  update a repo-local skill as needed so future agents can execute it
  consistently; prefer adding a supporting script when the workflow can be
  automated.
- Keep skill overlap intentional and layered: use
  [../skills/repository-normalization/SKILL.md](../skills/repository-normalization/SKILL.md)
  as the top-level governance orchestrator, then route through
  docs/boundary/structure governance or the richer specialized skill. When two
  skills or scripts overlap, preserve the more precise and executable one as
  the source of truth.
- Close repository-normalization work in durable docs: classify accepted,
  active, and deferred boundaries in architecture/handoff/governance docs before
  treating local planning notes or warning lists as complete.
- If behavior changes in code, update these documents in the same change set.
- Contributors, including LLM agents, are expected to read the task-relevant documents before changing code, tests, structure, or deployment assets.
- The documentation set is part of the implementation surface, not optional commentary.
- For database-related tests and “zero-skip” full `pytest` claims, see the **full regression prerequisites** in [testing/DEVELOPMENT_AND_TESTING.md](testing/DEVELOPMENT_AND_TESTING.md).
- Large structured ledgers belong in CSV/JSON/YAML; Markdown should link to
  them and explain interpretation rules. The current test execution ledgers
  live under [testing/](testing/).
- The `docs/` root should contain only this hub README. Put every other
  document in a topic folder with its own `README.md`.
- For repository naming, package, service, and ops-template normalization
  checks, run `python ops/scripts/dev/check_repository_normalization.py`.

---

## 5. Mandatory reading by task

Use this section as an operational gate, not a suggestion.

### Before any repository-structure or path change

Read:

1. [architecture/REPOSITORY_STRUCTURE.md](architecture/REPOSITORY_STRUCTURE.md)
2. [architecture/SYSTEM_OVERVIEW.md](architecture/SYSTEM_OVERVIEW.md)
3. [architecture/BACKEND_PACKAGE_STRUCTURE.md](architecture/BACKEND_PACKAGE_STRUCTURE.md) when touching backend package layout

Why:

- this repository contains intentional compatibility layers
- some directories seen locally are runtime artifacts rather than source layout
- moving files without reading the structure contract can break tests, deploy scripts, or startup commands

### Before backend or feature work

Read:

1. [architecture/SYSTEM_OVERVIEW.md](architecture/SYSTEM_OVERVIEW.md)
2. [architecture/CORE_BUSINESS_FLOWS.md](architecture/CORE_BUSINESS_FLOWS.md)
3. the relevant product document such as [product/LLM_HOMEWORK_GUIDE.md](product/LLM_HOMEWORK_GUIDE.md) or [product/PARENT_PORTAL.md](product/PARENT_PORTAL.md)

Why:

- route shape, bootstrap behavior, and LLM flows are interdependent
- feature work can accidentally break quota, notification, enrollment, or startup assumptions outside the immediate edit area

### Before running tests or diagnosing failures

Read:

1. [testing/DEVELOPMENT_AND_TESTING.md](testing/DEVELOPMENT_AND_TESTING.md)
2. [contributing/ENCODING_AND_MOJIBAKE_SAFETY.md](contributing/ENCODING_AND_MOJIBAKE_SAFETY.md)
3. [testing/TEST_EXECUTION_PITFALLS.md](testing/TEST_EXECUTION_PITFALLS.md)
4. [architecture/TROUBLESHOOTING.md](architecture/TROUBLESHOOTING.md) for a short symptom index

Why:

- this repository has known Windows + PowerShell execution traps
- Playwright failures can come from port collisions, stale processes, or sandbox limits rather than product regressions

### Before deployment, environment, or bootstrap changes

Read:

1. [operations/DEPLOYMENT_AND_OPERATIONS.md](operations/DEPLOYMENT_AND_OPERATIONS.md)
2. [operations/ADMIN_BOOTSTRAP.md](operations/ADMIN_BOOTSTRAP.md)
3. [architecture/CONFIGURATION_REFERENCE.md](architecture/CONFIGURATION_REFERENCE.md)
4. [architecture/REPOSITORY_STRUCTURE.md](architecture/REPOSITORY_STRUCTURE.md)

Why:

- startup, service layout, and compatibility entrypoints are coupled
- deploy scripts may depend on current import and directory conventions

---

## 6. Suggested reading paths

### Product or engineering overview

1. [architecture/SYSTEM_OVERVIEW.md](architecture/SYSTEM_OVERVIEW.md)
2. [architecture/CORE_BUSINESS_FLOWS.md](architecture/CORE_BUSINESS_FLOWS.md)
3. [architecture/REPOSITORY_STRUCTURE.md](architecture/REPOSITORY_STRUCTURE.md)
4. [product/LLM_HOMEWORK_GUIDE.md](product/LLM_HOMEWORK_GUIDE.md)

### Local development

1. [testing/DEVELOPMENT_AND_TESTING.md](testing/DEVELOPMENT_AND_TESTING.md)
2. [contributing/ENCODING_AND_MOJIBAKE_SAFETY.md](contributing/ENCODING_AND_MOJIBAKE_SAFETY.md)
3. [testing/TEST_SUITE_MAP.md](testing/TEST_SUITE_MAP.md)
4. [testing/TEST_REDUNDANCY_AUDIT.md](testing/TEST_REDUNDANCY_AUDIT.md)
5. [testing/TEST_EXECUTION_PITFALLS.md](testing/TEST_EXECUTION_PITFALLS.md)
6. [architecture/MAINTAINER_AGENT_GUIDE.md](architecture/MAINTAINER_AGENT_GUIDE.md)

### Autonomous agent onboarding (Codex / Cursor / cloud agents)

1. [AGENTS.md](../AGENTS.md)
2. [agents/agent-playbook.md](agents/agent-playbook.md)
3. [reference/CODE_MAP_AND_ENTRYPOINTS.md](reference/CODE_MAP_AND_ENTRYPOINTS.md)
4. [governance/known-issues-and-risks.md](governance/known-issues-and-risks.md)
5. [architecture/CORE_BUSINESS_FLOWS.md](architecture/CORE_BUSINESS_FLOWS.md)

### Production deployment

1. [operations/DEPLOYMENT_AND_OPERATIONS.md](operations/DEPLOYMENT_AND_OPERATIONS.md)
2. [architecture/CONFIGURATION_REFERENCE.md](architecture/CONFIGURATION_REFERENCE.md)
3. [product/LLM_HOMEWORK_GUIDE.md](product/LLM_HOMEWORK_GUIDE.md)

### Parent-facing experience

1. [product/PARENT_PORTAL.md](product/PARENT_PORTAL.md)
2. [architecture/SYSTEM_OVERVIEW.md](architecture/SYSTEM_OVERVIEW.md)
