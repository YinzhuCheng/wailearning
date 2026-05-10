---
name: permission-audit
description: Use this when changing or reviewing CourseEval authorization, role boundaries, course access, subject-scoped teacher routes, parent-code access, homework/file/notification permissions, or security-sensitive backend/API behavior.
---

# Permission Audit

## Purpose

Keep authorization enforced in backend code, not only hidden in frontend UI.
Preserve CourseEval's current role and object-level access contracts.

## Workflow

1. Read `docs/reference/PERMISSIONS_AND_SECURITY_BOUNDARIES.md`,
   `docs/architecture/CORE_BUSINESS_FLOWS.md`, and feature-specific docs.
2. Trace the request through router dependency, current-user resolution,
   permission helper, domain helper, and query filter.
3. For explicit `subject_id` routes, validate course access with
   `ensure_course_access_http(...)` before applying class-only filters.
4. For no-subject class-wide routes, class visibility checks may be the primary
   gate.
5. Confirm students resolve through `users.student_id`; do not reintroduce
   username/student-number guessing as normal behavior.
6. Add or update tests that prove unauthorized API calls fail at the backend.
7. Update permission docs when the contract changes.

## Commands

```powershell
rg -n "ensure_course_access_http|get_accessible_class_ids|get_accessible_courses_query|UserRole|parent" apps/backend/courseeval_backend tests
python ops/scripts/dev/select_validation_targets.py --worktree
python ops/scripts/dev/run_validation_target.py security.api_regression --timeout-seconds 120
```

## Guardrails

- Frontend hiding is not authorization.
- Do not restore `Subject.class_id` as the effective fallback for required
  course visibility or auto-enrollment.
- Do not weaken `/api/e2e/dev/*` gates.
- Treat parent-code flows separately from staff/student JWT flows.
- Escalate to broader validation for auth helpers, schema, or shared course
  access changes.

## Related Files

- `docs/reference/PERMISSIONS_AND_SECURITY_BOUNDARIES.md`
- `apps/backend/courseeval_backend/core/permissions.py`
- `apps/backend/courseeval_backend/domains/courses/access.py`
- `apps/backend/courseeval_backend/api/routers/`
- `tests/security/test_security_regression.py`
