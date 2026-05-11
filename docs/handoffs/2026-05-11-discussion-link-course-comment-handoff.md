# Structured Discussion Link Cards: Course + Comment Targets Handoff

Date: 2026-05-11

Branch: `cursor/repository-normalization`

Status: implemented and partially validated. This was interrupted before the final Playwright run, so treat the browser E2E spec as written but not yet proven green in Chromium.

## User Request

The user asked to extend the existing structured discussion link-card feature so users can link to:

- comments that are visible to the current user;
- courses that the current user can see, participate in, or teach;
- with full UX, deep links, screenshots, difficult tests, and bug fixing until green.

The user then interrupted and asked for a detailed handoff and local commit without pushing.

## Functional Design Implemented

Two new link target types were added:

- `course`
- `discussion_entry`

Existing target types remain:

- `homework`
- `material`
- `learning_note`

The implementation keeps the existing structured metadata model. It does not paste or parse raw URLs.

### Visibility Model

Creation-time validation still validates every linked target against the current user:

- `course`: uses course access rules via `ensure_course_access_http`.
- course discussion comments: visible only if the user can access the underlying course discussion thread.
- learning-note discussion comments: visible only if the user can read the learning note.

View-time serialization re-resolves every saved target for the viewer:

- visible targets render normal cards;
- invisible or deleted targets degrade to unavailable cards;
- unavailable comment cards do not expose original comment body/title.

### Comment ID Strategy

Course discussion entries and learning-note discussion entries are stored in different tables, but link cards expose a single public target type: `discussion_entry`.

Because both tables can have overlapping integer primary keys, learning-note discussion entries are exposed as:

```text
LEARNING_NOTE_DISCUSSION_TARGET_ID_OFFSET + row.id
```

Current offset:

```text
1_000_000_000
```

This constant lives in:

- `apps/backend/courseeval_backend/domains/discussion_links.py`

Course discussion entries keep their raw `course_discussion_entries.id`.

### Locator Endpoints

Deep linking to comments requires page calculation, so two locator endpoints were added:

- `GET /api/discussions/entries/{entry_id}/locator`
- `GET /api/learning-notes/discussion-entries/{entry_target_id}/locator`

They return enough routing state for the frontend to navigate to the thread and set query params:

- course comments:
  - `discussion_family`
  - `entry_id`
  - `thread_target_type`
  - `thread_target_id`
  - `subject_id`
  - `class_id`
  - `page`
  - `page_size`
- learning-note comments:
  - `discussion_family`
  - `entry_id`
  - offset `target_id`
  - `note_id`
  - `page`
  - `page_size`

Page calculation uses the same ascending `(created_at, id)` order as list endpoints.

## Backend Files Changed

### `apps/backend/courseeval_backend/domains/discussion_links.py`

Main shared implementation.

Important additions:

- `DiscussionLinkTargetType` now includes `course` and `discussion_entry`.
- `LINKABLE_TARGET_TYPES` now includes `course` and `discussion_entry`.
- `LEARNING_NOTE_DISCUSSION_TARGET_ID_OFFSET = 1_000_000_000`.
- `DiscussionLinkedTargetResponse` payloads can include `meta`.
- Added resolvers:
  - `_resolve_course_target`
  - `_resolve_course_discussion_entry_target`
  - `_resolve_learning_note_discussion_entry_target`
  - `_resolve_discussion_entry_target`
- Added search branches for:
  - `course`
  - `discussion_entry`

Important behavior:

- `discussion_entry` search aggregates visible course comments first, then visible learning-note comments.
- Search uses body text matching for comments.
- Comment card titles are short excerpts prefixed by author display name.
- Private/inaccessible comments return unavailable fallback when serialized for a viewer.

Potential follow-up:

- `discussion_entry` search currently loads visible note ids using `_visible_note_query(...).all()`. This is acceptable for current product scale/tests but can be optimized later if note volume becomes large.

### `apps/backend/courseeval_backend/api/schemas.py`

Updated:

- `DiscussionLinkedTargetInput.target_type`
- `DiscussionLinkedTargetResponse.target_type`
- Added optional `meta: dict[str, Any] | None` to `DiscussionLinkedTargetResponse`.

### `apps/backend/courseeval_backend/api/routers/discussions.py`

Updated:

- `/api/discussions/link-targets` accepts `course` and `discussion_entry`.
- Added course-discussion entry locator endpoint:
  - `/api/discussions/entries/{entry_id}/locator`

### `apps/backend/courseeval_backend/api/routers/learning_notes.py`

Updated:

- imports `LEARNING_NOTE_DISCUSSION_TARGET_ID_OFFSET`.
- Added learning-note discussion entry locator endpoint:
  - `/api/learning-notes/discussion-entries/{entry_target_id}/locator`

## Frontend Files Changed

### `apps/web/admin/src/api/index.js`

Added:

- `api.discussions.locateEntry(id, params)`
- `api.learningNotes.locateDiscussionEntry(id, params)`

### `apps/web/admin/src/utils/discussionLinkTargets.js`

Click behavior now supports:

- `course`
  - switches selected course using existing course selection logic;
  - student route: `StudentCourseHome`;
  - non-student route currently goes to `Students` after course switch.
- `discussion_entry`
  - learning-note comments call `api.learningNotes.locateDiscussionEntry`;
  - course comments call `api.discussions.locateEntry`;
  - routes to:
    - `LearningNotes?note=...&discussion_entry=...&discussion_page=...`
    - `MaterialRead/:id?discussion_entry=...&discussion_page=...`
    - `HomeworkSubmit/:id?discussion_entry=...&discussion_page=...`
    - `HomeworkSubmissions/:id?discussion_entry=...&discussion_page=...`

Potential follow-up:

- Non-student course-card routing is conservative. It currently switches course context and opens `Students`. Product may prefer a future teacher course-home route if one exists later.

### `apps/web/admin/src/components/DiscussionLinkTargetPicker.vue`

Picker now has five tabs:

- homework
- material
- learning_note
- course
- discussion_entry

Mobile radio grid changed from 3 columns to 5 columns.

### `apps/web/admin/src/components/CourseDiscussionPanel.vue`

Added:

- `useRoute`.
- query support for:
  - `discussion_entry`
  - `discussion_page`
- page auto-load from `discussion_page`.
- scroll + transient highlight for `[data-discussion-entry-id="..."]`.
- `.discussion-row--highlighted` style.

Important detail:

- The target row uses `:data-discussion-entry-id="row.id"`.
- Highlight clears after roughly 3.2 seconds.

### `apps/web/admin/src/views/LearningNotes.vue`

Added:

- query support for:
  - `note`
  - `discussion_entry`
  - `discussion_page`
- `discussionPage` state.
- scroll + transient highlight for note discussion rows.
- `.discussion-row--highlighted` style.

Important detail:

- Offset learning-note entry ids in query are normalized back to raw row ids for DOM lookup.

### `apps/web/admin/src/components/DiscussionLinkedTargetCards.vue`

This file already had substantial pre-existing changes in the worktree before this turn from the previous link-card UI pass:

- card structure avoids nested buttons;
- saved/draft cards have compact UI;
- unavailable cards render disabled;
- card radius kept at 8px or below.

This commit includes those existing changes because the user asked to commit the whole link-card batch.

## Tests Added / Extended

### Backend Discussion Tests

File:

- `tests/behavior/test_discussion_api_behavior.py`

Added difficult coverage for:

- course target search and round trip;
- course discussion comment target search and round trip;
- comment card `meta` shape;
- comment locator page calculation with `page_size=5`;
- invisible course comment search returning no rows for an unrelated teacher;
- existing link-card tests for dedupe, limit, unavailable fallback.

### Backend Learning Notes Tests

File:

- `tests/backend/learning_notes/test_learning_notes_api.py`

Added difficult coverage for:

- learning-note discussion comment target search;
- offset target id behavior;
- note comment target round trip;
- learning-note comment locator page calculation with `page_size=20`;
- private note comment card degradation for a public viewer without leaking the secret comment body.

### Playwright E2E

File:

- `tests/e2e/web-admin/e2e-discussion-link-cards.spec.js`

This is a new screenshot-oriented spec. It already existed as untracked work from the previous pass and was extended in this turn.

Current coverage in the spec:

1. Existing screenshot flow:
   - opens discussion composer from homework submit;
   - opens picker;
   - screenshots picker desktop;
   - attaches a visible target;
   - screenshots draft card desktop;
   - submits;
   - screenshots saved card desktop;
   - reloads mobile;
   - screenshots saved card mobile;
   - opens composer mobile;
   - screenshots draft card mobile.

2. New course + comment link flow:
   - uses API to create a target comment;
   - uses API to create another comment linking both:
     - the course;
     - the target comment;
   - screenshots saved course/comment cards;
   - clicks course card and expects `/course-home`;
   - screenshots opened course page;
   - clicks comment card and expects `discussion_entry=...`;
   - asserts target row is visible and has `discussion-row--highlighted`;
   - screenshots highlighted comment desktop;
   - reloads mobile deep link and screenshots highlighted comment mobile.

Important: this Playwright spec was edited but not run before interruption. It may need selector or seed-shape fixes.

Potential issue to check first:

- The new E2E uses `s.class_id_1`, `s.course_required_id`, and `s.homework_id`, which exist in current `scenario.json` shape.
- It imports `apiJson`, `login`, and `obtainAccessToken` from `future-advanced-coverage-helpers.cjs`.

## Validation Already Run

These commands passed in this turn:

```powershell
.\.venv\Scripts\python.exe -m py_compile apps\backend\courseeval_backend\domains\discussion_links.py apps\backend\courseeval_backend\api\routers\discussions.py apps\backend\courseeval_backend\api\routers\learning_notes.py apps\backend\courseeval_backend\api\schemas.py
```

```powershell
.\.venv\Scripts\python.exe -m pytest tests\behavior\test_discussion_api_behavior.py -q
```

Result:

```text
16 passed
```

```powershell
.\.venv\Scripts\python.exe -m pytest tests\backend\learning_notes\test_learning_notes_api.py -q
```

Result:

```text
15 passed
```

```powershell
npm.cmd run build
```

Run from:

```text
apps/web/admin
```

Result:

```text
built successfully
```

Only existing non-blocking warnings appeared:

- Vite CJS Node API deprecation;
- large chunk-size warning.

## Validation Not Yet Run

The final Playwright run was not started before user interruption.

Recommended next command:

```powershell
.\.venv\Scripts\python.exe ops\scripts\dev\playwright_preflight.py --json
```

Then from `apps/web/admin`:

```powershell
node scripts\playwright-external-runner.cjs e2e-discussion-link-cards.spec.js --project=chromium
```

Use the external runner. The docs warn that the direct Playwright managed `webServer` path can hang or fail on Windows teardown.

After the run, collect screenshot artifacts from:

```text
apps/web/admin/test-results/
```

Expected new screenshot attachment names include:

- `discussion-link-picker-desktop`
- `discussion-link-draft-desktop`
- `discussion-link-saved-desktop`
- `discussion-link-saved-mobile`
- `discussion-link-draft-mobile`
- `discussion-link-course-comment-saved-desktop`
- `discussion-link-course-opened-desktop`
- `discussion-link-comment-highlight-desktop`
- `discussion-link-comment-highlight-mobile`

## Known Risks / Things To Review Next

1. Playwright spec may need adjustment:
   - The second test is newly written and not run.
   - Check route URL expectation for `/homework/:id/submit?...discussion_entry=...`.
   - Check that the highlight is still present long enough for assertion and screenshot.

2. Course card routing for teachers/class teachers:
   - Current behavior switches selected course and routes non-students to `Students`.
   - There is no obvious teacher course-home route in the router.
   - If product expects a richer course landing page for teachers, implement that separately.

3. Learning-note discussion IDs:
   - Offset strategy avoids cross-table id collisions without schema migration.
   - Future API docs should mention that `discussion_entry` ids are opaque and clients must not assume raw database ids.

4. Comment search performance:
   - Current implementation is fine for present tests and product scale.
   - It can be optimized if note/comment volume grows.

5. Existing mojibake display:
   - PowerShell output shows many Chinese strings as mojibake in existing files.
   - Do not infer file corruption solely from terminal rendering.
   - Use repo encoding helpers if inspecting exact Chinese text.

## Suggested Resume Checklist

1. Run `git status --short` to confirm this commit is the only local branch head change.
2. Run Playwright preflight.
3. Run the targeted Playwright spec through the external runner.
4. If Playwright fails:
   - first classify environment vs product failure using `docs/development/TEST_EXECUTION_PITFALLS.md`;
   - then fix selectors/route behavior as needed.
5. If Playwright passes, report screenshot artifact paths for user acceptance.
6. Run selector:

```powershell
.\.venv\Scripts\python.exe ops\scripts\dev\select_validation_targets.py --worktree
```

Expect it may still recommend broad/full PostgreSQL validation because behavior tests changed. That target was not run in this interrupted pass.

