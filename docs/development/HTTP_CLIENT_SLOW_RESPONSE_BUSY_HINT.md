# HTTP client: slow-response “system busy” hint (admin SPA)

## Purpose

When the backend is under load or the network is slow, users may see an apparently frozen UI with no feedback until axios hits its **full request timeout** (e.g. 10s) or the browser gives up.

The admin SPA therefore shows a **non-blocking** Element Plus message after a **first-byte delay threshold** (currently **3 seconds**):

> 系统正忙，请等待。

The message stays open until the request **settles** (success, HTTP error, or network/timeout error), then it is closed automatically. Users may also dismiss it with the close control.

## Implementation

| Item | Location |
|------|----------|
| Threshold constant | `apps/web/admin/src/api/index.js` — `SLOW_RESPONSE_THRESHOLD_MS = 3000` |
| Message text | `SLOW_BUSY_MESSAGE` in the same file |
| Logic | `attachSlowBusyWatcher` + `clearSlowBusyIfAny` on `http`, `httpQuiet`, and `httpPublic` axios instances |

### Request lifecycle

1. **Outgoing** (`request` interceptor): after attaching the Bearer token, call `attachSlowBusyWatcher(config)`.
2. **Timer**: `setTimeout(..., 3000)` stores handle on `config._slowBusyTimer`.
3. **On fire**: open `ElMessage({ duration: 0, showClose: true, type: 'warning' })` and store instance on `config._slowBusyMessage`.
4. **Settling** (`response` / `responseError` interceptor): always `clearSlowBusyIfAny(config)` — clears timer if still pending and closes message if shown.

### Opt-outs

- **`timeout: 0` or `timeout: false`** (unbounded requests, e.g. file uploads / blob downloads): **no** slow-busy timer — otherwise a large upload could show “busy” for the entire upload duration.
- **`skipSlowBusyMessage: true`** on a config: skips the watcher entirely (use if a specific long-poll or streaming endpoint needs silence).

### Pitfalls (agent-oriented)

1. **Must clear on both success and error**  
   Forgetting `clearSlowBusyIfAny` on the success branch leaves a stuck `duration: 0` message. Both `http` interceptors’ fulfilled handler must call clear.

2. **`error.config` may be undefined**  
   Some axios failures omit `config`. Always call `clearSlowBusyIfAny(error?.config)` safely.

3. **Do not stack messages per retry**  
   The timer and message live on the **same** config object for one adapter call; axios retries may reuse config—clearing on any terminal outcome prevents duplicates.

4. **Changing the threshold**  
   Edit `SLOW_RESPONSE_THRESHOLD_MS` only in `api/index.js`; keep product copy in `SLOW_BUSY_MESSAGE` if marketing changes wording.

## Related

- [Test Execution Pitfalls](TEST_EXECUTION_PITFALLS.md) — broader frontend/CI notes
- [Notification header badge and realtime sync](NOTIFICATION_HEADER_AND_REALTIME_SYNC.md) — separate concern (polling `sync-status`)
