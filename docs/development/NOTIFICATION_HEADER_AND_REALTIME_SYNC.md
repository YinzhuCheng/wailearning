# Notification header badge, user-menu entry, and near-real-time sync

## Purpose (for humans and LLM agents)

Course notifications are stored server-side (`notifications` + `notification_reads`). The admin SPA must:

1. Show **unread count on the header avatar** (badge) so users notice new items without opening the sidebar.
2. Expose **「查看通知」** from the **avatar dropdown** (same place as personal settings / logout), with optional unread count in the label.
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

### Dropdown label

- Computed `notificationsMenuLabel`: `查看通知` or `查看通知（N 条未读）` when `N > 0`.
- Command `notifications` routes to `/notifications`.

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

## Related documentation

- [Test Execution Pitfalls](TEST_EXECUTION_PITFALLS.md) — general CI / Playwright traps
- [Content format: Markdown vs plain text](CONTENT_FORMAT_MARKDOWN_AND_PLAIN_TEXT.md) — touches `Notifications.vue` for rich text bodies
