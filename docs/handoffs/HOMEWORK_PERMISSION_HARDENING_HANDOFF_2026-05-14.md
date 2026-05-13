# Homework Permission Hardening Handoff

## Scope

This handoff captures the multi-round homework/attendance/notification security
hardening work on branch `cursor/repository-normalization-schema-notifications`
through commit `17fd7dc`.

The recent rounds focused on a repeated repository risk:

- route-local logic started supporting multi-class / linked-class course
  behavior;
- shared helpers or neighboring teacher endpoints still assumed a single
  `Subject.class_id` anchor or treated course visibility as management
  authority.

## Branch State

- Branch: `cursor/repository-normalization-schema-notifications`
- Recent local commits:
  - `17fd7dc fix: gate batch homework policy updates by ownership`
  - `7c99055 fix: restrict homework submission management to instructors`
  - `6c267aa fix: honor linked-class homework access invariants`
  - `3fd78dd fix: require course ownership for homework mutation`
  - `f5540e2 fix: support linked-class attendance and homework writes`
  - `30c686f fix: allow linked-class course notifications`

## What Was Hardened

### 1. Linked-class course notification writes

`apps/backend/courseeval_backend/api/routers/notifications.py`

- Fixed course notification create/update scope checks so a course teacher may
  bind a course notification to any administrative class linked through
  `subject_class_links`, not only `Subject.class_id`.

Security tests added:

- `hard123`
- `hard124`

### 2. Linked-class attendance and homework writes

`apps/backend/courseeval_backend/api/routers/attendance.py`

- Fixed single-write attendance create.
- Fixed attendance batch create.
- Fixed class-batch attendance create.

`apps/backend/courseeval_backend/api/routers/homework.py`

- Fixed linked-class homework create.

Security tests added:

- `hard125`
- `hard126`
- `hard127`

### 3. Homework mutation ownership

`apps/backend/courseeval_backend/api/routers/homework.py`

- Fixed course homework update so class-teacher visibility no longer implies
  mutation authority.
- Fixed course homework delete so class-teacher visibility no longer implies
  mutation authority.

Security tests added:

- `hard128`
- `hard129`

### 4. Homework read invariants for linked-class rows

`apps/backend/courseeval_backend/api/routers/homework.py`

- Fixed `_ensure_homework_access(...)` so linked-class course homework created
  on a secondary administrative class is no longer rejected as a fake data
  integrity error during teacher/student reads.

Security test added:

- `hard130`

### 5. Homework submission-management ownership

`apps/backend/courseeval_backend/api/routers/homework.py`

- Added shared submission-management gate for subject-scoped homework teacher
  endpoints.
- Applied it to:
  - submissions list
  - submission deep-link status
  - batch regrade
  - appeal acknowledge
  - submission history
  - teacher review
  - teacher regrade
  - submission attachment download

Also aligned an older backend test that had drifted from the current security
contract:

- `tests/backend/llm/test_llm_concurrency_scenarios.py`
  - old expectation: class teacher could read submissions for a visible course
  - current contract: class teacher cannot manage or deeply read another
    teacher's course submissions

Security tests added:

- `hard131`
- `hard132`

### 6. Batch homework policy ownership

`apps/backend/courseeval_backend/api/routers/homework.py`

- Fixed `POST /api/homeworks/batch-late-submission` so subject-scoped homework
  rows also require owner-level authority, not just course visibility.

Security test added:

- `hard133`

## Current Remaining Risks

These are the highest-signal remaining risks after the rounds above.

### A. `homework.py` still relies on multiple overlapping guards

There are now several guard layers in the file:

- `_ensure_homework_access(...)`
- `_ensure_homework_course_write_access(...)`
- `_ensure_homework_submission_management_access(...)`
- `_ensure_course_homework_status_access(...)`

This is safer than before, but it increases the chance that a future endpoint
will call the wrong helper or omit one entirely.

Next useful move:

- inventory every subject-scoped teacher endpoint in `homework.py`;
- classify it as read/list, submission-management, or homework-mutation;
- map each class to exactly one shared guard path where possible.

### B. Appeal flow remains a sensitive adjacent surface

Student appeal creation is intentionally student-scoped, but it touches:

- submission visibility;
- grading completion state;
- teacher notification fan-out;
- teacher acknowledgment/resolution.

The teacher acknowledgment side is now gated, but the broader appeal workflow
still deserves a denser red-team pass for:

- linked-class courses;
- resolved vs acknowledged status transitions;
- multi-attempt submissions;
- teacher review after appeal state transitions.

### C. Other subject-scoped modules may still have the same visibility-vs-owner split

These rounds found the same pattern repeatedly:

- route supports linked classes or course visibility;
- neighboring endpoint still treats visibility as management authority or keeps
  a stale single-class assumption.

The highest-likelihood remaining candidates are modules adjacent to homework or
sharing similar subject-scoped teacher workflows, especially where student
content or teacher actions are involved.

### D. Validation debt remains explicit

Observed local evidence is good for the targeted fixes above, but the selector
continued to recommend broader validation in recent rounds, especially:

- `security.api_regression`
- `full.pytest.postgres`

One attempted full `tests/security -q` run in a recent round timed out under the
current local timeout budget after partial progress. Treat that as incomplete
evidence, not a pass.

## Useful Tests Added In Recent Rounds

File:

- `tests/security/test_security_hardening_followup.py`

New cases added across recent rounds:

- `hard123` through `hard133`

These are high-value entry points for continuing the same style of hardening:

- start with the nearest neighboring subject-scoped route;
- copy the closest helper pattern;
- write a class-teacher-visible-but-not-owner case first;
- then add a linked-class positive case when the product should allow it.

## Validation Notes

Observed passing targeted validations from recent rounds included combinations
of:

- focused `tests/security/test_security_hardening_followup.py -k ...`
- `tests/backend/courses/test_student_course_roster_behavior.py`
- `tests/behavior/test_course_roster_homework_edge_behavior.py`
- `tests/backend/homework/test_homework_batch_ops.py`
- `tests/backend/llm/test_llm_concurrency_scenarios.py -k class_teacher`
- `ops/scripts/dev/check_api_surface_governance.py`
- `git diff --check`

Incomplete / deferred:

- full `tests/security -q` did not complete within the recent 120s local
  timeout budget and should not be reported as passed.
- `full.pytest.postgres` remains the main deferred high-confidence target.

## Recommended Next Step

If continuing this branch, the next best round is:

1. inventory remaining subject-scoped homework teacher endpoints by guard type;
2. red-team the appeal lifecycle and any teacher-side status transition route
   not yet covered by `hard131`-`hard133`;
3. run a broader `security.api_regression` pass with a longer timeout or the
   repo's PostgreSQL-backed profile if environment allows.
