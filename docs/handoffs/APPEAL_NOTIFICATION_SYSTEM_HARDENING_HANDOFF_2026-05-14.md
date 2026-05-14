# Appeal Notification System Hardening Handoff

## Scope

This handoff captures the system-oriented repair pass on branch
`cursor/repository-normalization-schema-notifications` for the appeal
notification chain:

- `grade_appeal`
- `score_grade_appeal`
- `appeal_status`
- notification list/detail projection
- deep-link route construction
- frontend action labels and readonly/actionable semantics

The goal of this round was not to keep finding one bug at a time, but to reduce
future drift by introducing shared projection logic and a shared frontend
resolver.

## Branch State

- Branch: `cursor/repository-normalization-schema-notifications`
- Worktree before commit included:
  - backend notification response/serializer changes
  - domain-level homework/score appeal notification rewrites
  - frontend resolver and Vue-page convergence
  - red-team and E2E follow-up tests

## What Was Systematically Repaired

### 1. Backend appeal notification projection was centralized

New file:

- `apps/backend/courseeval_backend/domains/appeal_notifications.py`

This helper now owns:

- normalized status values
- actionable vs readonly status groupings
- title prefix projection:
  - `【已阅】`
  - `【已处理】`
  - `【已拒绝】`
- content status-line projection
- notification-linked appeal status resolution for:
  - `Notification.related_appeal_id -> HomeworkGradeAppeal.status`
  - `Notification.related_score_appeal_id -> ScoreGradeAppeal.status`

This replaced the previous pattern where:

- router code re-queried appeal status inline
- homework notification update logic appended ad hoc text
- score notification update logic hard-coded only the handled path

### 2. NotificationResponse contract was clarified

Files:

- `apps/backend/courseeval_backend/api/schema_defs/notifications.py`
- `apps/backend/courseeval_backend/api/routers/notifications.py`

Changes:

- `NotificationResponse` is now explicit instead of inheriting the writable base
  notification schema.
- `appeal_status` remains response-only projection state.
- both `related_appeal_id` and `related_score_appeal_id` are included in the
  response model.
- list/detail serialization now uses a single response builder path.

### 3. Homework and score appeal notification semantics were aligned

Files:

- `apps/backend/courseeval_backend/domains/homework/appeals.py`
- `apps/backend/courseeval_backend/domains/scores/appeals.py`

Changes:

- base titles no longer hard-code "待处理" into the durable title text
- acknowledged/resolved/rejected are projected from state, not copied by local
  string surgery
- score appeal notifications now project terminal states through the same helper
  path as homework notifications

### 4. Frontend appeal action rules were centralized

New file:

- `apps/web/school/src/utils/appealNotificationActions.js`

This resolver now owns:

- `isTerminalAppealStatus`
- `isActionableAppealStatus`
- `getAppealStatusLabel`
- `getAppealStatusTagType`
- `getAppealActionLabel`
- `getAppealReadonlyLabel`
- `canOpenAppealNotification`
- `buildAppealNotificationRoute`
- `buildAppealRouteSelectedCourse`

### 5. Vue pages were converged onto the shared resolver

Touched pages:

- `apps/web/school/src/views/Notifications.vue`
- `apps/web/school/src/views/Scores.vue`
- `apps/web/school/src/views/HomeworkSubmission.vue`
- `apps/web/school/src/views/HomeworkSubmissions.vue`
- `apps/web/school/src/views/HomeworkSubmissionReview.vue`
- `apps/web/school/src/views/StudentHomeworkByCourse.vue`

Key outcomes:

- pending / acknowledged now consistently remain actionable
- resolved / rejected now consistently become readonly/view semantics
- `Notifications.vue` no longer needs to inline core terminal-state checks for
  this chain
- score-appeal deep-link route construction is centralized

## Tests Added / Extended

### Backend

File:

- `tests/backend/homework/test_homework_appeal_redteam.py`

Coverage now includes:

- resolved homework appeal notification exposes `appeal_status == resolved`
- resolved score appeal notification exposes `appeal_status == resolved`
- pending score appeal notification exposes `appeal_status == pending`
- resolved score appeal notification keeps `related_score_appeal_id`
- homework acknowledged list/detail status parity
- rejected score appeal terminal projection on notification list/detail
- rejected homework appeal terminal projection on notification list/detail
- homework submission detail surfaces `appeal_reason_text` and `appeal_teacher_response`

### Frontend

New lightweight script:

- `apps/web/school/scripts/test-appeal-notification-actions.cjs`

Hooked in `package.json` as:

- `npm run test:appeals`

It verifies:

- pending / acknowledged -> actionable
- resolved / rejected -> terminal
- route generation for homework vs score appeals
- missing `related_score_appeal_id` safely suppresses score deep-link route
- `Notifications.vue` no longer inlines a resolved-only core appeal check

### Existing E2E Follow-up Retained

File:

- `tests/e2e/web-school/e2e-scenario-resilience.spec.js`

This existing uncommitted follow-up now continues to cover the teacher
notification -> resolved score appeal -> deep-link route path.

## Validation Observed

Observed passing commands during this round:

- `npm.cmd run test:appeals`
- `npm.cmd run build`
- `.\.venv\Scripts\python.exe -m pytest tests\backend\homework\test_homework_appeal_redteam.py -q`
- `.\.venv\Scripts\python.exe -m pytest tests\behavior\test_notification_sync_api_edge_behavior.py -q`
- `git diff --check`

Notes:

- `.\.agent-run\use-local-env.ps1` was attempted as requested, but the local
  PowerShell execution policy blocked dot-sourcing in this environment.
- This was an execution-policy issue, not a repository code failure.

## Main Worries / Remaining Risks

These are the most important unresolved concerns to hand off.

### A. Notification body text still depends on projected status line rather than a richer event log

The new projection helper prevents contradictory status text, but it still
stores final user-facing body text directly on the notification row. If product
later wants a richer timeline like:

- created
- acknowledged
- rejected
- resolved

that would require a separate event-log model or a more explicit transition log.

### B. Other appeal-status consumers may still exist outside this chain

This round converged the known school-web pages for homework and notifications,
but future work touching parent portal or new dashboards should grep
`appeal_status` again before assuming every consumer has been normalized.

## Follow-up Applied After The Main Round

The earlier handoff worried that `/scores?subject_id=...&appeal_id=...` could
degrade into an empty or misleading course state when the deep-linked course no
longer existed in the current teacher course list.

That fallback is now hardened in `apps/web/school/src/views/Scores.vue`:

- route recovery still restores the exact course when `subject_id` is still
  available in the teacher's current course list;
- when the deep-linked course is no longer recoverable, the page now enters an
  explicit missing-course state instead of silently continuing with another
  selected course;
- the page surfaces a dedicated warning explaining that the target course
  context can no longer be restored, and intentionally avoids querying or
  presenting appeals for the wrong course.

Follow-up browser proof was added in
`tests/e2e/web-school/e2e-scenario-resilience.spec.js` and verified with a
single-case Playwright run that exercises a foreign-course `subject_id` while
the teacher already has a different current course selected.

An additional red-team follow-up on the same surface exposed a second-order UX
bug: once the page entered the missing-course state, a teacher could still be
effectively trapped there even after manually switching to another accessible
course from the header course switcher.

That recovery path is now also hardened in `apps/web/school/src/views/Scores.vue`:

- the first blocked deep-link keeps its own route-key and selected-course
  snapshot;
- a later manual switch to a different accessible course is treated as an
  explicit user override of the broken deep-link context;
- after that override, the warning state is cleared and the stale
  `subject_id` / `appeal_id` route context is removed so the page can continue
  under the newly selected course instead of re-blocking itself.

The latest frontend/system follow-up tightened this same recovery lane further:

- `Scores.vue` now keeps one explicit `appealRouteState` object instead of
  spreading the recovery state across several loosely coupled refs;
- the page distinguishes only two route-recovery failure modes at runtime:
  `missing-course` and `missing-target`, which reduces watcher drift and makes
  later fixes easier to reason about;
- the user store no longer exposes a page-agnostic `selectedCourseRevision`
  counter for this flow; instead it emits a narrower
  `selectedCourseSelectionEvent` that only fires for explicit user-initiated
  course selections.

That narrower signal matters because automatic course synchronization on focus,
visibility change, or route repair should not be interpreted as a teacher's
explicit recovery decision. The current recovery logic now clears stale
score-appeal route state only after a real user selection event or the
dedicated "继续使用当前课程" action.

Focused browser coverage for the score-appeal recovery lane now proves all of
the following in `tests/e2e/web-school/e2e-scenario-resilience.spec.js`:

- a foreign-course `subject_id` does not silently fall back to the current
  selected course;
- an accessible course plus a missing `appeal_id` surfaces a target-missing
  notice rather than silently treating the list as a successful locate;
- manual switch to another accessible course clears stale query state and
  survives reload;
- later local refresh does not re-poison the manually recovered page;
- the explicit "继续使用当前课程" recovery button now has clean focused green
  proof, including stale query cleanup and reload survival.

Observed passing validation for this latest follow-up:

- `npm.cmd run build`
- `python ops/scripts/dev/check_text_encoding.py apps/web/school/src/views/Scores.vue apps/web/school/src/stores/user.js tests/e2e/web-school/e2e-scenario-resilience.spec.js docs/handoffs/APPEAL_NOTIFICATION_SYSTEM_HARDENING_HANDOFF_2026-05-14.md docs/testing/agent-update-log.csv`
- `node scripts/playwright-external-runner.cjs e2e-scenario-resilience.spec.js --project=chromium --grep "teacher explicit current-course recovery button clears a foreign score-appeal deep-link warning|teacher explicit current-course recovery clears stale query context and survives reload|teacher manual recovery from a foreign score-appeal deep-link clears stale query context and survives reload|teacher manual recovery from a foreign score-appeal deep-link is not re-poisoned by a later local refresh|teacher can recover from a foreign score-appeal deep-link by manually switching to another accessible course|teacher score-appeal deep-link with a missing appeal_id inside an accessible course is not silently treated as a successful locate|teacher score-appeal deep-link with a foreign subject_id does not fall back to the currently selected course"`

Another red-team follow-up exposed a separate ambiguity on the same page:

- when `subject_id` still points at an accessible course but `appeal_id` is
  missing, stale, or outside the current course scope, the page previously
  fell back to the ordinary score/appeal list with no explicit indication that
  the requested appeal target itself was not found.

That case is now hardened too:

- `Scores.vue` distinguishes “course context missing” from “appeal target
  missing”;
- an accessible-but-missing `appeal_id` now surfaces a dedicated
  target-missing notice instead of silently implying that the ordinary list
  already represents the requested appeal;
- focused Playwright coverage was added for this exact condition in
  `tests/e2e/web-school/e2e-scenario-resilience.spec.js`.

The latest backend/frontend follow-up also removed the remaining homework-vs-score
appeal state-machine mismatch:

- `HomeworkGradeAppeal` now persists `teacher_response` and supports explicit
  terminal `rejected` handling in addition to `pending`, `acknowledged`, and
  `resolved`;
- `PUT /api/homeworks/{homework_id}/submissions/{submission_id}/appeal` now
  mirrors the score-appeal teacher handling model for `resolved` / `rejected`
  decisions with required teacher response text;
- homework submission serializers now expose `appeal_reason_text` and
  `appeal_teacher_response` so both student and teacher views can render the
  actual disposition context instead of only a status tag;
- `HomeworkSubmissionReview.vue` now offers an explicit appeal-resolution dialog
  instead of relying only on the old “标记已阅” fast path.

Observed passing validation for this follow-up:

- `python -m py_compile apps/backend/courseeval_backend/api/routers/homework.py apps/backend/courseeval_backend/api/schemas.py apps/backend/courseeval_backend/domains/homework/appeals.py apps/backend/courseeval_backend/db/models.py`
- `.\.venv\Scripts\python.exe -m pytest tests\backend\homework\test_homework_appeal_redteam.py -q`
- `npm.cmd run build`

## Recommended Next Step

If work continues on this branch, the next best follow-up is:

1. add one more browser-backed regression for the new homework appeal
   `rejected` teacher-resolution dialog if this branch continues to touch the
   homework review UI
2. add one more API regression around notification content/title parity for the
   score appeal `rejected` path if product relies on that text for staff triage
3. grep other school-web or parent-facing consumers for `appeal_status` and
   `related_score_appeal_id` before assuming this chain is fully converged
4. run the full `school.e2e.scenario_resilience` broad suite again when the
   branch is ready for broader browser closeout, because the current focused
   evidence closes the appeal-recovery lane itself but does not replace the
   full resilience tier as a whole
