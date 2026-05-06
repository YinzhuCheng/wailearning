# Documentation Hub

This directory is the authoritative documentation home for the repository. The root [`README.md`](../README.md) is the public entry point; everything else lives here.

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
| [architecture/BACKEND_PACKAGE_STRUCTURE.md](architecture/BACKEND_PACKAGE_STRUCTURE.md) | Layer model inside `wailearning_backend` |
| [architecture/STRUCTURE_AUDIT_AND_MIGRATION_PLAN.md](architecture/STRUCTURE_AUDIT_AND_MIGRATION_PLAN.md) | Structural migration rationale |
| [operations/DEPLOYMENT_AND_OPERATIONS.md](operations/DEPLOYMENT_AND_OPERATIONS.md) | Production layout, nginx, systemd, env templates |
| [operations/ADMIN_BOOTSTRAP.md](operations/ADMIN_BOOTSTRAP.md) | Startup ordering, seed behavior |

---

## 2. Product features

| Document | Purpose |
|----------|---------|
| [product/LLM_HOMEWORK_GUIDE.md](product/LLM_HOMEWORK_GUIDE.md) | LLM entities, quotas, async worker behavior |
| [product/PARENT_PORTAL.md](product/PARENT_PORTAL.md) | Parent-code flows vs staff JWT accounts |

---

## 3. Development, testing, and quality

| Document | Purpose |
|----------|---------|
| [development/DEVELOPMENT_AND_TESTING.md](development/DEVELOPMENT_AND_TESTING.md) | Local workflow, pytest/Playwright layers, E2E dual gate |
| [development/TEST_SUITE_MAP.md](development/TEST_SUITE_MAP.md) | What lives where in `tests/` |
| [development/TEST_EXECUTION_PITFALLS.md](development/TEST_EXECUTION_PITFALLS.md) | **Large** — Windows/PowerShell, ports, Element Plus, SQLite vs PG |
| [development/FULL_PLAYWRIGHT_E2E_RUNBOOK.md](development/FULL_PLAYWRIGHT_E2E_RUNBOOK.md) | Full admin E2E environment contract |
| [development/NOTIFICATION_HEADER_AND_REALTIME_SYNC.md](development/NOTIFICATION_HEADER_AND_REALTIME_SYNC.md) | Header badge, sync API, sidebar navigation notes |
| [development/ENCODING_AND_MOJIBAKE_SAFETY.md](development/ENCODING_AND_MOJIBAKE_SAFETY.md) | UTF-8 / PowerShell display traps |
| [development/CONTENT_FORMAT_MARKDOWN_AND_PLAIN_TEXT.md](development/CONTENT_FORMAT_MARKDOWN_AND_PLAIN_TEXT.md) | Homework/submission `content_format` |
| [development/GIT_WORKFLOW.md](development/GIT_WORKFLOW.md) | Branch and contribution conventions |
| [development/HISTORICAL_CODE_CLEANUP.md](development/HISTORICAL_CODE_CLEANUP.md) | When legacy-looking code is still required |
| [development/UI_UX_AUDIT_AND_RESPONSIVE_REPAIR.md](development/UI_UX_AUDIT_AND_RESPONSIVE_REPAIR.md) | Admin SPA responsive / UX notes |
| [development/HTTP_CLIENT_SLOW_RESPONSE_BUSY_HINT.md](development/HTTP_CLIENT_SLOW_RESPONSE_BUSY_HINT.md) | HTTP client UX hint behavior |
| [development/TEST_REDUNDANCY_AUDIT.md](development/TEST_REDUNDANCY_AUDIT.md) | Test merge/delete policy |
| [architecture/TEST_INFERRED_RISKS_AND_FOLLOWUPS.md](architecture/TEST_INFERRED_RISKS_AND_FOLLOWUPS.md) | Risks inferred from coverage |

---

## 4. Documentation principles

- These files describe the **current implementation** in this repository.
- If behavior changes in code, update these documents in the same change set.
- Contributors, including LLM agents, are expected to read the task-relevant documents before changing code, tests, structure, or deployment assets.
- The documentation set is part of the implementation surface, not optional commentary.
- For database-related tests and “zero-skip” full `pytest` claims, see the **full regression prerequisites** in [development/DEVELOPMENT_AND_TESTING.md](development/DEVELOPMENT_AND_TESTING.md).

---

## 5. Mandatory reading by task

Use this section as an operational gate, not a suggestion.

### Before any repository-structure or path change

Read:

1. [architecture/REPOSITORY_STRUCTURE.md](architecture/REPOSITORY_STRUCTURE.md)
2. [architecture/SYSTEM_OVERVIEW.md](architecture/SYSTEM_OVERVIEW.md)
3. [architecture/STRUCTURE_AUDIT_AND_MIGRATION_PLAN.md](architecture/STRUCTURE_AUDIT_AND_MIGRATION_PLAN.md)

Why:

- this repository contains intentional compatibility layers
- some directories seen locally are runtime artifacts rather than source layout
- moving files without reading the structure contract can break tests, deploy scripts, or startup commands

### Before backend or feature work

Read:

1. [architecture/SYSTEM_OVERVIEW.md](architecture/SYSTEM_OVERVIEW.md)
2. [architecture/CORE_BUSINESS_FLOWS.md](architecture/CORE_BUSINESS_FLOWS.md)
3. the relevant product document such as [product/LLM_HOMEWORK_GUIDE.md](product/LLM_HOMEWORK_GUIDE.md) or [product/PARENT_PORTAL.md](product/PARENT_PORTAL.md)
4. [architecture/TEST_INFERRED_RISKS_AND_FOLLOWUPS.md](architecture/TEST_INFERRED_RISKS_AND_FOLLOWUPS.md) when working near fragile areas

Why:

- route shape, bootstrap behavior, and LLM flows are interdependent
- feature work can accidentally break quota, notification, enrollment, or startup assumptions outside the immediate edit area

### Before running tests or diagnosing failures

Read:

1. [development/DEVELOPMENT_AND_TESTING.md](development/DEVELOPMENT_AND_TESTING.md)
2. [development/ENCODING_AND_MOJIBAKE_SAFETY.md](development/ENCODING_AND_MOJIBAKE_SAFETY.md)
3. [development/TEST_EXECUTION_PITFALLS.md](development/TEST_EXECUTION_PITFALLS.md)
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
5. [architecture/TEST_INFERRED_RISKS_AND_FOLLOWUPS.md](architecture/TEST_INFERRED_RISKS_AND_FOLLOWUPS.md)

### Local development

1. [development/DEVELOPMENT_AND_TESTING.md](development/DEVELOPMENT_AND_TESTING.md)
2. [development/ENCODING_AND_MOJIBAKE_SAFETY.md](development/ENCODING_AND_MOJIBAKE_SAFETY.md)
3. [development/TEST_SUITE_MAP.md](development/TEST_SUITE_MAP.md)
4. [development/TEST_REDUNDANCY_AUDIT.md](development/TEST_REDUNDANCY_AUDIT.md)
5. [development/TEST_EXECUTION_PITFALLS.md](development/TEST_EXECUTION_PITFALLS.md)
6. [architecture/MAINTAINER_AGENT_GUIDE.md](architecture/MAINTAINER_AGENT_GUIDE.md)

### Production deployment

1. [operations/DEPLOYMENT_AND_OPERATIONS.md](operations/DEPLOYMENT_AND_OPERATIONS.md)
2. [architecture/CONFIGURATION_REFERENCE.md](architecture/CONFIGURATION_REFERENCE.md)
3. [product/LLM_HOMEWORK_GUIDE.md](product/LLM_HOMEWORK_GUIDE.md)

### Parent-facing experience

1. [product/PARENT_PORTAL.md](product/PARENT_PORTAL.md)
2. [architecture/SYSTEM_OVERVIEW.md](architecture/SYSTEM_OVERVIEW.md)
