# Discussion Link Cards Handoff

## Status

- Active handoff: **in-progress feature work** on structured internal link cards
  inside discussion/comment surfaces.
- Branch: `cursor/repository-normalization`
- The user interrupted this round because of quota limits and explicitly asked
  for a careful committed handoff plus a commit of the in-progress work.

## User-Aligned Requirements

These requirements were explicitly confirmed with the user in this thread and
 should be treated as the current product direction unless the user changes
 them later:

1. Support **all current discussion surfaces**, not only one:
   - homework discussions
   - material discussions
   - learning-note discussions
2. Allow **all current authenticated roles on those surfaces** to insert links.
3. Link targets may be chosen from **anything the current user can already
   see**; cross-course is allowed if visible.
4. A single comment may contain **multiple** linked targets.
5. Mobile only needs **basic usable adaptation**, not a full design-heavy
   mobile workflow in the first pass.

The implementation assumption for this round was:

- links are stored as **structured metadata attachments**, not pasted raw URLs;
- the UI uses a picker + compact cards, not freeform URL entry;
- post-send editing of existing comments was **not** added in this round
  because the current discussion surfaces do not already expose message-edit
  capability.

## What Was Implemented

### Backend

The backend now has a shared structured-link path for both course discussions
and learning-note discussions.

Files changed:

- `apps/backend/courseeval_backend/domains/discussion_links.py`
  - new shared helper module for:
    - normalizing `linked_targets`
    - validating target visibility at create time
    - expanding stored targets into viewer-specific card payloads
    - searching visible targets for the picker
- `apps/backend/courseeval_backend/db/models.py`
  - added `linked_targets` JSON columns to:
    - `CourseDiscussionEntry`
    - `LearningNoteDiscussionEntry`
- `apps/backend/courseeval_backend/bootstrap.py`
  - added additive schema updates for those new JSON columns
- `apps/backend/courseeval_backend/api/schemas.py`
  - added:
    - `DiscussionLinkedTargetInput`
    - `DiscussionLinkedTargetResponse`
    - `DiscussionLinkTargetSearchResponse`
  - extended:
    - `CourseDiscussionCreate`
    - `CourseDiscussionEntryResponse`
    - `LearningNoteDiscussionCreate`
    - `LearningNoteDiscussionEntryResponse`
- `apps/backend/courseeval_backend/api/routers/discussions.py`
  - new `GET /api/discussions/link-targets`
  - course discussion create/list now round-trip `linked_targets`
- `apps/backend/courseeval_backend/api/routers/learning_notes.py`
  - note discussion create/list now round-trip `linked_targets`
- `apps/backend/courseeval_backend/llm_discussion.py`
  - assistant-generated discussion rows now set `linked_targets=[]`
- `apps/backend/courseeval_backend/domains/seed/demo.py`
  - seeded discussion rows now set `linked_targets=[]`

Current backend behavior:

- create endpoints accept `linked_targets: [{target_type, target_id}, ...]`
- supported target types are:
  - `homework`
  - `material`
  - `learning_note`
- create-time validation checks the caller can currently access every target
- stored payload is lightweight pair data only
- list responses expand that into card metadata:
  - `target_label`
  - `title`
  - `subject_id` / `subject_name`
  - `class_id` / `class_name` where relevant
  - `secondary_text`
  - `available`
- if a target later becomes inaccessible or deleted, the response degrades to
  an unavailable card instead of failing the whole discussion response

### Frontend

The admin SPA now has a shared picker + card layer wired into both discussion
entry points.

Files changed:

- `apps/web/admin/src/api/index.js`
  - added `api.discussions.searchTargets(...)`
- `apps/web/admin/src/components/DiscussionLinkTargetPicker.vue`
  - new picker dialog with:
    - type tabs
    - title search
    - add button
- `apps/web/admin/src/components/DiscussionLinkedTargetCards.vue`
  - new compact card renderer
- `apps/web/admin/src/utils/discussionLinkTargets.js`
  - shared helpers for:
    - card dedupe key
    - switching `selectedCourse` before navigation
    - resolving target routes
- `apps/web/admin/src/components/CourseDiscussionPanel.vue`
  - course discussion composer can now attach multiple link cards
  - persisted discussion rows render those cards
  - clicking a card navigates to the target
- `apps/web/admin/src/views/LearningNotes.vue`
  - note discussion composer can now attach multiple link cards
  - persisted note discussion rows render those cards
  - clicking a note link can route to `/learning-notes?note=<id>`
  - route query handling now attempts to open a linked note by id

Current UX shape:

- picker is **type-tab + search**, not a heavy multi-step stepper
- selected links are shown as removable draft cards before submit
- saved links show as compact cards under the discussion body
- navigation tries to switch the SPA course context first when the target has a
  `subject_id`

## Important Constraints And Known Gaps

These are the main things the next agent must understand before continuing:

1. **Existing discussion messages are still immutable after send.**
   - This round did not add edit/update APIs for either discussion family.
   - If the product now requires editing existing message links, that is a
     follow-up feature, not a bug in this patch.

2. **The picker searches only by title right now.**
   - It does not yet expose richer filters like chapter/category/semester.
   - That was an intentional simplification for the first pass.

3. **Cross-viewer availability can differ.**
   - Because the rule is “creator may link anything they can see”, one user can
     attach a target that another viewer cannot open later.
   - The backend intentionally serializes those as unavailable cards rather than
     leaking the original hidden title.
   - If product wants “only link targets visible to the whole thread audience,”
     that is a policy change and needs backend rule changes.

4. **Admin note-link navigation is still awkward by existing route policy.**
   - `LearningNotes` remains hidden from admins by existing route guards.
   - This is acceptable for now because the feature surface was historically
     teacher/student-focused, but it is a known mismatch with the user's
     “all roles” wording.

5. **No dedicated new regression tests for link-card semantics were added yet.**
   - Existing discussion and learning-note suites still pass.
   - The next agent should add explicit tests for:
     - picker search endpoint
     - create/list `linked_targets`
     - unavailable-card fallback behavior

## Validation Run In This Round

### Passed

1. Python syntax check:

```powershell
python -m py_compile apps\backend\courseeval_backend\domains\discussion_links.py apps\backend\courseeval_backend\api\routers\discussions.py apps\backend\courseeval_backend\api\routers\learning_notes.py apps\backend\courseeval_backend\api\schemas.py apps\backend\courseeval_backend\llm_discussion.py apps\backend\courseeval_backend\bootstrap.py apps\backend\courseeval_backend\db\models.py
```

2. Admin frontend production build:

```powershell
cd apps\web\admin
npm.cmd run build
```

3. Existing course-discussion behavior suite:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\behavior\test_discussion_api_behavior.py -q
```

- Result: `12 passed`

4. Existing learning-notes backend suite:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\backend\learning_notes\test_learning_notes_api.py -q
```

- Result: `11 passed`

5. Selector recommendation snapshot:

```powershell
.\.venv\Scripts\python.exe ops\scripts\dev\select_validation_targets.py --worktree
```

- Result: `non_full_validation.status = not_sufficient`
- Escalation reason: selector recommends `full.pytest.postgres` because this
  diff touches ORM/bootstrap/shared backend discussion surfaces.

### Environment note

- System `python` at `C:\Python314\python.exe` did **not** have `pytest`
  installed.
- Validation therefore used the repository `.venv` for pytest.

## Recommended Next Steps

1. Add explicit backend tests for the new link-card behavior.
   - Suggested locations:
     - `tests/behavior/test_discussion_api_behavior.py`
     - `tests/backend/learning_notes/test_learning_notes_api.py`
   - Cover:
     - `GET /api/discussions/link-targets`
     - discussion create/list with `linked_targets`
     - inaccessible/deleted target fallback

2. Decide whether post-send editing is actually required.
   - If yes, add update routes and UI for both discussion families together.

3. Decide whether thread-level audience constraints are needed.
   - Current rule is per-caller visibility only.
   - If product wants “no cards that become unavailable to other viewers,”
     change the policy before extending the feature further.

4. If admin really must navigate to learning-note targets, revisit admin route
   hiding for `/learning-notes` or add an admin-safe read-only deep link.

5. Consider a small documentation follow-up.
   - `docs/architecture/CORE_BUSINESS_FLOWS.md` was partially updated in this
     round, but the next agent may want to add a fuller note specifically under
     the course-discussion section once the feature is considered settled.

## Files The Next Agent Must Read First

- `AGENTS.md`
- `docs/README.md`
- `docs/reference/PERMISSIONS_AND_SECURITY_BOUNDARIES.md`
- `docs/architecture/CORE_BUSINESS_FLOWS.md`
- `apps/backend/courseeval_backend/domains/discussion_links.py`
- `apps/backend/courseeval_backend/api/routers/discussions.py`
- `apps/backend/courseeval_backend/api/routers/learning_notes.py`
- `apps/web/admin/src/components/CourseDiscussionPanel.vue`
- `apps/web/admin/src/views/LearningNotes.vue`
- `apps/web/admin/src/components/DiscussionLinkTargetPicker.vue`
- `apps/web/admin/src/components/DiscussionLinkedTargetCards.vue`
- `apps/web/admin/src/utils/discussionLinkTargets.js`

## Do Not Revert

- The new `linked_targets` JSON fields on both discussion models.
- The viewer-specific unavailable-card fallback in
  `domains/discussion_links.py`.
- The route-query note opening behavior in `LearningNotes.vue`.
- The course-context switch before link navigation in
  `src/utils/discussionLinkTargets.js`.

Those changes are the backbone of the current implementation direction.
