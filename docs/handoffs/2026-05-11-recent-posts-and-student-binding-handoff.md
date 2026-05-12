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
- `GET /api/recent-posts/me/grouped`
- `GET /api/recent-posts/users/{user_id}/grouped`

Supported `kind` values:

- `all`
- `comment`
- `note`
- `material`
- `homework`
- `course`

Grouped response behavior:

- groups are ordered as `course`, `homework`, `material`, `note`, `comment`;
- empty groups are omitted, so student pages normally show only note/discussion/material groups when those are the only visible authored kinds;
- each group returns `total`, `latest_created_at`, and an initial `data` slice controlled by `group_limit`;
- the frontend can load more rows for a group through the existing list endpoint with `kind`, `page`, and `page_size`.

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

The recent-posts page is organized by link type instead of a single mixed timeline:

- non-empty groups render as collapsible sections;
- default group order is `课程`, `作业`, `资料`, `笔记`, `讨论`;
- each group starts expanded and initially shows three rows;
- groups with more rows expose `查看更多`;
- the date range filter remains at the top and applies across all groups.

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
- grouped feed ordering and per-group limits;
- `kind=material`, `kind=homework`, and `kind=course` filters;
- teacher feeds including homework and course items;
- link target payload types matching the link-card target types;
- hidden private notes;
- LLM assistant comments excluded;
- same-course and outsider student visibility filtering for both list and grouped endpoints;
- admin not bypassing private note visibility.

Current targeted validation for this follow-up round:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\backend\recent_posts\test_recent_posts_api.py -q
```

Result:

- `13 passed`

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

- a local ignored Playwright helper under `.agent-run/` started the backend with `INIT_DEFAULT_DATA=true`, launched the admin SPA, logged in as `teacher / 111111`, opened `/recent-posts/me`, captured the grouped desktop/mobile UI, and exercised group collapse.
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
- default demo data demonstrates homework, material, course, and discussion groups in the feed;
- no known unresolved failures in the targeted recent-posts validation listed above;
- local screenshots are stored in `.agent-run/screenshots/` and should not be committed.

This handoff should stay with the current branch so future agents do not restart the recent-posts product discussion from the earlier comments-only proposal.

---

## 9. 2026-05-12 Link-Oriented Follow-Up

This section records the next round of work on the same branch. The user summarized the product direction as two main link-oriented lines plus several adjacent workflow improvements:

1. discussion areas should support structured link cards, and clicking an author's avatar / viewing `近期发表` should expose linkable authored objects;
2. other workflows should reuse that same permission-aware link model, including teacher views of student homework and teacher placement of homework links inside the course directory.

The implementation in this round intentionally kept `近期发表` and the discussion linkable object set aligned. If an object cannot be represented as a normal internal link target that the viewer could already open, it should not appear in the feed merely because the feed page exists.

### 9.1 Terminology and Navigation Cleanup

User-facing terminology was normalized during this round:

- `最近发表` was changed to `近期发表` across the admin SPA surfaces touched by the feature.
- `课程资料` was changed to `课程目录` where the UI is presenting the structured course outline / chapter directory rather than a generic file list.
- The left sidebar large brand text is now only `CourseEval`; the smaller subtitle carries the Chinese system description.
- The personal settings label formerly shown as `圆角` was renamed to `界面圆润度`.
- The `近期发表` sidebar/account icon was changed away from the learning-note icon to avoid duplicate visual meaning.

Files involved include:

- `apps/web/admin/src/views/Layout.vue`
- `apps/web/admin/src/router/index.js`
- `apps/web/admin/src/views/RecentPosts.vue`
- `apps/web/admin/src/views/Materials.vue`
- `apps/web/admin/src/views/PersonalSettings.vue`
- `apps/web/admin/src/components/AppearanceStylePanel.vue`
- `apps/web/admin/src/components/DiscussionAuthorAvatar.vue`
- `apps/web/admin/src/views/StudentCourseHome.vue`
- `apps/web/admin/src/views/Subjects.vue`
- `apps/web/admin/src/views/Users.vue`

### 9.2 Link Cards In Discussion Areas

The discussion link-card line remains the base contract for this whole feature family:

- users can attach structured internal link cards to comments;
- target validation happens server-side at creation time;
- target expansion happens again per viewer, so deleted or unauthorized objects degrade to unavailable cards instead of leaking titles or routes;
- the frontend uses one opener utility for supported target types instead of ad hoc route pushes.

The relevant implemented target family now includes the same broad object set used by `近期发表`:

- discussion entries;
- courses;
- homework;
- course materials;
- learning notes.

Important implementation intent:

- Link-card permission checks are the baseline. A later feature should not add a feed/list/card that can reveal a title or route the viewer could not obtain through the normal link resolver.
- Discussion cards are deliberately object references, not copied content. They should stay valid through route changes as long as the target resolver remains current.

### 9.3 Avatar and `近期发表`

Clicking a discussion author's avatar now opens that user's `近期发表` page instead of being only decorative identity UI. The sidebar/account area also exposes the current user's `近期发表` entry.

Current feed semantics:

- The feed is permission-filtered for the current viewer.
- The feed object set is aligned with the linkable target set.
- Groups are organized by link target type instead of one flat mixed timeline.
- Groups are collapsible.
- The feed defaults to newest authored/published items.
- Sorting/filtering remains intentionally conservative and page-size capped.

Current entry points confirmed in this workstream:

- current user's own `近期发表` from the account/sidebar area;
- another user's `近期发表` from discussion author avatars;
- admin user-management table action for user feeds.

Known product interpretation:

- "Published" for this feature currently means an authored object with a linkable product destination and a visible timestamp, not every audit/activity row.
- Homework submissions are not currently part of the general `近期发表` object set, because they are not the same kind of public/linkable authored object as homework assignments, notes, materials, courses, and comments.
- Teacher-specific student homework visibility is handled through course/student homework workflows, not by making all submissions globally appear in `近期发表`.

### 9.4 Teacher Views of Student Homework

The user asked for teacher affordances such as clicking a student's avatar to see the student's homework publishing/submission status. The current implementation partially satisfies the teacher need but does not yet fully unify all entry points.

Current state:

- Course teachers can access per-student homework status for students in their taught courses through the teacher/course homework workflows.
- `近期发表` and avatar flows are centered on linkable authored objects. They do not fully replace a teacher's operational view of a student's homework submissions.
- The earlier product decision remains: a course teacher may see each student's homework publishing/submission status only for students in courses the teacher teaches.

Important gap:

- Clicking a student avatar and clicking a roster row are not yet guaranteed to expose the exact same teacher actions.
- The roster/student table should eventually provide the same useful actions as an avatar hover/click:
  - view the student's `近期发表` where permission allows;
  - view that student's homework/submission status for the selected course;
  - avoid showing cross-course or cross-teacher data.

Recommended follow-up:

- Add a shared student action menu component or helper used by both `DiscussionAuthorAvatar.vue` and roster/student list rows.
- Gate the homework-status action with server-side course-teacher permission, not only by hiding the button.
- Add tests for teacher A seeing homework status for students in teacher A's course while teacher B cannot access the same status unless they also teach that course.

### 9.5 Course Directory Homework Links

The course directory now supports placing homework links into chapters. This is the main new "other workflow" shipped in the 2026-05-12 round.

Backend implementation:

- Added ORM model `CourseMaterialHomeworkLink`.
- Added idempotent schema DDL in `bootstrap.ensure_schema_updates()`.
- Added API schemas:
  - `CourseMaterialHomeworkLinkResponse`
  - `CourseMaterialHomeworkLinkCreate`
  - `CourseMaterialChapterNode.homework_links`
- Extended `GET /api/material-chapters/tree` to include `homework_links`.
- Added:
  - `POST /api/material-chapters/homework-links?subject_id=...`
  - `DELETE /api/material-chapters/homework-links/{link_id}?subject_id=...`
- Server-side permission rules:
  - caller must have access to the course;
  - mutation is restricted to the course instructor or admin;
  - chapter and homework must belong to the same subject/course.
- Cleanup was added so deleting chapters or homework rows removes course-directory homework links.

Frontend implementation:

- `apps/web/admin/src/api/index.js` now exposes add/remove homework-link helpers.
- `apps/web/admin/src/views/Materials.vue` now renders an `关联作业` panel for the selected chapter.
- Teachers/admin instructors can click `添加作业链接`.
- The picker searches `api.discussions.searchTargets({ target_type: 'homework', preferred_subject_id, q, limit: 30 })`.
- Picker rows are client-filtered to the current course and already-linked homework is disabled.
- Linked homework cards open through the same discussion-link target opener utility.
- A UI issue found during screenshot validation was fixed: chapter label click now selects a chapter, while double-click opens the reading page. This makes chapter management and homework-link placement usable.
- Mobile overflow was fixed for teacher chapter action buttons in the course directory tree.

Default data:

- Demo seed now ensures at least one course-directory chapter links to a homework item, so `INIT_DEFAULT_DATA=true` visibly demonstrates the feature.
- The default `teacher / 111111` account can see the linked homework in the `数据挖掘` course directory.

Screenshots from this round were captured locally under `.agent-run/screenshots/` and must remain uncommitted:

- `material-homework-link-default-data.png`
- `material-homework-link-picker-default-data.png`
- `material-homework-link-mobile-default-data.png`

### 9.6 Role Coverage Concerns

The current implementation is permission-conscious but not yet product-complete across every role-specific surface.

Concerns to carry forward:

- Student, teacher, admin, class-teacher, and parent-like external views do not all necessarily have the same UX entry points for `近期发表` or link opening, even when backend permissions would allow a subset of the data.
- Admin can reach user feeds from user management, but admin does not bypass private-note visibility. This is correct for privacy, but product copy should make the limitation understandable if admins expect "see everything".
- Teacher affordances are strongest in discussion avatar and course directory flows, but roster/table surfaces are not fully harmonized with those avatar actions.
- Student-facing navigation uses the same terminology for `课程目录`, but the course-directory homework-link management affordance is teacher/admin-only. Student display should continue to be validated whenever new link targets are added to directory nodes.
- Class teachers may have course visibility through class/course bindings. Any future class-teacher recent-posts or student-homework action must be checked carefully against `subject_class_links` and `CourseEnrollment`, not against legacy `Subject.class_id` fallbacks.
- Parent portal behavior was not part of this round. Do not assume parent users can or should open the same link targets unless a separate parent-link permission model is designed.

### 9.7 Functional Gaps and Suggested Next Steps

High-priority gaps:

- Roster/student rows should expose the same `近期发表` and course-scoped homework-status affordances as student avatars.
- The student action menu should be centralized so future UI entry points do not drift.
- There should be an explicit teacher-facing page or panel for "this student's homework status in this course" if the current scattered entry points remain hard to discover.
- `近期发表` currently filters candidates in Python after collecting candidate rows. This is conservative and correct for page-size-capped use, but could become expensive at higher volume.
- Course-directory homework links use the link-target search endpoint and then client-side course filtering. The backend still validates same-course ownership on mutation, but a future API could expose a course-scoped homework picker directly to reduce client work and ambiguity.
- The feed and link-card target set should be audited whenever a new link type is added. Otherwise `近期发表` and discussion link cards can drift again.

Testing gaps to consider:

- More role-matrix browser coverage for `近期发表`: teacher viewing student, student viewing teacher, admin viewing teacher, class teacher viewing class student, outsider teacher denied.
- Browser tests for roster-row action parity with avatar actions once implemented.
- Browser tests for students opening course-directory homework links, not only teachers managing them.
- PostgreSQL-backed validation for the new `course_material_homework_links` table and cleanup behavior.
- Full admin Playwright remains a high-cost selector recommendation after these broad frontend/router changes.

### 9.8 Validation From The 2026-05-12 Round

Observed passing validation:

```powershell
git diff --check
```

```powershell
python ops\scripts\dev\check_schema_governance.py
python ops\scripts\dev\check_api_surface_governance.py
```

```powershell
.\.venv\Scripts\python.exe -m py_compile apps\backend\courseeval_backend\db\models.py apps\backend\courseeval_backend\bootstrap.py apps\backend\courseeval_backend\api\schemas.py apps\backend\courseeval_backend\api\routers\material_chapters.py apps\backend\courseeval_backend\api\routers\subjects.py apps\backend\courseeval_backend\domains\homework\cleanup.py apps\backend\courseeval_backend\domains\seed\demo.py
```

```powershell
.\.venv\Scripts\python.exe -m pytest tests\behavior\test_material_chapters_notifications_homework_flow.py::test_ui10_teacher_links_homework_into_chapter_and_student_reads_link tests\behavior\test_material_chapters_notifications_homework_flow.py::test_ui11_student_and_foreign_teacher_cannot_manage_homework_links tests\backend\e2e_dev\test_demo_course_seed.py::test_demo_seed_creates_teacher_students_course_homework -q
```

Result:

- `3 passed`
- only existing Pydantic deprecation warnings were observed.

```powershell
cd apps\web\admin
npm.cmd run build
```

Result:

- passed;
- existing Vite CJS deprecation and large chunk warnings remain.

```powershell
cd apps\web\admin
$env:E2E_USE_REAL_WORKER='false'; npm.cmd run test:e2e:external -- e2e-course-ui-markdown-reader.spec.js --project=chromium
```

Result:

- `12 passed`

```powershell
cd apps\web\admin
$env:E2E_USE_REAL_WORKER='false'; npm.cmd run test:e2e:external -- ui-materials-outline-regression.spec.js --project=chromium
```

Result:

- `1 passed`

Validation caveat:

- A first attempt to run two Playwright external runners in parallel failed because both runners defaulted to the same ports and SQLite database. One run saw `ERR_CONNECTION_REFUSED` after Vite moved to another port while the test base URL still expected the default port; the other saw SQLite `database is locked`. The same suites passed when rerun serially. Treat this as an operator/harness concurrency pitfall, not a product regression.
- The selector still reported `not_sufficient` because schema/router/frontend changes recommend high-cost broader targets: `admin.e2e.full` and `full.pytest.postgres`. Those were not run in this round, so the current evidence is targeted validation, not release-level full validation.

### 9.9 Current Worktree Notes

At the time this section was written:

- branch remains `cursor/repository-normalization`;
- `error.txt` is untracked and should not be committed unless the user explicitly asks;
- `.agent-run/` contains local scripts/screenshots/logs and must remain uncommitted;
- the new course-directory homework-link implementation is present in the worktree but had not yet been committed in this latest round.
