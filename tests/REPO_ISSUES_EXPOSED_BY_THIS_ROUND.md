# Repository Issues Exposed By This Round

This file records repository-side issues found during this test round.
It does not record pure test-run environment problems.

## 1. Startup-time `CourseLLMConfig` initialization was not idempotent inside one ORM session

### Symptom

- During startup backfill, the app could initialize `course_llm_configs`.
- If a `CourseLLMConfig` for a `subject_id` had already been added to the same SQLAlchemy session but not yet flushed,
  later existence checks could miss that pending row.
- A second insert then triggered:
  - `UNIQUE constraint failed: course_llm_configs.subject_id`

### Fix applied this round

- `app/llm_grading.py`
  - `ensure_course_llm_config()` now checks session-local objects before querying the database.
- `app/bootstrap.py`
  - startup backfill now avoids duplicate initialization for the same subject in one pass.

## 2. Startup-time course enrollment backfill was not idempotent inside one ORM session

### Symptom

- `prepare_student_course_context()` and `sync_student_course_enrollments()` looked only at flushed database rows.
- If the same student had pending `CourseEnrollment` objects in the current session, a second pass could re-add them.
- That triggered:
  - `UNIQUE constraint failed: course_enrollments.subject_id, course_enrollments.student_id`

### Fix applied this round

- `app/course_access.py`
  - pending session enrollments are now included in the "already exists" check.

## 3. Frontend E2E coverage still depends too much on text selectors

### What was confirmed

- The mojibake seen in the `boundary` spec was mainly introduced by this round's command-line editing chain.
- However, that incident exposed a real repository-level weakness:
  - many important tests still depend on dialog titles, labels, toast copy, and full-row text.

### Why it matters

- This makes E2E outcomes sensitive to:
  - wording changes
  - pagination and list refresh
  - animation timing
  - encoding environments

### Suggested repository-level improvement

- Add more stable `data-testid` coverage in:
  - `Users`
  - `Subjects`
  - `Homework`
  - batch-class flows
  - personal settings

## 4. UI flows expose too little stable submission state

### Symptom

- In several flows, the action had already succeeded but the dialog was still in a closing animation state.
- Tests then had to rely on `toBeHidden()`, which was weaker than asserting a real outcome.

### Why it matters

- It increases false negatives in E2E even when the business action has completed.

### Suggested repository-level improvement

- Provide stronger UI signals after save/confirm actions, such as:
  - stable loading completion markers
  - a success state with a test hook
  - clearer list/API refresh completion points

## 5. User-list and enrollment-list flows may still have refresh or paging consistency issues

### Symptom

- Some full-suite Playwright failures were tied to locating rows by username or student identity.
- Single-case runs sometimes passed while full runs failed.

### Possible causes

- pagination
- residual filters
- delayed list refresh
- row selection state not fully synchronized with visible data

### Status

- This is not yet fully proven as a product bug.
- But it is a high-risk area that should be examined as a repository issue, not just dismissed as flaky tests.

## 6. Summary

- Real backend bugs were found and fixed:
  - startup `CourseLLMConfig` idempotency
  - startup `CourseEnrollment` idempotency
- The biggest remaining repository risks are in UI testability and observable state:
  - too much text-based selection
  - too much dependence on dialog animation completion
  - possible list refresh and pagination consistency problems
