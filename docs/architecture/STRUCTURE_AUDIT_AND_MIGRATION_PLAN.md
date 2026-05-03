# Structure Audit And Migration Plan

## Purpose

This document records the current repository-structure assessment for the May 2026 branch state and the migration decisions already applied in this branch.

It is intentionally written for maintainers and LLM coding agents that need to answer these questions without improvising:

1. Is the current tree catastrophically wrong, merely transitional, or already close to target shape?
2. Which structural concerns are repository-level versus backend-package-local?
3. What had to be documented and cleaned before large file moves occurred?
4. Which risks must be expected when imports or app boundaries move?

This branch has already executed the first large internal backend cleanup pass. The governing strategy remains:

- clarify boundaries first,
- tighten repository-level contracts second,
- extract domains behind the same import root,
- and avoid changing the repository-visible import contract unless strictly necessary.

## Current repository-level labels

The current tree is best described by the following labels.

### Repository-level pattern labels

- **Good / explicit multi-app monorepo shape**
  - `apps/`, `docs/`, `ops/`, `tests/`, and `tools/` are clearly separated.
  - The root does not currently contain ad hoc launchers, legacy compatibility packages, copied frontend output, or app-local scripts.
  - The two frontends are separated by deployment surface and user journey rather than being mixed into one UI tree.

- **Neutral / transitional explicit-import monorepo**
  - The canonical Python import root `apps.backend.wailearning_backend` is already documented and consistently used.
  - This is structurally clearer than a short alias plus shim, but it still carries migration cost because every ops and test surface depends on the long path.

- **Transitional backend-package flattening**
  - The backend package now has meaningful subpackages: `api/`, `core/`, `db/`, `domains/`, and `services/`.
  - A large first-pass de-flattening has already moved course, roster, score, seed, homework-support, and part of the LLM support logic into explicit subpackages.
  - The remaining issue is not broad flattening everywhere; it is a few still-heavy orchestration modules.

- **Root-level contract discipline mostly achieved**
  - Root files are almost entirely repository-scoped contract files: `README.md`, `requirements.txt`, `pytest.ini`, `conftest.py`, `.gitignore`, `.gitattributes`, `.editorconfig`, and deployment env template.
  - `conftest.py` is intentionally repository-scoped rather than app-local.
  - `requirements.txt` still reflects a repo-root backend dependency contract instead of an app-local Python package manifest; that is acceptable for now but should stay documented as intentional.

### Repository-level anti-pattern labels

- **Backend root-module concentration**
  - `apps/backend/wailearning_backend/` still contains many large domain modules beside the subpackages that are supposed to absorb them.
  - The clearest examples are now `llm_grading.py` (~2128 lines), `bootstrap.py` (~965 lines), and `llm_discussion.py` (~516 lines).

- **Entry-point dependency fan-out**
  - `main.py`, Playwright bootstrapping, `systemd`, Windows launchers, tests, and ops scripts all depend on the same explicit backend entrypoint path.
  - This is manageable, but it means future import-root or entrypoint moves are operationally expensive.

## Current conclusions by audit question

### 1. Does directory naming match repository scale and shape?

Mostly yes.

- `apps/` is justified because the repository contains:
  - one FastAPI backend,
  - one admin SPA,
  - one parent SPA.
- `docs/`, `ops/`, `tests/`, and `tools/` are appropriate at this size and keep non-runtime concerns out of app code.
- `apps/web/admin` and `apps/web/parent` are correctly separate because the deployment base path, runtime role model, and UX surface are different.

Where naming and scale still drift:

- `wailearning_backend/` is no longer broadly too flat, but a few package-root modules are still too large for a finished architecture.
- the next architectural work is now concentrated refinement, not first-principles tree invention.

### 2. Is the Python import root and app boundary documented?

Yes, and materially better than in many repositories.

The canonical import root `apps.backend.wailearning_backend` is documented in:

- `README.md`
- `docs/architecture/REPOSITORY_STRUCTURE.md`
- `docs/architecture/BACKEND_PACKAGE_STRUCTURE.md`
- `docs/architecture/SYSTEM_OVERVIEW.md`
- `docs/development/DEVELOPMENT_AND_TESTING.md`

It is also reflected in real execution surfaces:

- `ops/systemd/ddclass-backend.service`
- `ops/scripts/windows/start-backend.bat`
- `apps/web/admin/playwright.config.cjs`
- tests under `tests/`

This is a **good current-state property** and should not be destabilized casually.

### 3. Does the backend package still mix flat-root modules and subpackages without one unified strategy?

Not in the same way as before.

The largest inconsistency has already been reduced.

Current backend shape:

```text
apps/backend/wailearning_backend/
  main.py
  bootstrap.py
  attachments.py
  llm_grading.py
  llm_discussion.py
  markdown_llm.py
  semester_utils.py
  services/
  api/
  core/
  db/
  domains/
```

Interpretation:

- `api/`, `core/`, and `db/` are coherent foundational layers.
- `domains/` is now the real home for most extracted business logic.
- `services/` now exists as a narrow home for cross-cutting operational helpers.
- the package root now mostly holds:
  - process entrypoints,
  - shared runtime helpers,
  - and a smaller set of still-heavy orchestration modules.

### 4. Does the repository root mostly hold global contract files only?

Yes.

Current root files are mostly appropriate:

- `.editorconfig`
- `.env.production`
- `.gitattributes`
- `.gitignore`
- `conftest.py`
- `LICENSE`
- `pytest.ini`
- `README.md`
- `requirements.txt`

This is close to the desired root shape.

Interpretation:

- `.env.production` is acceptable at root as a deployment template and repository-wide contract example.
- `requirements.txt` is acceptable at root while backend packaging remains repo-root-oriented.
- `conftest.py` is intentionally repo-scoped because it stabilizes pytest behavior before test discovery.

The root is therefore **not** the main problem area right now.

## Recommended target tree

The target should remain conservative at the top level and become more explicit inside the backend package.

```text
repo/
  apps/
    backend/
      wailearning_backend/
        __init__.py
        main.py
        bootstrap.py
        api/
          __init__.py
          schemas.py
          routers/
            __init__.py
            auth.py
            classes.py
            discussions.py
            homework.py
            llm_settings.py
            materials.py
            notifications.py
            parent.py
            points.py
            scores.py
            students.py
            subjects.py
            users.py
        core/
          __init__.py
          auth.py
          config.py
          permissions.py
        db/
          __init__.py
          database.py
          models.py
        domains/
          llm/
            __init__.py
            attachments.py
            errors.py
            grading.py
            protocol.py
            quota.py
            routing.py
            worker.py
          homework/
            __init__.py
            appeals.py
            cleanup.py
            notifications.py
            service.py
          roster/
            __init__.py
            reconciliation.py
            sync.py
          courses/
            __init__.py
            access.py
            enrollments.py
            schedule.py
          scores/
            __init__.py
            composition.py
            appeals.py
          seed/
            __init__.py
            demo.py
        services/
          __init__.py
          logging.py
    web/
      admin/
      parent/
  docs/
    architecture/
      REPOSITORY_STRUCTURE.md
      BACKEND_PACKAGE_STRUCTURE.md
      STRUCTURE_AUDIT_AND_MIGRATION_PLAN.md
  ops/
  tests/
  tools/
  README.md
  requirements.txt
  pytest.ini
  conftest.py
```

Important interpretation of the target tree:

- this is a **directional target**, not a one-commit rename plan
- package-root flattening should decrease over time
- top-level root discipline should remain almost unchanged
- no short import alias or root compatibility package should be reintroduced

## Migration order that was applied

### Phase 1: document and freeze boundaries

Done first:

- keep `README.md`, `REPOSITORY_STRUCTURE.md`, and `BACKEND_PACKAGE_STRUCTURE.md` aligned
- document which backend package-root files are transitional and which are intended long-term entrypoints
- document the rule that new business logic should prefer `domains/<slice>/` instead of new package-root files
- tighten `.gitignore` only for repository-level runtime artifacts, not for source-structure shortcuts

Do not do first:

- large path renames,
- import-root shortening,
- compatibility packages,
- or sweeping directory moves.

Result:

- contributors can tell where new code belongs before any physical migration continues

### Phase 2: tools and root-directory hygiene

Done second:

- keep the root limited to repository-scoped files
- move any future one-off scripts under `ops/scripts/` or `tools/` immediately instead of letting root sprawl return
- keep local runtime outputs out of source trees via `.gitignore`
- make sure CI, Playwright config, Windows launchers, and systemd continue to point at the same canonical entrypoints while domain extraction happens internally

Applied examples in this phase:

- `.gitignore` refinements
- docs-hub updates
- script relocation that does not change the backend import root

### Phase 3: domain extraction inside the backend package

Applied after the documentation contract was stable:

- move `homework_appeals.py` and `homework_notifications.py` under `domains/homework/`
- move `student_user_sync.py` and `student_user_roster.py` under `domains/roster/`
- move `course_access.py` under `domains/courses/`
- move `score_composition.py` and `score_grade_appeals.py` under `domains/scores/`
- move `demo_course_seed.py` under `domains/seed/`
- move `llm_group_routing.py`, `llm_token_quota.py`, and `discussion_llm_ui.py` under `domains/llm/`
- move `services.py` under `services/logging.py`

Constraint:

- preserve `apps.backend.wailearning_backend` as the import root during this entire phase

### Phase 4: import-contract changes deferred

Still deferred, and only justified if the repository eventually needs it:

- any entrypoint rename
- any import-path contract change that affects `uvicorn`, `gunicorn`, Playwright, CI, `systemd`, Windows scripts, or tests

Default recommendation:

- avoid import-root contract changes unless there is a very strong reason
- internal file movement is much cheaper than changing the package root visible to every tool surface

## Risk list

### Import risk

- every move inside `apps/backend/wailearning_backend/` can affect:
  - route modules,
  - tests,
  - bootstrap helpers,
  - seed helpers,
  - ops scripts using `python -m ...`
- the repository is already healthy on the import-root question; introducing a second valid style would be a regression
- circular-import risk is now concentrated around:
  - `llm_grading.py`
  - `llm_discussion.py`
  - `bootstrap.py`
  - router-to-router helper imports

### CI risk

- current CI runs `python3 -m pytest -q` from repo root
- moving files without updating imports or test bootstrap will fail immediately
- if backend dependencies are ever moved out of repo-root `requirements.txt`, CI must be changed in the same commit

### E2E risk

- Playwright bootstraps the backend through `apps.backend.wailearning_backend.main:app`
- it also assumes the repo-root shape when calculating `repoRoot`
- any entrypoint move or `apps/` tree shift will break:
  - managed `webServer`
  - local E2E startup
  - seed/reset API assumptions

### Dual-frontend risk

- the admin and parent SPAs are separate apps with separate Vite projects, lockfiles, ports, and deployment destinations
- structural cleanup must not accidentally:
  - merge their runtime config,
  - move one app's tooling into the other app,
  - or document them as one deployment surface
- ops and docs must continue to reflect:
  - admin served at `/`
  - parent portal served at `/parent/`

### Ops and deployment risk

- `systemd`, nginx, deploy scripts, Windows launchers, and Playwright all encode assumptions about current entrypoints and app layout
- domain extraction inside the backend package is relatively cheap
- moving process entrypoints or changing package root is not cheap

## Immediate recommendation after this pass

The repository should be treated as:

- **top-level shape: acceptable and worth preserving**
- **backend internal shape: largely re-layered, with a smaller set of heavy orchestration modules left**
- **import root: stable contract, do not reopen casually**
- **root directory discipline: already close to target, keep it strict**

The next useful work is therefore not another broad move. It is:

1. maintain the explicit boundary docs,
2. prevent new root or package-root sprawl,
3. continue breaking down `llm_grading.py`, `llm_discussion.py`, and `bootstrap.py`,
4. postpone any import-contract change until there is a proven need.
