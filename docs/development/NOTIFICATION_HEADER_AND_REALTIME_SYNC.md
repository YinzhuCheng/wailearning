# Notification header badge, user-menu entry, and near-real-time sync

## Purpose (for humans and LLM agents)

Course notifications are stored server-side (`notifications` + `notification_reads`). The admin SPA must:

1. Show **unread count on the header avatar** (badge) so users notice new items without opening the sidebar.
2. Primary navigation to the inbox remains the **sidebar** (`课程学习` → **课程通知** for students). The avatar menu keeps **个人设置** / **退出登录** only so notification discovery is not duplicated in two places.
3. **Refresh quickly** when someone publishes a notification (including the **publisher’s own tab** on `/notifications`).
4. Optionally **surface a desktop toast** (`ElNotification`) when the unread count increases or the inbox grows while unread exists.

This document ties together the Vue layout, the lightweight sync API, the `notificationSync` helper, and pitfalls observed while wiring the feature.

## Data flow (high level)

### Authoritative state

- `GET /api/notifications` (and list variants) return `is_read` per row for the current user.
- `GET /api/notifications/sync-status` returns `{ total, unread_count, latest_updated_at }` with the **same visibility rules** as the list endpoint (`_visible_notifications_query` in `apps/backend/wailearning_backend/api/routers/notifications.py`).

### Client refresh triggers

1. **Polling** from `Layout.vue`: calls `syncStatus` on an interval while the document is visible.
2. **BroadcastChannel** (`broadcastNotificationChange` in `apps/web/admin/src/utils/notificationSync.js`): fired after publish/update/delete/mark-all in `Notifications.vue` so **other tabs** refetch.
3. **In-tab emit** (`emitNotificationRefresh`): after a successful publish/update in `Notifications.vue`, the same tab calls `emitNotificationRefresh()` so `onNotificationRefresh` listeners reload the table **immediately** without waiting for the next poll.

### Header badge source

`Layout.vue` stores `headerUnreadCount` from each `syncStatus` response. The avatar trigger is wrapped in `el-badge` with `:hidden="headerUnreadCount === 0"`.

## File map (implementation)

| Concern | Path |
|---------|------|
| Poll + toast + badge | `apps/web/admin/src/views/Layout.vue` |
| Default poll interval export | `apps/web/admin/src/utils/notificationSync.js` (`DEFAULT_NOTIFICATION_POLL_INTERVAL_MS`, default `12_000`) |
| List UI + publish | `apps/web/admin/src/views/Notifications.vue` |
| Sync API | `apps/web/admin/src/api/index.js` → `api.notifications.syncStatus` |
| Backend sync | `GET /api/notifications/sync-status` in `apps/backend/wailearning_backend/api/routers/notifications.py` |

## UX details

### Avatar badge

- Uses Element Plus `el-badge` around the existing `.user-box` (avatar + optional name).
- CSS: `.header-user-badge :deep(.el-badge__content)` nudges the dot so it sits on the avatar corner with a light border for contrast on varied themes.

### Sidebar vs avatar menu

- **Unread count** still appears on the avatar badge; route to **`/notifications`** is via **sidebar** for students/teachers (see `Layout.vue` menu definitions).
- **Historical note:** an older iteration duplicated **「查看通知」** inside the avatar dropdown (`data-testid="header-menu-notifications"`). That duplicate entry was removed to reduce redundant navigation paths; regression specs now click **`课程通知`** under **`课程学习`** where applicable.

### Toast (`ElNotification`)

- When **baseline exists** (second successful poll) and either:
  - `unread_count` strictly increases, or
  - `total` increases **and** `unread_count > 0`,
- Then show a non-spamming toast keyed by the sync signature `(total, unread, latest_updated_at)`.

This avoids toasting on every poll when counts are stable, and avoids double-toasts for the same server snapshot.

### Notifications table “已读” column

`Notifications.vue` adds an explicit **已读 / 未读** column (`el-tag`) in addition to the existing unread title styling and dot column for pinned rows.

## Pitfalls encountered (agent-oriented)

### 1. Vite / Vue SFC parse error: “Missing semicolon” after `computed`

**Symptom:** `npm run build` fails with `[vue/compiler-sfc] Missing semicolon` pointing at a random line **after** a `computed(() => { ... })` block.

**Cause:** The `computed` callback was closed with `})` but the **`const quotaBarColors = [` assignment line was accidentally deleted**, leaving bare array literals `{ color: ... }` in `<script setup>` top-level scope.

**Fix:** Restore the full declaration:

```js
const quotaBarColors = [
  { color: '#93c5fd', percentage: 60 },
  ...
]
```

**Prevention:** after editing `Layout.vue`, always run `npm run build` before commit; diff the script block around any new `computed` insertions.

### 2. Publisher tab does not refresh until poll interval

**Symptom:** Teacher stays on `/notifications`, publishes a notice, table still empty/old until ~45s (old default poll).

**Cause:** `broadcastNotificationChange` only reaches **other** tabs; the publishing tab does not receive its own BroadcastChannel message.

**Fix:** call `emitNotificationRefresh()` from `Notifications.vue` after successful create/update (same pattern as delete/mark-all).

### 3. False-positive “new notification” toasts

**Symptom:** user gets toasts when nothing new happened.

**Mitigation implemented:**

- Require a **prior poll baseline** before comparing counts.
- Compare **numeric** unread/total (`Number(...)`) to avoid string ordering bugs.
- De-duplicate with `lastNotificationToastSignature` per `(total, unread, latest_updated_at)` snapshot.

### 4. Admin vs course-scoped sync params

`notificationSyncParams` in `Layout.vue` returns `null` for admin (all notifications) and `{ subject_id }` when a course is selected for teacher/student. Changing course resets signature refs so the next poll establishes a clean baseline.

## Operational tuning

- **Poll interval:** `DEFAULT_NOTIFICATION_POLL_INTERVAL_MS` in `notificationSync.js` (currently **12000 ms**). Lower = snappier UI + more `/sync-status` traffic; raise if an environment rate-limits.

## Automated regression coverage (additive)

This subsection records **machine-verified** suites that target the header badge + `/sync-status` contract. It is written primarily for LLM agents who need searchable pointers; humans may skim the file paths and commands.

### Playwright (UI + API hybrid)

- **File:** `tests/e2e/web-admin/e2e-notification-header-sync-tier.spec.js` (**10** `test(...)` cases).
- **What it proves beyond older notification E2E:**
  - The DOM under `data-testid="header-notification-badge"` reflects **`sync-status.unread_count`** after **`window.focus`**-equivalent polling (`dispatchEvent('focus')`), not only after API-only assertions.
  - Case **02** asserts unread appears on the **badge** and that **sidebar `课程通知`** reaches **`/notifications`** (replaces the former duplicate-dropdown label check).
  - **`header-course-switch`** changes which `subject_id` the layout passes into `syncStatus`, so the badge can drop to **hidden** when the elective scope has zero unread even if the required course still has unread rows server-side.
  - Route transitions (`/courses` → `/course-home`) still execute `watch(route)` hooks that call `pollNotificationSync()` — the spec deep-links `/course-home` instead of clicking **进入课程** twice (second click can remain **disabled** while enrollment reconciliation catches up; same failure family as catalog flip-flop pitfalls).
- **Run command** (always from `apps/web/admin`; never from `<REPO_ROOT>/tests/e2e/...` alone — Playwright project discovery requires `playwright.config.cjs`):

```bash
cd <REPO_ROOT>/apps/web/admin
CI=1 E2E_PYTHON=<python-with-requirements> E2E_DEV_SEED_TOKEN=<seed> \
  npx playwright test e2e-notification-header-sync-tier.spec.js --project=chromium
```

### Playwright deep tier (follow-up hazards)

- **File:** `tests/e2e/web-admin/e2e-notification-sync-deep-tier.spec.js` (**15** `test(...)` cases).
- **Why it exists:** The first tier proved baseline badge wiring; this module stresses **role-specific** aggregation (**admin** global `sync-status` vs **teacher/student** course-scoped params), **corrupt `selected_course` localStorage** healing, **concurrent** teacher `POST`s, **teacher-owned vs other-teacher** notification isolation, **403** on inaccessible `subject_id`, **mobile viewport**, **full page reload** (`onMounted` → `pollNotificationSync` without relying on manual focus), and **delete race** while the student notifications view loads.
- **Lessons baked into the spec comments:**
  - Teachers may land on **`/dashboard`** with **`ensureSelectedCourse`** picking a **non-required** course first (ranking by semester/id). Assertions against **`course_required_id`** must **explicitly switch** via **`header-course-switch`** → `.course-dropdown-menu .course-option` (click **switcher**, not hover-only).
  - Overriding **`document.visibilityState`** in Playwright did **not** stop `pollNotificationSync` reliably in Chromium (the visibility descriptor is not consistently honored for interval timers). The **`visibility hidden`** scenario was replaced by **`page.reload()`** evidence for cold-start polling — document that **true background-tab** gating remains a **residual risk** not fully automated here.
- **Run command:**

```bash
cd <REPO_ROOT>/apps/web/admin
CI=1 E2E_PYTHON=<python-with-requirements> E2E_DEV_SEED_TOKEN=<seed> \
  npx playwright test e2e-notification-sync-deep-tier.spec.js --project=chromium
```

### pytest behavior (HTTP contract stress)

- **File:** `tests/behavior/test_notification_sync_api_edge_behavior.py` (**10** tests).
- **What it proves:**
  - `GET /api/notifications` **total** / **unread_count** match `GET /api/notifications/sync-status` for the same **subject_id** scope (student).
  - Multi-course isolation: second enrollment + notifications pinned to **different** `subject_id` rows stay isolated in per-subject sync snapshots.
  - **Concurrent** teacher publishes + student read storms settle without violating uniqueness expectations on `notification_reads`.
  - Students receive **403** (not **500**) when requesting sync-status with a **subject_id** they cannot access (must use HTTP-layer course gate — see backend notes below).

### Backend notes the tests forced into clarity (May 2026)

These are not “optional commentary”; they are contract fixes discovered while turning the tests green:

1. **`ensure_course_access` vs HTTP errors:** `_visible_notifications_query` previously called `ensure_course_access(...)`, which raises **`PermissionError`** when the subject is not in the user’s accessible set. Uncaught, Starlette turns that into a **500**. The notifications router now uses **`ensure_course_access_http`** anywhere the failure must map to **403** for API clients.

2. **`updated_at` on notification updates:** SQLite + SQLAlchemy `onupdate=func.now()` on `Notification.updated_at` did **not** reliably advance within the same HTTP request when a teacher `PUT` changed only `title`. That left `latest_updated_at` in **`GET /api/notifications/sync-status`** unchanged across back-to-back polls — exactly the “sync signature never moves” failure mode for UI dedupe. `update_notification` now assigns **`notification.updated_at = datetime.now(timezone.utc)`** immediately before `commit()`.

3. **Concurrent delete vs list serialization:** Under SQLite dev E2E load, `GET /api/notifications` could fetch rows then lose them to a concurrent **`DELETE`** before `_serialize_notification` touched `notification.id`, raising **`sqlalchemy.orm.exc.ObjectDeletedError`**. The list handler now **skips** expired instances instead of failing the whole response (short window; acceptable trade for dev/E2E stability).

## Related documentation

- [Test Execution Pitfalls](TEST_EXECUTION_PITFALLS.md) — general CI / Playwright traps
- [Content format: Markdown vs plain text](CONTENT_FORMAT_MARKDOWN_AND_PLAIN_TEXT.md) — touches `Notifications.vue` for rich text bodies
