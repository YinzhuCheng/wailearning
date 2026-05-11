# Recent Posts + Student Binding Handoff

Date: 2026-05-11

Branch: `cursor/repository-normalization`

Status:

- the structured discussion link-card line is functionally complete for this round and its targeted Playwright spec has passed locally;
- the student roster/account strong-binding refactor described below is implemented and validated locally;
- the new `最近发表` feature is **not** implemented yet; only requirement alignment and architecture discussion were completed.

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

## 5. Recent Posts Feature: Requirement Alignment Summary

The user introduced a new feature request, but implementation did **not** start in this round. The following is the latest requirement understanding.

### Proposed feature meaning

`最近发表` should mean a unified feed of **discussion comments**, not every possible authored object.

Planned scope for first implementation:

- course discussion comments
- learning-note discussion comments

Out of scope for first implementation unless the user later expands it:

- homework submission bodies
- learning-note document bodies
- notifications
- materials
- generic audit/activity feed

### Requested entry points

1. current user can open their own recent posts from personal settings;
2. users can click an author's avatar in discussion UI to view that author's recent posts;
3. teachers / class teachers can open a student's recent posts from class roster / related student surfaces;
4. administrators can view recent posts for any user.

### Important product/permission assumptions agreed during discussion

1. Teachers do **not** need a bound class.
   - A `teacher` may teach across multiple classes.
   - This matches current code and docs.
2. `class_teacher` is the class-scoped role.
3. Students should be bound to a class; missing class should be normalized into a temporary class rather than remaining null.
4. The roster/account strong-binding work above is intended to make the roster entry point reliable for this future feature.

---

## 6. Recent Posts: Proposed Technical Shape

This is not implemented yet, but the current recommendation is:

### Backend

Build a unified recent-posts API over:

- `CourseDiscussionEntry`
- `LearningNoteDiscussionEntry`

Likely route family:

- `GET /api/recent-posts/me`
- `GET /api/recent-posts/users/{user_id}`

The feed should:

- aggregate both tables into one ordered stream;
- apply **viewer-specific visibility filtering**;
- expose enough route/deep-link metadata to jump back to the source thread.

### Frontend

Use a dedicated page rather than trying to overload existing discussion pages.

Likely route shape:

- `/recent-posts/me`
- `/recent-posts/users/:userId`

The page should render:

- author header (avatar, name, role, maybe class);
- recent comment items with timestamp, source type, source context, body preview;
- click-through to the original discussion location.

### Reuse from current link-card line

The discussion link-card work already added:

- public `discussion_entry` target ids;
- comment locator endpoints;
- frontend deep-link routing helpers;
- row highlighting in source discussion UIs.

That means `最近发表` can reuse the same deep-linking strategy rather than inventing a second jump protocol.

---

## 7. Recent Posts: Still-To-Align Questions

These points were discussed but not finally resolved in code.

### 7.1 Exact visibility policy

Recommended rule:

- a viewer only sees recent-post items they are already allowed to see in their normal product visibility model.

This avoids leaking existence of hidden/private comments.

Still to confirm explicitly with the user/product:

- should students be allowed to open another student's recent-posts page from an avatar click when they can already see that student in-thread?
- should the page silently omit hidden items, or should it expose some "partially hidden history" indicator?

Current recommendation:

- allow opening the page;
- silently filter inaccessible items;
- do **not** expose hidden counts.

### 7.2 Admin handling for learning-note deep links

Current router behavior still redirects admins away from `/learning-notes`.

This creates a product decision:

1. allow admin read-only access to the learning-notes page/path for deep linking;
2. or let admin view note-discussion recent-posts items in the feed but not jump into the original note thread.

Recommended implementation direction:

- add an admin-safe read-only route/path for learning-note deep linking, because otherwise the feed becomes inconsistent for admin users.

### 7.3 Source identity for roster entry points

Roster surfaces are `Student`-centric, but recent posts should be `User`-centric.

Thanks to the strong-binding work above, the intended product rule can now be:

- roster UI entry resolves `Student -> bound User(role=student)` and opens recent posts by `user_id`.

If a future environment still has legacy drift, that should be treated as repair debt, not as a normal feature branch in the UI.

### 7.4 Whether “recent posts” should stay comments-only forever

Current recommendation:

- start comments-only;
- only expand later if the user explicitly wants a broader authored-activity feed.

Keeping first scope comments-only makes aggregation, permissions, and navigation much simpler.

---

## 8. Recommended Resume Order

When the next agent resumes:

1. Read:
   - `AGENTS.md`
   - this handoff
   - `docs/reference/DATA_MODEL_ESSENTIALS.md`
   - `docs/reference/PERMISSIONS_AND_SECURITY_BOUNDARIES.md`
   - `apps/backend/courseeval_backend/domains/roster/identity.py`
   - `apps/backend/courseeval_backend/domains/roster/reconciliation.py`
   - `apps/backend/courseeval_backend/domains/roster/sync.py`
   - `apps/backend/courseeval_backend/api/routers/users.py`
   - `apps/backend/courseeval_backend/api/routers/students.py`
   - `apps/backend/courseeval_backend/api/routers/auth.py`
2. Decide whether to start `最近发表` implementation immediately or first add a small explicit audit/repair CLI/report around remaining legacy roster drift.
3. If implementing `最近发表`, start with a backend-only unified recent-posts query and permission model before building the page.
4. Only after backend shape is stable, add:
   - personal-settings entry
   - avatar click entry
   - roster/user-management entry
   - frontend recent-posts page
5. If admin must deep-link into learning-note discussion items, resolve the admin route policy before polishing UI.

---

## 9. Final State At Handoff

Current branch/worktree state before commit/push for this handoff:

- branch: `cursor/repository-normalization`
- worktree: modified files listed in `git status --short`
- no known unresolved test failures in the changed surfaces
- `最近发表` remains requirement-aligned only, not implemented

This handoff is intended to be committed together with the strong-binding changes and pushed to the current branch so the next agent can continue from repository state alone.
