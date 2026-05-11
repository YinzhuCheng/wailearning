# Recent Posts + Student Binding Handoff

Date: 2026-05-11

Branch: `cursor/repository-normalization`

Status:

- the structured discussion link-card line is functionally complete for this round and its targeted Playwright spec has passed locally;
- the student roster/account strong-binding refactor described below is implemented and validated locally;
- the `最近发表` feature is now implemented as a permission-filtered authored-content feed aligned with the discussion linkable target set.

---

## 1. User Direction At Handoff Time

The user redirected from governance cleanup to feature work, then asked for:

1. removal of the obsolete governance handoff file;
2. continuation and validation of the discussion link-card line;
3. discussion and implementation groundwork for a new `最近发表` feature;
4. stronger invariant alignment between student roster rows (`Student`) and student login accounts (`User(role=student)`);
5. finally, a committed handoff plus commit/push before leaving.

This document is therefore the active handoff for the current branch state.

---

## 2. Completed Since The Last Push

### 2.1 Discussion link cards line: locally closed for now

Previously implemented link-card support for:

- `course`
- `discussion_entry`

was resumed and validated rather than further changed.

Confirmed local validation:

```powershell
.\.venv\Scripts\python.exe ops\scripts\dev\playwright_preflight.py --json
```

```powershell
cd apps\web\admin
node scripts\playwright-external-runner.cjs e2e-discussion-link-cards.spec.js --project=chromium
```

Result:

- `2 passed`

Implication:

- picker, saved-card, and mobile screenshots flow passed;
- course-card deep link to `/course-home` passed;
- discussion-entry deep link and highlight flow passed.

No additional code changes were required for the link-card line in this round.

### 2.2 Governance cleanup completed

Removed:

- `docs/handoffs/2026-05-10-documentation-governance.md`

Updated:

- `AGENTS.md`

Reason:

- the user explicitly said they no longer wanted the governance-level handoff retained;
- `AGENTS.md` now refers generically to the active committed handoff under `docs/handoffs/` instead of naming the deleted file.

### 2.3 Student roster/account strong-binding refactor completed

This was the main implementation work in this round.

User-aligned product decision:

- every active student should have both:
  - a canonical `Student` roster row;
  - a bound `User(role=student)` login account;
- students should not remain permanently classless;
- missing class assignment should fall back to a reserved temporary class instead of `NULL`;
- ordinary `teacher` users do **not** need a class;
- `class_teacher` users **do** need a class;
- initial student password may remain equal to the student username / student number.

Implemented behavior:

1. Added a reserved temporary class helper under roster identity utilities:
   - class name: `待分班`
   - grade: `0`
2. Student-side repair helpers now normalize missing class assignment into that temporary class.
3. Student roster rows and student login accounts now align more aggressively:
   - `users.username` mirrors `students.student_no`
   - `users.real_name` mirrors `students.name`
   - `users.class_id` mirrors `students.class_id`
   - `users.student_id` is the canonical binding
4. Active student-user reconciliation ignores inactive student accounts, so deleting or deactivating a student account no longer automatically resurrects a roster row on the next reconcile pass.
5. API write paths now fail loudly on student-binding conflicts instead of silently leaving half-bound state in explicit admin routes.
6. `class_teacher` role now requires a class binding; ordinary `teacher` remains class-optional.

Important implementation interpretation:

- this round intentionally makes the product **less permissive** about "classless active students";
- legacy compatibility still exists in some response models (`class_id: Optional[int]`) for schema/read compatibility, but normal create/update/repair paths now backfill classless active students into `待分班`.

---

## 3. Files Changed In This Round

### Backend code

- `apps/backend/courseeval_backend/domains/roster/identity.py`
- `apps/backend/courseeval_backend/domains/roster/sync.py`
- `apps/backend/courseeval_backend/domains/roster/reconciliation.py`
- `apps/backend/courseeval_backend/domains/roster/audit.py`
- `apps/backend/courseeval_backend/api/routers/users.py`
- `apps/backend/courseeval_backend/api/routers/students.py`
- `apps/backend/courseeval_backend/api/routers/auth.py`
- `apps/backend/courseeval_backend/api/schemas.py`

### Tests and validation metadata

- `tests/backend/roster/test_student_identity_guardrails.py`
- `tests/backend/roster/test_student_identity_repair.py`
- `tests/backend/roster/test_student_user_api_roster_sync.py`
- `tests/backend/roster/test_admin_student_roster_from_users.py`
- `tests/backend/roster/test_roster_enroll_and_batch_class.py`
- `tests/backend/courses/test_user_student_class_required.py`
- `tests/TEST_SELECTION_TARGETS.json`
- `docs/development/testing/test-execution-targets.csv`

### Documentation

- `docs/reference/DATA_MODEL_ESSENTIALS.md`
- `AGENTS.md`
- removed `docs/handoffs/2026-05-10-documentation-governance.md`
- added this handoff file

---

## 4. Validation Run In This Round

### Static / governance

Passed:

```powershell
.\.venv\Scripts\python.exe -m py_compile apps\backend\courseeval_backend\domains\roster\identity.py apps\backend\courseeval_backend\domains\roster\sync.py apps\backend\courseeval_backend\domains\roster\reconciliation.py apps\backend\courseeval_backend\domains\roster\audit.py apps\backend\courseeval_backend\api\routers\users.py apps\backend\courseeval_backend\api\routers\students.py apps\backend\courseeval_backend\api\routers\auth.py apps\backend\courseeval_backend\api\schemas.py
```

```powershell
git diff --check
```

```powershell
.\.venv\Scripts\python.exe ops\scripts\dev\check_schema_governance.py
```

```powershell
.\.venv\Scripts\python.exe ops\scripts\dev\check_repository_normalization.py
```

```powershell
.\.venv\Scripts\python.exe ops\scripts\dev\check_api_surface_governance.py
```

```powershell
.\.venv\Scripts\python.exe ops\scripts\dev\lint_validation_registry.py
```

```powershell
.\.venv\Scripts\python.exe -m unittest tests.backend.manual.test_validation_selector -v
```

```powershell
.\.venv\Scripts\python.exe ops\scripts\dev\check_text_encoding.py apps\backend\courseeval_backend\api\schemas.py docs\reference\DATA_MODEL_ESSENTIALS.md docs\development\testing\test-execution-targets.csv tests\TEST_SELECTION_TARGETS.json
```

### Focused backend / roster validation

Passed:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\backend\roster\test_student_identity_audit.py tests\backend\roster\test_student_identity_repair.py tests\backend\roster\test_student_identity_guardrails.py tests\backend\roster\test_student_user_api_roster_sync.py tests\backend\courses\test_user_student_class_required.py -q
```

Initial run exposed expected old-assumption failures about:

- allowing classless students;
- preserving mismatched `student_no` when a bound user had a different username;
- silently allowing cross-class duplicate username/student_no half-binding.

Those failures were fixed and the updated grouped run passed.

Passed:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\backend\roster -q
```

Result:

- `59 passed`

Passed:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\backend\auth\test_public_registration_validation.py tests\backend\roster\test_admin_student_roster_from_users.py tests\backend\roster\test_roster_enroll_and_batch_class.py tests\backend\courses\test_student_course_roster_behavior.py -q
```

Result:

- `37 passed`

### Security regression

Selector had recommended broad review for `security.api_regression` because auth and user-management routes were touched.

Passed:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\security -q
```

Result:

- `22 passed`

### Discussion link-card browser validation

Passed:

```powershell
.\.venv\Scripts\python.exe ops\scripts\dev\playwright_preflight.py --json
```

```powershell
cd apps\web\admin
node scripts\playwright-external-runner.cjs e2e-discussion-link-cards.spec.js --project=chromium
```

Result:

- `2 passed`

---

## 5. Recent Posts Current Implementation

`最近发表` is now implemented, and its object set intentionally matches the discussion linkable target set:

- `discussion_entry`: course discussion entries and learning-note discussion entries, excluding `message_kind == "llm_assistant"`.
- `learning_note`: authored learning notes.
- `material`: authored course materials that resolve through the normal linked-target resolver.
- `homework`: teacher-authored homework assignments that resolve through the normal linked-target resolver.
- `course`: courses where `Subject.teacher_id == author.id`.

Important exclusions:

- homework submissions are not aggregated;
- notifications and audit/activity rows are not aggregated;
- class-only materials or homework without a linkable course target are not shown in the feed, because the user asked for `最近发表` and linkable objects to stay consistent.

Unassigned / ownerless edge cases:

- courses with no `teacher_id` have no author for this feed and are not listed on any user's recent-posts page;
- homework requires `created_by`, so an ownerless homework row is not expected in normal data;
- hidden objects are silently omitted rather than counted.

### Backend Surface

Implemented routes:

- `GET /api/recent-posts/me`
- `GET /api/recent-posts/users/{user_id}`

Supported `kind` values:

- `all`
- `comment`
- `note`
- `material`
- `homework`
- `course`

Visibility rule:

- each item is included only if the current viewer could already open the underlying object through the normal product route / link-card resolver;
- private notes remain hidden from other users and from admins when the normal learning-note route would hide them;
- students viewing a teacher see only teacher-authored homework / teacher-taught courses from courses they can already access;
- admins do not gain private-note visibility through this feed.

Backend files:

- `apps/backend/courseeval_backend/api/routers/recent_posts.py`
- `apps/backend/courseeval_backend/api/schemas.py`

### Frontend Surface

Implemented routes:

- `/recent-posts/me`
- `/recent-posts/users/:userId`

Entry points:

- personal settings opens the current user's feed;
- discussion author avatar opens that user's feed;
- admin user management table has a `最近发表` action.

The recent-posts page now exposes filters for all current authored kinds:

- all, comment, note, material, homework, course.

Frontend files:

- `apps/web/admin/src/views/RecentPosts.vue`
- earlier route/API/avatar entry wiring remains in `apps/web/admin/src/router/index.js`, `apps/web/admin/src/api/index.js`, `apps/web/admin/src/components/DiscussionAuthorAvatar.vue`, `apps/web/admin/src/components/CourseDiscussionPanel.vue`, and `apps/web/admin/src/views/Users.vue`.

### Default Demo Data

The existing `INIT_DEFAULT_DATA=true` demo bundle already contains visible examples for the implemented feed:

- demo teacher `teacher` / password `111111`;
- teacher-authored required and elective homework;
- teacher-authored course materials;
- teacher-taught required and elective courses;
- teacher discussion entries;
- public learning-note activity from demo runtime activity.

No committed seed-data expansion was required for this round. Local Playwright screenshots were captured from a fresh `.agent-run` SQLite database with `INIT_DEFAULT_DATA=true`.

---

## 6. Recent Posts Validation Added

Targeted backend tests were added / expanded in:

- `tests/backend/recent_posts/test_recent_posts_api.py`

The tests cover:

- `/api/recent-posts/me` sorted feed behavior;
- `kind=material`, `kind=homework`, and `kind=course` filters;
- teacher feeds including homework and course items;
- link target payload types matching the link-card target types;
- hidden private notes;
- LLM assistant comments excluded;
- same-course and outsider student visibility filtering;
- admin not bypassing private note visibility.

Current targeted validation for this follow-up round:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\backend\recent_posts\test_recent_posts_api.py -q
```

Result:

- `11 passed`

```powershell
.\.venv\Scripts\python.exe -m py_compile apps\backend\courseeval_backend\api\routers\recent_posts.py apps\backend\courseeval_backend\api\schemas.py
```

Result:

- passed

```powershell
cd apps\web\admin
npm.cmd run build
```

Result:

- passed, with the existing Vite large chunk warning.

Local browser validation:

- a local ignored Playwright helper under `.agent-run/` started the backend with `INIT_DEFAULT_DATA=true`, launched the admin SPA, logged in as `teacher / 111111`, opened `/recent-posts/me`, exercised the `homework` filter, and captured desktop/mobile screenshots.
- screenshots remain local under `.agent-run/screenshots/` and are intentionally not committed.

---

## 7. Remaining Risks / Follow-Ups

- The diff selector still recommends broader targets when router registration / shared FastAPI surfaces are touched. This handoff records the targeted validation actually run for recent-posts behavior; a release gate should still include the repository's broader backend and Playwright profiles.
- The recent-posts query currently aggregates candidate rows and then filters in Python through existing permission/link resolvers. This is conservative for correctness and acceptable for the current page-size capped surface, but a later high-volume deployment may want DB-side prefiltering per viewer role.
- The admin learning-note route decision was resolved pragmatically by allowing admin deep links to visible public notes while preserving private-note backend denial.

---

## 8. Final State At Handoff

Current branch/worktree state for this handoff line:

- branch: `cursor/repository-normalization`
- `最近发表` is implemented and aligned with linkable object types;
- default demo data demonstrates homework, material, course, and discussion items in the feed;
- no known unresolved failures in the targeted recent-posts validation listed above;
- local screenshots are stored in `.agent-run/screenshots/` and should not be committed.

This handoff should stay with the current branch so future agents do not restart the recent-posts product discussion from the earlier comments-only proposal.
