# Backend Package Structure

## Purpose

This document explains how to navigate the backend package after the namespace migration to:

- `apps.backend.wailearning_backend`

It is intended for maintainers and LLM coding agents that need to answer two recurring questions:

1. Where should a backend change go?
2. Which layer should own a new piece of code?

For the repository-wide assessment of whether the backend package is still too flat, and for the recommended migration order, also read:

- [STRUCTURE_AUDIT_AND_MIGRATION_PLAN.md](STRUCTURE_AUDIT_AND_MIGRATION_PLAN.md)

## Canonical Package Root

The backend package root is:

- `apps/backend/wailearning_backend/`

The canonical Python import root is:

- `apps.backend.wailearning_backend`

Examples:

- `from apps.backend.wailearning_backend.core.config import settings`
- `from apps.backend.wailearning_backend.db.models import User`
- `from apps.backend.wailearning_backend.api.schemas import Token`
- `from apps.backend.wailearning_backend.api.routers import auth`

Do not use:

- `app.*`
- `wailearning_backend.*` without the `apps.backend` prefix
- ad hoc `sys.path` edits in normal application code

## Current Layer Model

The backend is organized into four practical layers plus explicit domain packages.

### Layer 1: process entrypoints

Files:

- `main.py`
- `bootstrap.py`

Responsibilities:

- compose the FastAPI application,
- register routers,
- coordinate startup lifecycle,
- run bootstrap and repair flows.

Rules:

- keep these files thin,
- avoid putting business rules directly here,
- avoid adding import-time side effects unless they are unavoidable and documented.

### Layer 2: HTTP API surface

Directory:

- `api/`

Subdirectories and files:

- `api/routers/`
- `api/schemas.py`

Responsibilities:

- request and response contracts,
- route wiring,
- parameter validation,
- translation between HTTP concerns and backend services.

Rules:

- routers may enforce authorization and orchestration,
- routers should avoid absorbing large business workflows,
- request and response DTOs belong here unless there is a strong reason otherwise.

### Layer 3: shared backend core

Directory:

- `core/`

Files:

- `core/config.py`
- `core/auth.py`
- `core/permissions.py`

Responsibilities:

- settings loading,
- token creation and current-user resolution,
- cross-domain permission helpers.

Rules:

- only put code here if it is genuinely cross-domain,
- do not turn `core/` into a new miscellaneous dumping ground,
- if logic is specific to homework, LLM, roster, or scores, it probably does not belong here.

### Layer 4: persistence primitives

Directory:

- `db/`

Files:

- `db/database.py`
- `db/models.py`

Responsibilities:

- SQLAlchemy engine and session setup,
- ORM base and shared DB dependency wiring,
- database entities and enums.

Rules:

- model definitions belong here,
- route-specific serialization does not,
- configuration parsing does not,
- app startup orchestration does not.

### Layer 5: extracted domain helpers

Directory:

- `domains/`

Current subpackages:

- `domains/courses/`
- `domains/roster/`
- `domains/scores/`
- `domains/seed/`
- `domains/llm/`
- `domains/homework/`

Responsibilities:

- hold business-domain helpers that were previously trapped inside giant modules,
- reduce router-to-router imports,
- reduce growth pressure on package-root monolith files.

Rules:

- use `domains/` for real business slices, not generic utilities,
- prefer one clear responsibility per domain module,
- if logic is still mostly HTTP orchestration, leave it in `api/`,
- if logic is still mostly persistence primitives, leave it in `db/`.

## Current Domain-Heavy Modules

The following package-root modules are still substantial and should be treated as candidates for further extraction or slimming:

- `llm_grading.py`
- `llm_discussion.py`
- `bootstrap.py`
- `attachments.py`
- `markdown_llm.py`

Interpretation:

- these modules are acceptable only where they still act as true orchestration or shared runtime boundaries
- they should not be treated as proof that flat package-root business modules are the long-term strategy
- new business logic should prefer extending `domains/` or `services/` rather than increasing root-module count

These files are acceptable for now, but contributors should avoid making them even broader unless the change is truly local and small.

The following extractions are already in place:

- attachment and archive parsing moved into `domains/llm/attachments.py`
- discussion UI prefix stripping moved into `domains/llm/discussion_ui.py`
- quota reservation and usage-accounting helpers moved into `domains/llm/quota.py`
- admin quota-policy helpers moved into `domains/llm/token_quota.py`
- endpoint-group routing moved into `domains/llm/routing.py`
- endpoint URL / response parsing helpers moved into `domains/llm/protocol.py`
- course access and enrollment logic moved into `domains/courses/access.py`
- homework row cleanup moved into `domains/homework/cleanup.py`
- homework appeal and notification helpers moved into `domains/homework/appeals.py` and `domains/homework/notifications.py`
- roster synchronization and reconciliation moved into `domains/roster/`
- score composition and score-appeal helpers moved into `domains/scores/`
- demo seeding moved into `domains/seed/demo.py`
- operation-log helpers moved into `services/logging.py`

That is the intended pattern for subsequent rounds: extract coherent vertical slices without inventing alternate import roots.

## Router Organization

The current route modules live in:

- `apps/backend/wailearning_backend/api/routers/`

Examples:

- `auth.py`
- `subjects.py`
- `students.py`
- `scores.py`
- `homework.py`
- `llm_settings.py`

Router modules should own:

- endpoint registration,
- endpoint-local validation,
- response shaping,
- orchestration of domain helpers.

Router modules should not become the only home of business rules. When a router grows because it owns nontrivial workflow logic, that is usually a signal to extract a domain-oriented helper module.

## How To Place New Backend Code

Use the following decision rules:

### Put code in `api/` when:

- it defines a request or response shape,
- it exists only because an HTTP endpoint needs it,
- it is route registration or endpoint orchestration.

### Put code in `core/` when:

- it is cross-domain,
- it is about authentication or permission primitives,
- it is configuration or settings parsing.

### Put code in `db/` when:

- it defines ORM models or database bootstrap primitives,
- it defines session or engine configuration,
- it is a persistence primitive used by many backend areas.

### Keep code at package root only when:

- it is a process entrypoint,
- it coordinates several domains and does not yet fit one current layer,
- it is a shared runtime adapter whose natural home is still under review,
- or it is a package entrypoint.

### Do not add code to a new random bucket when:

- the real issue is that a domain subpackage should exist.

If a change is large enough to justify a new subpackage, create or extend a domain-oriented package with a clear name such as:

- `domains/homework/`
- `domains/llm/`
- `domains/roster/`
- `domains/courses/`
- `domains/scores/`
- `domains/seed/`
- `services/`

Do not create vague buckets such as:

- `misc/`
- `helpers/`
- `common2/`
- `temp/`

## Recommended Next Domain Extractions

The next worthwhile structural reductions are:

1. `llm_grading.py`
2. `api/routers/homework.py`
3. `api/routers/subjects.py`
4. `api/routers/scores.py`
5. `bootstrap.py`

The likely extraction shape is:

```text
apps/backend/wailearning_backend/
  domains/
    llm/
      worker.py
      routing.py
      quota.py
      grading.py
    homework/
      service.py
      appeals.py
      notifications.py
    roster/
      sync.py
      reconciliation.py
    scores/
      composition.py
      appeals.py
    seed/
      demo.py
  services/
    logging.py
```

Most of those directories now exist. The remaining work is to keep reducing the few heavy package-root orchestration modules without re-accumulating structural debt at the root.

## Import Rules For Future Refactors

When moving backend files again:

1. Preserve the canonical import root `apps.backend.wailearning_backend`.
2. Prefer a single explicit edit set over compatibility shims.
3. Update tests, docs, ops scripts, and Playwright config in the same change set.
4. Avoid partial namespace migrations that leave two valid import styles in circulation.

## Operational Consequences

Because the backend package now uses its real namespace everywhere, the following operational commands are authoritative:

- `python -m uvicorn apps.backend.wailearning_backend.main:app --host 127.0.0.1 --port 8001 --reload`
- `python -m apps.backend.wailearning_backend.bootstrap`
- `gunicorn apps.backend.wailearning_backend.main:app`

If future refactors move `main.py` or `bootstrap.py`, update:

- `ops/systemd/ddclass-backend.service`
- `ops/scripts/windows/start-backend.bat`
- `apps/web/admin/playwright.config.cjs`
- developer docs and README examples

in the same change set.
