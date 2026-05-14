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

### A. Homework vs score appeal state machines are still not truly identical

The projection layer is now shared, but backend state progression is still only
partially aligned:

- homework currently uses:
  - `pending`
  - `acknowledged`
  - `resolved`
- score appeal currently uses:
  - `pending`
  - `resolved`
  - `rejected`

The frontend/state resolver now understands all four states, but homework still
has no native reject path. This is a **spec ambiguity**, not something to
invent silently.

### B. Deep-link recovery for missing course context is still weak

`Scores.vue` can recover `subject_id` when the target course still exists in the
teacher's available teaching-course list. If the route points at a course that
is no longer recoverable there, the page still degrades toward empty selected
course state rather than a dedicated explanation. This remains a product/UX gap.

### C. Notification body text still depends on projected status line rather than a richer event log

The new projection helper prevents contradictory status text, but it still
stores final user-facing body text directly on the notification row. If product
later wants a richer timeline like:

- created
- acknowledged
- rejected
- resolved

that would require a separate event-log model or a more explicit transition log.

### D. Other appeal-status consumers may still exist outside this chain

This round converged the known school-web pages for homework and notifications,
but future work touching parent portal or new dashboards should grep
`appeal_status` again before assuming every consumer has been normalized.

## Recommended Next Step

If work continues on this branch, the next best follow-up is:

1. decide whether homework appeal should ever support explicit `rejected`
   semantics; document that decision instead of leaving it implicit
2. add one more API regression around notification content/title parity for the
   score appeal `rejected` path if product relies on that text for staff triage
3. consider a dedicated UX fallback for `/scores?subject_id=...&appeal_id=...`
   when the target course context can no longer be restored
