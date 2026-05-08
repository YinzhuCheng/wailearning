# Core Business Flows (Implementation-Aligned)

## Purpose

This document traces **how features actually run** in this repository: HTTP entrypoints, domain helpers, persistence, background processing, and how state appears back in clients. It is written primarily for maintainers and LLM coding agents who need to avoid guessing from folder names alone.

When this document conflicts with marketing language or older notes elsewhere, **trust the cited code paths**.

If you change router signatures, queue semantics, or worker startup, update this file in the same change set.

---

## Conventions

- **Admin SPA**: `apps/web/admin/` — Vue 3 + Element Plus; API calls go through `apps/web/admin/src/api/` helpers (axios) and typically hit `/api/*` via Vite dev proxy (`apps/web/admin/vite.config.js`: `VITE_PROXY_TARGET` defaults to `http://127.0.0.1:8001`).
- **Parent SPA**: `apps/web/parent/` — separate build; dev server defaults to port **5174** (`apps/web/parent/vite.config.js`); same `/api` proxy pattern.
- **Backend**: FastAPI app assembled in `apps/backend/wailearning_backend/main.py`; route modules under `apps/backend/wailearning_backend/api/routers/`; Pydantic contracts in `apps/backend/wailearning_backend/api/schemas.py`.
- **Course access**: Most course-scoped routes call `ensure_course_access` / `ensure_course_access_http` in `apps/backend/wailearning_backend/domains/courses/access.py`. The `_http` variant maps `PermissionError` → **403** and `ValueError` → **404** for consistent API behavior.

---

## 1. Authentication and sessions

### Entry

- `POST /api/auth/login` — `apps/backend/wailearning_backend/api/routers/auth.py`
- JWT dependency — `apps/backend/wailearning_backend/core/auth.py` (`get_current_user`, `get_current_active_user`, optional JWT for E2E gates)

### Behavior (high level)

1. Client sends credentials; router validates user and returns a JWT (`ACCESS_TOKEN_EXPIRE_MINUTES` from settings).
2. Subsequent requests send `Authorization: Bearer <token>`.
3. Role checks use string values stored on `users.role` aligned with `UserRole` enum — `apps/backend/wailearning_backend/db/models.py` (`admin`, `class_teacher`, `teacher`, `student`).

For **student** accounts, login is also a light repair point:

4. After successful login, the router caches the role/class decision **before** writing the login `operation_logs` row, then re-queries the user when needed and runs `prepare_student_course_context(...)`.
5. `prepare_student_course_context(...)` may:
   - reconcile a sole same-`student_no` roster row into the account class as a legacy compatibility path,
   - create a missing roster row from the student account itself (`sync_student_roster_from_user_accounts`) when legacy drift left only the login account,
   - and then sync required-course enrollments.

This is important because student quota APIs, homework submission, and discussion LLM billing all depend on the resolved `Student.id`, not merely on `users.id`.

### Related configuration

- `SECRET_KEY`, `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES` — `apps/backend/wailearning_backend/core/config.py`

### Pitfalls

- Forgot-password throttling and registration validation interact with `operation_logs` and optional public registration flags — see [CONFIGURATION_REFERENCE.md](CONFIGURATION_REFERENCE.md).

---

## 2. Course visibility and enrollment

### Entry (examples)

- Subject listing and mutations — `apps/backend/wailearning_backend/api/routers/subjects.py`
- Student elective catalog / enroll / drop — same router (endpoints gated by `UserRole.STUDENT`)
- Class-scoped administration — `apps/backend/wailearning_backend/api/routers/classes.py`, `students.py`, `users.py`

### Domain logic

- **Which courses a user sees** — `get_accessible_courses_query` and related helpers in `domains/courses/access.py`:
  - **Admin**: all subjects.
  - **Student**: subjects linked through `CourseEnrollment` after `prepare_student_course_context` reconciles roster vs account class when applicable.
  - **Teacher**: subjects where `Subject.teacher_id == user.id`.
  - **Class teacher**: subjects whose legacy anchor `Subject.class_id == user.class_id`, **plus** any subject that has a `subject_class_links` row for that class, union subjects where the user is the assigned teacher (`Subject.teacher_id`).

- **Multi-class required offerings** — `subject_class_links` (`SubjectClassLink` ORM) stores `(subject_id, class_id, enrollment_mode)`. Whole-class auto sync only applies to links with `enrollment_mode == all_in_class`. Electives intentionally have **no** links and `Subject.class_id IS NULL`; student self-enroll writes `CourseEnrollment.class_id` from the student's roster class, not from the course.

### Student roster coupling

- `reconcile_student_users_and_roster` runs during app lifespan — `main.py` — and ties student login identities primarily through `users.student_id`, using `student_no == username` only as a legacy recovery path when an explicit binding is missing.

---

## 3. Homework: submission → queue → worker → UI

This is the highest-traffic “vertical slice” for the product.

### 3.1 Student submission (HTTP)

1. **Frontend**: student homework UI calls `POST /api/homeworks/{homework_id}/submission` with body validated by `HomeworkSubmissionCreate` — see `api/schemas.py`.
2. **Router**: `submit_homework` in `api/routers/homework.py`.
3. **Access**: `_ensure_homework_access` / `_resolve_student_for_user` ensure the caller is the roster-linked student for that homework’s class/course.
4. **Roster + enrollment side effects (student logins)**: `prepare_student_course_context` in `domains/courses/access.py` runs on many student requests and can **synchronize** `CourseEnrollment` rows for **required** courses by inspecting `subject_class_links` where `enrollment_mode == all_in_class` (with a legacy fallback to `Subject.class_id == student.class_id` until every historical row has been backfilled). Students may therefore gain enrollment implicitly without an explicit teacher click. **`_resolve_student_for_user`** still checks enrollment when `homework.subject_id` is set; cross-class cases may hit **`ensure_course_access_http`** first (**403**) before roster mismatch (**404**).

5. **Persistence**:
   - Upserts `HomeworkSubmission` summary row.
   - Inserts immutable `HomeworkAttempt` for each submission.
6. **Auto grade enqueue**: if `homework.auto_grading_enabled`, calls `queue_grading_task(db, attempt, "new_submission")` — defined in `apps/backend/wailearning_backend/llm_grading.py`.
7. **Summary refresh**: `refresh_submission_summary` recomputes denormalized fields on `HomeworkSubmission`. The displayed **「有效成绩」** (`review_score` / `review_comment`) is **not** necessarily tied only to `latest_attempt_id`: among attempts linked to the submission summary, only rows that are **on/before the homework due time** or have **`counts_toward_final_score == true`** participate; the winner is the maximum score after resolving teacher-vs-auto precedence **per attempt**, then taking the global max across those attempts. Tie-break favors higher score, then teacher source, then newer candidate timestamps. Implementation lives in `apps/backend/wailearning_backend/llm_grading.py` (`resolve_effective_submission_score`, `refresh_submission_summary`). The summary row still mirrors **latest** attempt body/attachments/`latest_task_*` fields for UX continuity while the score reflects the aggregate rule.
8. **Commit** and response serialized via `_serialize_submission`.

Code anchor for enqueue:

```1059:1061:apps/backend/wailearning_backend/api/routers/homework.py
    if homework.auto_grading_enabled:
        queue_grading_task(db, attempt, "new_submission")
```

### 3.2 Queue model (database-backed, not Redis)

- New rows in `HomeworkGradingTask` with `status="queued"` — created by `queue_grading_task` — `llm_grading.py`.
- Duplicate protection: if a queued/processing task already exists for the attempt, the existing task is reused and submission summary task fields are aligned.

### 3.3 Worker execution

- **Startup**: `main.py` lifespan calls `start_grading_worker()` when `ENABLE_LLM_GRADING_WORKER` and `LLM_GRADING_WORKER_LEADER` are true — only the leader process should drain in multi-worker `gunicorn`.
- **Implementation**: `llm_grading.py` — polling loop + thread pool for LLM HTTP calls; stale task reclamation controlled by `LLM_GRADING_TASK_STALE_SECONDS`.
- **Outcome**: writes `HomeworkScoreCandidate` rows, updates task status/error fields, records token usage through `domains/llm/quota.py`, and may emit notifications via `domains/homework/notifications.py`.

There is **no separate message broker** (no Redis/Celery) in this codebase; the queue is the `homework_grading_tasks` table.

### 3.4 Teacher / admin views

- Lists and batch actions — still `api/routers/homework.py` (e.g. submissions list, batch regrade).
- Regrade paths enqueue new tasks or reuse queue logic depending on operation — follow call sites of `queue_grading_task` and teacher-triggered helpers in the same module.
- **Serialization rule**: `_serialize_homework(..., viewer=current_user)` strips `reference_answer` and `rubric_staff_only` when `viewer.role == student`, while retaining both fields for teachers/admins/creators. Agents altering homework visibility must update serializers and LLM/discussion prompt builders together — see [LLM homework guide](../product/LLM_HOMEWORK_GUIDE.md) «Rubric visibility» section.

### 3.5 Parent portal read path

- Parent-facing aggregated homework/score routes live under `api/routers/parent.py` — they enforce parent-code verification and read student data indirectly; they do not bypass homework access rules for staff routes.

---

## 4. LLM configuration and quotas

### Admin / teacher configuration HTTP

- `api/routers/llm_settings.py` — presets, course LLM config, global quota policy, student overrides.
- Student-facing quota **read** endpoints avoid side effects that mutate course configuration (quota snapshots read from policy + usage tables).

### Domain

- Quota math and recording — `domains/llm/quota.py`, `domains/llm/token_quota.py`.
- Routing between endpoint presets — `domains/llm/routing.py`.

### Persistence (conceptual)

- Described in [../product/LLM_HOMEWORK_GUIDE.md](../product/LLM_HOMEWORK_GUIDE.md) — source of truth for table names and field responsibilities.

---

## 5. Materials and chapters

### HTTP

- Materials and placement — `api/routers/materials.py`
- Hierarchical chapters — `api/routers/material_chapters.py`

### Access

- Instructor checks often use `is_course_instructor` / `ensure_course_access_http` — `domains/courses/access.py`.

---

## 6. Notifications

### HTTP

- CRUD and read-state — `api/routers/notifications.py`
- Lightweight poll snapshot — `GET /api/notifications/sync-status` (same visibility as list query helpers in-router).

### Admin SPA behavior

- Header badge + polling + `BroadcastChannel` — documented in [../development/NOTIFICATION_HEADER_AND_REALTIME_SYNC.md](../development/NOTIFICATION_HEADER_AND_REALTIME_SYNC.md).

---

## 7. Learning notes

### HTTP

- `api/routers/learning_notes.py` - prefix `/api/learning-notes`.
- `GET /api/learning-notes?scope=mine|public&subject_id=...` lists owned notes or public notes. The persisted enum value for public notes is still `visibility="course"` for compatibility, but the effective audience is determined by `subject_id`: a public note with a course remains same-course-visible, while a public note with `subject_id IS NULL` is visible to every authenticated user. Public listing with a `subject_id` filter returns only notes bound to that accessible course; public listing without a filter returns unbound public notes plus public notes for courses from `get_accessible_course_ids(current_user, db)`.
- `POST /api/learning-notes` creates a named note. `visibility` defaults to `private`; `visibility="course"` may be saved with a valid accessible `subject_id` for same-course sharing or with `subject_id = NULL` for all-authenticated sharing.
- `GET/PUT/DELETE /api/learning-notes/{note_id}` enforce owner-only mutation and owner-or-public-scope read. Private notes remain owner-only. Public notes bound to a course require normal course access for non-owner readers/commenters. Public notes without a course can be read and discussed by any authenticated user.
- `/{note_id}/chapters` and `/{note_id}/resources` implement an editable note-local outline and resource tree.
- `/{note_id}/discussion` stores note-scoped discussion entries. Private note discussion is readable/commentable only by the owner. Course-visible note discussion is readable/commentable by same-course users.

### Copy semantics

Learning notes deliberately do **not** reuse `CourseMaterial` rows. When a note is created with `copy_from_subject_id`, the backend copies the course's `CourseMaterialChapter` tree into `LearningNoteChapter` rows owned by the new note. If `copy_materials` is true, each copied resource stores a note-owned snapshot of title/body/content format and keeps attachment URLs by reference through `LearningNoteResource.source_material_id` / `attachment_url`. This avoids physical file duplication while allowing students to freely edit their note structure and resource text.

### LLM discussion behavior

The note discussion assistant reuses the course LLM routing stack (`ensure_course_llm_config` + `_call_discussion_with_routing`) only after the note is associated with a course. Student callers still must resolve to a roster row through the discussion binding helper before an assistant reply is attempted. Current implementation caveat: learning-note assistant replies do **not** reserve or write rows in `LLMQuotaReservation` / `LLMTokenUsageLog` because those quota rows are currently tied to `discussion_llm_jobs` or homework grading jobs. A robust future implementation should add a note-specific LLM job/usage attribution table or generalize quota attribution before claiming parity with course discussion billing.

### Admin SPA

`apps/web/admin/src/views/LearningNotes.vue` exposes the teacher/student sidebar destination `/learning-notes`. It lets users create private notes, optionally copy course outline/materials from accessible courses, publish a note either to same-course users (when a course is selected) or to all authenticated users (when no course is selected), edit the note-local outline/resources, and participate in the note discussion. Admin users are intentionally routed away by `adminHiddenPaths`; the feature was requested for teachers and students.

---

## 8. Course discussions (homework / materials threads)

### HTTP

- `api/routers/discussions.py` — prefix `/api/discussions`.
- Access uses `ensure_course_access_http` and `is_course_instructor` patterns consistent with other course features.

Discussion LLM jobs (if enabled for a course) are orchestrated through modules referenced from this router and `llm_discussion.py` — **待人工确认**: exact job lifecycle should be verified against `DiscussionLLMJob` usage when changing async discussion behavior.

Implementation-aligned student binding rule for discussion LLM:

- the assistant reply path no longer requires `Subject.class_id` to be populated;
- instead it runs the same `prepare_student_course_context(...)` + `get_student_profile_for_user(...)` chain used elsewhere and validates the discussion's explicit `class_id` scope against the resolved roster row;
- this matters for elective / multi-class-compatible course shapes where `subjects.class_id` may be `NULL` while the homework/material discussion itself is still class-scoped and the student is legitimately enrolled.

Implementation-aligned role / quota rule for discussion LLM:

- students may invoke discussion LLM and are billed against the same per-student daily pool used by homework grading;
- teachers, class teachers, and administrators may also invoke discussion LLM on accessible course discussions;
- those staff/admin discussion-LMM calls are **not** gated by student token caps and do not require a `requester_student_id`;
- student-only hidden rubric / reference-answer leakage rules still apply: staff/admin invocation changes quota treatment, not content redaction boundaries.

Admin SPA discussion list rendering:

- each discussion row now serializes `author_avatar_url` alongside author identity fields;
- the frontend discussion panel fetches authenticated avatar blobs when available and otherwise falls back to role-colored initials (or `助` for the assistant user).

---

## 9. Appearance presets (user themes)

### HTTP

- `api/routers/appearance.py` — prefix `/api/appearance`.

---

## 10. E2E and mock LLM (non-production only)

### Router registration

- `api/routers/e2e_dev.py` mounted under `/api/e2e` with a **dependency** that returns **404** unless `settings.expose_e2e_dev_api()` is true — see `main.py` comments.
- `expose_e2e_dev_api()` is **false** when `APP_ENV` is production or `E2E_DEV_SEED_ENABLED` is false — `core/config.py`.

### Typical automation flow

1. `POST /api/e2e/dev/reset-scenario` with `X-E2E-Seed-Token` seeds users/courses/homework for Playwright.
2. “Powerful” endpoints (mock LLM, forced grading pump) may require **dual gate**: seed token **plus** admin JWT when `E2E_DEV_REQUIRE_ADMIN_JWT=true` — default in `apps/web/admin/playwright.config.cjs` for managed subprocesses.

Details: [../development/DEVELOPMENT_AND_TESTING.md](../development/DEVELOPMENT_AND_TESTING.md) and [../development/TEST_EXECUTION_PITFALLS.md](../development/TEST_EXECUTION_PITFALLS.md).

---

## 11. Operational logging

### HTTP

- `api/routers/logs.py` — audit / operation logs for administrator views.

---

## Cross-links

- Deployment shape — [../operations/DEPLOYMENT_AND_OPERATIONS.md](../operations/DEPLOYMENT_AND_OPERATIONS.md)
- Full env reference — [CONFIGURATION_REFERENCE.md](CONFIGURATION_REFERENCE.md)
- Test layers and commands — [../development/DEVELOPMENT_AND_TESTING.md](../development/DEVELOPMENT_AND_TESTING.md)
