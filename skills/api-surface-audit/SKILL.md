---
name: api-surface-audit
description: Use this when changing CourseEval FastAPI routers, route prefixes, frontend API clients, OpenAPI/API documentation, parent-code endpoints, E2E dev API routes, or API regression tests.
---

# API Surface Audit

## Purpose

Keep CourseEval's backend routers, frontend API clients, docs, and validation
targets aligned. This skill is for API contract changes; it does not replace a
full OpenAPI export.

## When to Use

Use this before changing:

- `apps/backend/courseeval_backend/api/routers/*.py`
- `apps/backend/courseeval_backend/main.py`
- `apps/backend/courseeval_backend/api/schemas.py`
- `apps/web/admin/src/api/index.js`
- `apps/web/parent/src/api/index.js`
- API route docs, parent-code docs, E2E dev API docs, or API regression tests

## Inputs

- Changed router/client/schema paths.
- Intended route family, HTTP method, request/query/body shape, and response
  model.
- Affected roles: admin, teacher, class teacher, student, parent-code caller, or
  E2E seed client.

## Workflow

1. Read `docs/reference/CODE_MAP_AND_ENTRYPOINTS.md`,
   `docs/reference/PERMISSIONS_AND_SECURITY_BOUNDARIES.md`, and the affected
   feature doc.
2. Open the backend router and `api/schemas.py` before trusting frontend helper
   names or older docs.
3. Confirm route prefix, method, query-vs-body shape, response model, and
   permission dependency in the router.
4. If the admin or parent SPA calls the route, update the matching API helper in
   the same change set.
5. If route semantics changed, update docs and selector targets together.
6. Prefer pytest/API regression for contract changes; reserve Playwright for
   browser routing, visibility, or multi-tab behavior.

## Commands

```powershell
python ops/scripts/dev/check_api_surface_governance.py
python ops/scripts/dev/select_validation_targets.py --worktree
python ops/scripts/dev/run_validation_target.py static.api_surface_governance --timeout-seconds 120
python ops/scripts/dev/run_validation_target.py security.api_regression --timeout-seconds 120
```

## Checks

- `check_api_surface_governance.py` passes.
- Changed route families are represented in selector targets or explicitly
  escalated to a broader target.
- Frontend helper URLs do not invent singular/plural paths that routers do not
  expose.
- Authorization-sensitive changes have backend tests, not only hidden UI
  buttons.

## Failure Handling

- If the static guardrail fails, fix the router/client/doc anchor before
  claiming API surface alignment.
- If the right API target is missing, add a selector rule or document why broad
  validation is required.
- If OpenAPI export is needed but not implemented, record that as a known gap;
  do not hand-write a pretend complete API reference.

## Related Files

- `apps/backend/courseeval_backend/main.py`
- `apps/backend/courseeval_backend/api/routers/`
- `apps/backend/courseeval_backend/api/schemas.py`
- `apps/web/admin/src/api/index.js`
- `apps/web/parent/src/api/index.js`
- `docs/reference/CODE_MAP_AND_ENTRYPOINTS.md`
- `docs/reference/PERMISSIONS_AND_SECURITY_BOUNDARIES.md`
- `ops/scripts/dev/check_api_surface_governance.py`
- `tests/TEST_SELECTION_TARGETS.json`
