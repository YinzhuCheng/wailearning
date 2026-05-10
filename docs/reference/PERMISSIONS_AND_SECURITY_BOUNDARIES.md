# Permissions and security boundaries

**Audience:** Agents implementing features without silently widening attack surface.

**Principle:** FastAPI dependencies + domain helpers enforce authorization. Vue `meta` flags are **UX hints only**.

---

## 1. Role enumeration (`UserRole`)

**Source:** `apps/backend/courseeval_backend/db/models.py` (`UserRole` enum).

| Stored value (`users.role`) | Typical meaning |
|----------------------------|-----------------|
| `admin` | Full administration; bypasses many class filters via queries |
| `class_teacher` | Scoped to `user.class_id` **plus** courses they instruct (`Subject.teacher_id`) |
| `teacher` | Subject teacher — primarily courses where `Subject.teacher_id == user.id` |
| `student` | Student — enrolled courses only (via `CourseEnrollment`) |

**Parents:** not `UserRole`. Parent flows authenticate via parent codes (`/api/parent/*`) — see [`../product/PARENT_PORTAL.md`](../product/PARENT_PORTAL.md).

---

## 2. Coarse helpers (`core/permissions.py`)

Functions like `is_admin`, `is_teacher`, `can_manage_scores` answer **role membership**, not **object ownership**.

**Risk:** Using only these for APIs that mutate another teacher’s course is insufficient — combine with course/subject checks.

---

## 3. Course visibility & access (`domains/courses/access.py`)

Key symbols:

| Symbol | Purpose |
|--------|---------|
| `get_accessible_courses_query(user, db)` | Builds filtered `Subject` query per role |
| `prepare_student_course_context` | Student login path repairs roster/enrollment alignment |
| `ensure_course_access(course_id, user, db)` | Raises `PermissionError` if not accessible |
| `ensure_course_access_http` | Same → HTTP 403/404 |
| `is_course_instructor(user, course)` | Admin **or** assigned `Subject.teacher_id` |
| `sync_course_enrollments` | Required courses: ensures enrollments for class roster; electives skipped |
| `sync_student_course_enrollments` | Student-side repair for required courses |
| `CourseEnrollmentBlock` | Prevents auto re-enrollment after explicit removal |

**Elective rule:** `sync_course_enrollments` returns early when `course_type == elective` — elective enrollment is explicit (`CourseEnrollment` rows from self-enroll API or seeds like partial demo enrollments).

---

### Subject-scoped route ordering rule

When a FastAPI route is explicitly scoped by `subject_id` / course id, validate
that course first:

```python
course = ensure_course_access_http(subject_id, current_user, db)
```

Only apply `get_accessible_class_ids(...)`, `apply_class_id_filter(...)`, or
`Subject.class_id.in_(...)` as the primary authorization filter for class-wide
routes that do **not** have a course scope. Do not return `[]` or raise `403`
just because the derived class-id set is empty before checking course access.

Why this matters:

- `teacher` users often own courses through `Subject.teacher_id` without having
  a `user.class_id`.
- `class_teacher` users may see courses through `subject_class_links`.
- elective courses may have `Subject.class_id = None` and still contain valid
  `CourseEnrollment` rows.
- score, dashboard, homework, material, notification, attendance, discussion,
  and file-download surfaces all need course-owned access to work even when a
  class-only filter would be empty.

Safe pattern:

1. If `subject_id` is present, call `ensure_course_access_http(...)`.
2. Build the query from the course/subject predicate, for example
   `Score.subject_id == subject_id`.
3. Apply optional `class_id` filters only as additional narrowing, not as the
   initial permission gate.
4. For no-`subject_id` list endpoints, keep class-wide filtering via
   `get_accessible_class_ids(...)` / `apply_class_id_filter(...)`.

---

## 4. Homework & grading (patterns)

Homework routers (`api/routers/homework.py`) generally:

1. Resolve current user (`get_current_user`).
2. Load homework / submission with DB session.
3. Compare `homework.subject_id` / `class_id` against accessible courses or instructor relationship.
4. Return redacted payloads for students (e.g. `rubric_staff_only`, `reference_answer` hidden — see serializers in-router).

**LLM discussion:** `llm_discussion.py` intentionally omits teacher-only homework fields from student-triggered assistant threads. Current invoke matrix:

- **student**: allowed, billed against the student's daily token pool after account↔roster resolution;
- **teacher / class_teacher / admin**: allowed on discussions they can already access, but not limited by student token caps;
- hidden teacher-only homework fields remain hidden from student-triggered context even though staff/admin may also invoke the assistant.

---

## 5. LLM admin vs teacher capabilities

| Surface | Who configures |
|---------|----------------|
| Global endpoint presets, global quota policy | Admin (`/api/llm-settings` family) |
| Per-course LLM enable, endpoints order, prompts | Teacher assigned to course **or** admin; class teachers may manage courses for their class per recent product rules — verify router guards when editing |

**Agent rule:** open the specific router function before assuming UI parity.

---

## 6. E2E dev API (`api/routers/e2e_dev.py`)

- Router always registered from `main.py`, but handlers short-circuit unless `settings.expose_e2e_dev_api()` is true.
- `expose_e2e_dev_api` is false when `APP_ENV` is production-like **or** `E2E_DEV_SEED_ENABLED` is false.
- Powerful endpoints may require **seed token + optional admin JWT** (`E2E_DEV_REQUIRE_ADMIN_JWT`).

This is a **supply-chain sensitive** surface — never weaken checks without security review.

---

## 7. JWT notes

- Tokens include user id + role; password changes bump `token_version` invalidating old JWTs (see auth router + login logging).
- CORS + credentials: wildcard origins disable credential cookies in `main.py` CORS middleware — review when touching auth.

---

## 8. Frontend route `meta` (admin)

`apps/web/admin/src/router/index.js` uses flags such as `requiresAdmin`, `requiresTeachingStaff`.

These control **navigation/UI**. They do **not** replace backend checks.

---

## 9. Reference reading

- Vertical traces: [`../architecture/CORE_BUSINESS_FLOWS.md`](../architecture/CORE_BUSINESS_FLOWS.md)
- LLM specifics: [`../product/LLM_HOMEWORK_GUIDE.md`](../product/LLM_HOMEWORK_GUIDE.md)

---

## 10. 待人工确认

- **Exact matrix** for every `subjects` mutation endpoint across `class_teacher` vs `teacher` (product evolves). Agents must grep `is_course_instructor` / `ensure_course_access` at edit time rather than trusting prose alone.
