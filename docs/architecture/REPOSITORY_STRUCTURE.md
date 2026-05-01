# Repository Structure

## Purpose

This document defines the intended repository layout, the boundary rules for the top level, and the specific compatibility choices that still exist after the recent multi-application restructuring.

This file is intentionally detailed. It is meant to help both humans and LLM agents distinguish between:

- source code versus local runtime artifacts,
- repository-level entrypoints versus app-local files,
- intentional compatibility layers versus long-term architectural targets.

## High-Level Layout

```text
repo/
  app/                    root compatibility package for app.*
  apps/
    backend/
      app/                real FastAPI backend package
    web/
      admin/              admin SPA
      parent/             parent SPA
  docs/                   authoritative documentation tree
  ops/                    deployment, CI, nginx, systemd, helper scripts
  tests/                  pytest suites and Playwright specs
  README.md               public repository entrypoint
  LICENSE                 license text
  requirements.txt        Python dependency lock surface for current backend
  pytest.ini              repository-level pytest defaults
  conftest.py             repository-level pytest bootstrap for Windows temp handling
```

## Root-Level Boundary Contract

The repository root is intentionally restrictive.

Only these categories should normally remain at the top level:

- repository metadata and onboarding files,
- repository-wide test configuration,
- the compatibility `app/` package,
- main structural directories such as `apps/`, `docs/`, `ops/`, and `tests/`.

The root should not be used as a generic dumping ground for:

- environment-specific launcher scripts,
- app-specific helper files,
- deploy-only shell wrappers,
- one-off maintenance scripts,
- copied frontend build outputs,
- browser test artifacts,
- temporary database files.

## Why `app/` Still Exists At The Root

At first glance, having both `app/` and `apps/` looks redundant. In purely conceptual terms, it is redundant. In the current implementation, however, the root `app/` directory is a compatibility layer, not a second backend tree.

The real backend source code lives in:

- `apps/backend/app/`

The root package:

- `app/__init__.py`

does not contain business logic. It only redirects Python package resolution so that legacy imports such as:

- `from app.config import settings`
- `from app.main import app`
- `python -m uvicorn app.main:app`
- `python -m app.bootstrap`

continue to work.

This shim remains necessary because all of the following still depend on `app.*`:

- internal backend module imports,
- tests and test fixtures,
- systemd startup commands,
- deployment helper scripts,
- local development commands in docs and shell wrappers.

## Why The Root `app/` Package Was Not Removed Yet

Removing the shim immediately would require a broad import migration across:

- backend modules,
- pytest modules,
- helper scripts,
- deployment configuration,
- service entrypoints,
- operational documentation.

That is a legitimate future cleanup, but it is a larger semantic refactor than a structure-only cleanup. The current repository chooses a lower-risk intermediate state:

- keep one small, explicit compatibility package at the root,
- keep the real code only under `apps/backend/app/`,
- document that distinction clearly,
- prevent additional unrelated files from accumulating beside it.

## Why The Root `conftest.py` Remains At The Root

The repository-level `conftest.py` is not an accidental leftover. It exists to apply Windows-specific pytest safeguards before test discovery and temp-directory creation become unstable.

Its responsibilities include:

- handling Windows temp-path permission issues more safely,
- stabilizing pytest temp behavior inside this repository,
- affecting the whole repository test session rather than only one sub-tree.

Keeping that file at the root is correct because its scope is repository-wide, not app-local.

If it were moved into a narrower directory without redesigning how pytest is invoked, its effect could become partial or inconsistent.

## Where Convenience Launchers Belong

Windows launchers are convenience tooling, not repository-entry metadata. They now live in:

- `ops/scripts/windows/start-backend.bat`
- `ops/scripts/windows/start-admin-frontend.bat`
- `ops/scripts/windows/start-parent-frontend.bat`

This is intentional for three reasons:

1. These files are operational helpers, not source code.
2. They should not visually compete with repository-level files in the root.
3. Consolidating them reduces the chance of inconsistent launcher behavior across apps.

The launchers are ASCII-only on purpose. This avoids carrying PowerShell or console encoding damage into tracked files.

## Where Deployment And Operations Assets Belong

Deployment assets live under `ops/`:

- `ops/scripts/` for deploy and maintenance scripts,
- `ops/scripts/windows/` for Windows convenience wrappers,
- `ops/nginx/` for reverse-proxy templates,
- `ops/systemd/` for Linux service definitions,
- `ops/ci/` for CI workflow configuration.

This boundary matters because these files are not part of the runtime application package itself. They are deployment surface area and should remain grouped as such.

## Application Boundaries

### Backend

The backend application lives in:

- `apps/backend/app/`

This directory contains:

- FastAPI startup and router registration,
- SQLAlchemy models,
- authentication and permissions,
- bootstrap and seed behavior,
- LLM grading logic,
- course, roster, and homework coordination modules.

### Admin frontend

The admin SPA lives in:

- `apps/web/admin/`

This directory contains:

- Vite application code,
- frontend dependencies and lockfile,
- Playwright configuration,
- admin UI source.

Playwright test specs do not live here. They live in:

- `tests/e2e/web-admin/`

That split is deliberate: the app owns the Playwright runtime configuration, while the repository-level `tests/` tree owns test suites.

### Parent frontend

The parent SPA lives in:

- `apps/web/parent/`

Its structure parallels the admin frontend, but it remains a separate app because it has a different route base, UX surface, and deployment target.

## Test Boundaries

Tests live under `tests/` and are split by style and purpose:

- `tests/backend/` for focused backend regression modules grouped by domain,
- `tests/behavior/` for higher-level multi-actor or workflow behavior,
- `tests/e2e/web-admin/` for browser E2E coverage,
- `tests/fixtures/` for test assets,
- `tests/scenarios/` for reusable scenario builders and stress helpers,
- a repository-level `tests/conftest.py` for test environment defaults.

Thin compatibility re-export modules remain at the `tests/` root for shared helpers such as `tests.llm_scenario`, but the actual helper implementations now live under `tests/scenarios/`.

## Local Runtime Artifacts That May Appear But Are Not Source Layout

Developers may see directories such as:

- `frontend/`
- `uploads/`
- `test-results/`
- `.pytest_tmp/`
- `.pytest_tmpbasetemp/`
- `.pytest-db/`
- `.e2e-run/`

These are not part of the intended repository structure.

Typical reasons they appear:

- legacy local Node dependency caches from the pre-restructure layout,
- attachment storage for local development,
- Playwright reports or browser-run artifacts,
- pytest temporary directories on Windows,
- local SQLite or temp data created during testing.

They are operational side effects, not architectural source boundaries.

## Current Transitional Elements

The repository is cleaner than before, but still includes deliberate transitional elements:

- the root `app/` compatibility shim,
- backend imports still written against `app.*`,
- deployment and test commands still using `app.main:app` or `python -m app.bootstrap`.

These are acceptable as long as they remain:

- small,
- explicit,
- documented,
- non-duplicative.

They become a problem only if new real source code starts accumulating in the root compatibility package.

## Rules For Future Changes

When adding or moving files, prefer these rules:

1. If a file applies to the whole repository, keep it at the root only if it is truly repository-scoped.
2. If a file starts or operates an application, prefer `ops/scripts/` or an app-local subdirectory instead of the root.
3. If a file is deployment-only, keep it under `ops/`.
4. If a file is test-only, keep it under `tests/` unless pytest itself requires a repository-level location.
5. If a directory is a local artifact and not source, ignore it in git and do not document it as part of the architecture.
6. If a compatibility layer exists, keep it minimal and explain why it exists.

## Future Cleanup Opportunities

The main remaining long-term cleanup is import-path normalization.

That would involve:

- replacing `app.*` imports with a single explicit backend package strategy,
- updating tests and operational scripts accordingly,
- simplifying service entrypoints,
- removing the root compatibility package when every dependent surface has migrated.

That work should be done as a dedicated refactor with targeted regression coverage, not as an incidental side effect of unrelated feature work.
