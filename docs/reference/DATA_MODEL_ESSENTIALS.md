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

---

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
