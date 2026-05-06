# Data model essentials (ORM-oriented)

**Audience:** Agents needing table/field grounding without reading all 800+ lines of `models.py` first.

**Authoritative source:** `apps/backend/wailearning_backend/db/models.py`.

**Schema repair:** additive columns and compatibility DDL live in `bootstrap.py` (`ensure_schema_updates()`). There is **no separate Alembic migration tree** in this repository snapshot — agents rely on `ensure_schema_updates` + `Base.metadata.create_all`.

---

## 1. Identity & roster

| Model | Table | Notes |
|-------|-------|------|
| `User` | `users` | `role` stores `UserRole` string; `class_id` nullable for staff |
| `Class` | `classes` | |
| `Student` | `students` | Roster row; `student_no` aligns with student user `username` |
| `CourseEnrollment` | `course_enrollments` | Unique `(subject_id, student_id)` |
| `CourseEnrollmentBlock` | `course_enrollment_blocks` | Blocks auto re-sync |

### 1.1 Student roster ↔ student `User` alignment (implementation truth)

The repository maintains **two persisted representations** of a learner:

1. **`students`** — administrative / teaching roster (`Student`), including gender and contact fields.
2. **`users`** where `role=student` — login account (`User.username` **must equal** `Student.student_no` for the same class context).

**Authoritative source for “who is in the class”:** the **`students` table** (plus `course_enrollments` for per-course views). Login accounts are **not** created through a separate CSV import on the Users screen; instead the backend **`reconcile_student_users_and_roster`** (`domains/roster/sync.py`) runs at application startup and is invoked again on **read/list admin surfaces** so transient drift self-heals:

- `GET /api/students` (list) and `GET /api/students/{id}` call `reconcile_student_users_and_roster` then `commit` before querying/serializing.
- `GET /api/users` (admin list) does the same **before** returning rows.

Effects for agents:

- Do **not** expect `GET /api/users/student-candidates` or `POST /api/users/student-candidates/load` — those endpoints were removed when the admin UI dropped 「文件导入学生用户」; roster import remains on **学生管理** (`Students.vue`: 文件 / 粘贴导入).
- `StudentResponse` (`api/schemas.py`) intentionally allows **`gender` default `MALE`** and **`class_id: Optional[int]`** so legacy rows with NULL ORM fields still serialize; `build_student_response` fills display placeholders (`无` / `—`) for empty names or student numbers.
- Permission checks on `GET/PUT/DELETE /api/students/{id}` treat **`class_id is None`** as “not yet assigned to a class shell” and **do not** 403 solely because `None not in class_ids` (that Python expression was a bug source).

### 1.2 Pitfall catalog (student admin UX)

| Symptom | Likely cause | Mitigation |
|---------|----------------|------------|
| Element Plus **student form** shows two red fields immediately (性别 + 班级) | `StudentForm.vue` used `el-radio value="..."` instead of `label="..."`, so `v-model` never matched an option; combined with NULL `class_id` from API | Fixed radios; `clearValidate()` after `loadStudent()`; reconcile fills class when a matching user exists |
| Playwright / strict tests fail looking for `users-open-student-import` | UI removed | Assert absence of 「文件导入学生用户」 or use `users-open-create` |
| Slow admin **学生管理** list on huge DB | Full `reconcile_student_users_and_roster` scans all roster + student users each request | Acceptable for demo/small schools; for very large tenants consider moving reconcile to a background job + lighter incremental sync (not implemented here) |


## 2. Courses & materials

| Model | Table | Notes |
|-------|-------|------|
| `Subject` | `subjects` | **Course** entity; `teacher_id`, `class_id`, `course_type` (`required`/`elective`), scheduling fields |
| `CourseMaterial` | `course_materials` | `content_format` default `markdown` |
| `CourseMaterialChapter` | `course_material_chapters` | Hierarchy + uncategorized bucket |
| `CourseMaterialSection` | `course_material_sections` | Placement linking materials to chapters |
| `CourseGradeScheme` | `course_grade_schemes` | Weights |
| `CourseExamWeight` | `course_exam_weights` | Exam composition |

---

## 3. Homework lifecycle

| Model | Table | Notes |
|-------|-------|------|
| `Homework` | `homeworks` | Instructions; split rubric: `rubric_text` (student-visible), `rubric_staff_only`; `reference_answer` teacher-only; `content_format`; late rules; `auto_grading_enabled` |
| `HomeworkSubmission` | `homework_submissions` | Summary row per student per homework; mirrors latest attempt content; `review_score`/**effective** aggregate |
| `HomeworkAttempt` | `homework_attempts` | Versioned attempts; `counts_toward_final_score`, `is_late` |
| `HomeworkScoreCandidate` | `homework_score_candidates` | Parallel scores (`source`: auto/teacher, …) |
| `HomeworkGradingTask` | `homework_grading_tasks` | Async LLM grading tasks |
| `HomeworkGradeAppeal` | `homework_grade_appeals` | Appeals |

**Effective score (product semantics):** aggregation crosses attempts according to eligibility rules implemented in `llm_grading.py` (`resolve_effective_submission_score`, `attempt_eligible_for_effective_score_aggregate`). Summary row still reflects **latest** attempt body for UX — see [`../architecture/CORE_BUSINESS_FLOWS.md`](../architecture/CORE_BUSINESS_FLOWS.md).

---

## 4. LLM configuration & usage accounting

| Model | Table | Notes |
|-------|-------|------|
| `LLMEndpointPreset` | `llm_endpoint_presets` | Vendor config + validation fields |
| `CourseLLMConfig` | `course_llm_configs` | Per-course LLM settings |
| `CourseLLMConfigEndpoint` | `course_llm_config_endpoints` | Ordered preset attachments |
| `LLMGroup` / members | `llm_groups`, membership tables | Routing groups |
| `LLMGlobalQuotaPolicy` | `llm_global_quota_policies` | Single-row global policy |
| `LLMStudentTokenOverride` | `llm_student_token_overrides` | Per-student caps |
| `LLMTokenUsageLog` | `llm_token_usage_logs` | Billing attribution |
| `LLMQuotaReservation` | `llm_quota_reservations` | Reservation rows |

Legacy quota columns on `course_llm_configs` were dropped on Postgres via `ensure_schema_updates` — SQLite attempts best-effort `ALTER DROP COLUMN`.

---

## 5. Discussions & notifications

| Model | Table | Notes |
|-------|-------|------|
| `CourseDiscussionEntry` | `course_discussion_entries` | Thread bodies; `body_format` |
| `Notification` | `notifications` | Multiple targeting modes |
| `NotificationRead` | `notification_reads` | Read receipts |

---

## 6. Logging & appearances

| Model | Table | Notes |
|-------|-------|------|
| `OperationLog` | `operation_logs` | Login / actions |
| `UserAppearanceStyle` | `user_appearance_styles` | Theme configs |

---

## 7. Naming traps

- **`Subject` ≠ generic English subject** — means **course offering** in most UI/API contexts (`/api/subjects`).
- **Teacher演示账号 vs roster `teacher_id`:** demo seed assigns roster students to primary demo teacher even when multiple teacher accounts exist — enrollment demos may still link to class roster teacher.

---

## 8. 待人工确认

- Whether every auxiliary table has parity coverage in `ensure_schema_updates` for greenfield SQLite installs under adversarial import orders — if pytest flakes arise, capture stack traces in [`../known-issues-and-risks.md`](../known-issues-and-risks.md).
