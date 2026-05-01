# Documentation Hub

This directory is the authoritative documentation home for the repository. The root [`README.md`](../README.md) is the public entry point; everything else lives here.

## Read This First

- [Repository Structure](architecture/REPOSITORY_STRUCTURE.md)
- [System Overview](architecture/SYSTEM_OVERVIEW.md)
- [LLM and Homework Guide](product/LLM_HOMEWORK_GUIDE.md)
- [Development and Testing](development/DEVELOPMENT_AND_TESTING.md)
- [Test Suite Map](development/TEST_SUITE_MAP.md)
- [Test Execution Pitfalls](development/TEST_EXECUTION_PITFALLS.md)
- [Deployment and Operations](operations/DEPLOYMENT_AND_OPERATIONS.md)
- [Parent Portal](product/PARENT_PORTAL.md)
- [Git Workflow](development/GIT_WORKFLOW.md)
- [Admin Bootstrap and Demo Seed](operations/ADMIN_BOOTSTRAP.md)
- [Test-Inferred Risks And Follow-Ups](architecture/TEST_INFERRED_RISKS_AND_FOLLOWUPS.md)

## Documentation Principles

- These files describe the current implementation in this repository.
- Historical one-off notes and scattered local readmes were consolidated here to reduce drift.
- If behavior changes in code, update these documents in the same change set.
- Contributors, including LLM agents, are expected to read the task-relevant documents before changing code, tests, structure, or deployment assets.
- The documentation set is part of the implementation surface, not optional commentary.

## Mandatory Reading By Task

Use this section as an operational gate, not a suggestion.

### Before any repository-structure or path change

Read:

1. [Repository Structure](architecture/REPOSITORY_STRUCTURE.md)
2. [System Overview](architecture/SYSTEM_OVERVIEW.md)

Why:

- this repository contains intentional compatibility layers
- some directories seen locally are runtime artifacts rather than source layout
- moving files without reading the structure contract can break tests, deploy scripts, or startup commands

### Before backend or feature work

Read:

1. [System Overview](architecture/SYSTEM_OVERVIEW.md)
2. the relevant product document such as [LLM and Homework Guide](product/LLM_HOMEWORK_GUIDE.md) or [Parent Portal](product/PARENT_PORTAL.md)
3. [Test-Inferred Risks And Follow-Ups](architecture/TEST_INFERRED_RISKS_AND_FOLLOWUPS.md) when working near fragile areas

Why:

- route shape, bootstrap behavior, and LLM flows are interdependent
- feature work can accidentally break quota, notification, enrollment, or startup assumptions outside the immediate edit area

### Before running tests or diagnosing failures

Read:

1. [Development and Testing](development/DEVELOPMENT_AND_TESTING.md)
2. [Test Execution Pitfalls](development/TEST_EXECUTION_PITFALLS.md)

Why:

- this repository has known Windows + PowerShell execution traps
- Playwright failures can come from port collisions, stale processes, blocked PowerShell shims, or sandbox limits rather than product regressions
- pytest startup issues can originate from temp-path behavior before application code even runs

### Before deployment, environment, or bootstrap changes

Read:

1. [Deployment and Operations](operations/DEPLOYMENT_AND_OPERATIONS.md)
2. [Admin Bootstrap and Demo Seed](operations/ADMIN_BOOTSTRAP.md)
3. [Repository Structure](architecture/REPOSITORY_STRUCTURE.md)

Why:

- startup, service layout, and compatibility entrypoints are coupled
- deploy scripts and service files may still depend on current import and directory conventions

## Suggested Reading Paths

### Product or engineering overview

1. [System Overview](architecture/SYSTEM_OVERVIEW.md)
2. [Repository Structure](architecture/REPOSITORY_STRUCTURE.md)
3. [LLM and Homework Guide](product/LLM_HOMEWORK_GUIDE.md)
4. [Test-Inferred Risks And Follow-Ups](architecture/TEST_INFERRED_RISKS_AND_FOLLOWUPS.md)

### Local development

1. [Development and Testing](development/DEVELOPMENT_AND_TESTING.md)
2. [Test Suite Map](development/TEST_SUITE_MAP.md)
3. [Repository Structure](architecture/REPOSITORY_STRUCTURE.md)
4. [Admin Bootstrap and Demo Seed](operations/ADMIN_BOOTSTRAP.md)
5. [Test Execution Pitfalls](development/TEST_EXECUTION_PITFALLS.md)

### Production deployment

1. [Deployment and Operations](operations/DEPLOYMENT_AND_OPERATIONS.md)
2. [LLM and Homework Guide](product/LLM_HOMEWORK_GUIDE.md)

### Parent-facing experience

1. [Parent Portal](product/PARENT_PORTAL.md)
2. [System Overview](architecture/SYSTEM_OVERVIEW.md)
