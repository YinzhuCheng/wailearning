# How To Better Simulate Real Environments

This note is a practical checklist for making local and CI testing behave more like real user environments.

It is not about increasing test count. It is about reducing the gap between:

- what passes in a controlled test run
- and what fails under real users, real concurrency, real browsers, and real infrastructure

## Current State

The current repo already simulates several important real-world behaviors well:

- real browser interaction through Playwright
- multi-user login and role switching
- multi-tab and multi-session behavior
- async grading and eventual UI convergence
- LLM routing, retry, failover, regrade, and quota scenarios

That is strong application-level simulation.

It still does not fully simulate production reality in these areas:

- production-grade database concurrency
- multi-process or multi-instance execution
- real network instability and transport failures
- real third-party LLM endpoint behavior
- OS-level permission differences
- browser/device/font/input-method differences

## Highest-Value Improvements

If the goal is to get much closer to real production behavior, prioritize these in order.

### 1. Run concurrency-sensitive tests against PostgreSQL

This is the single biggest realism upgrade if production is not using SQLite.

Why it matters:

- transaction isolation differs
- lock behavior differs
- unique-constraint races differ
- deadlock behavior differs
- retry and conflict patterns differ

Recommended:

- keep SQLite for fast local smoke tests
- add PostgreSQL-backed runs for E2E and concurrency-heavy backend tests
- make all idempotency, quota, appeal, enrollment, and async-task tests runnable on PostgreSQL in CI

## 2. Separate API and worker processes

The current controlled task-drain approach is useful for deterministic testing, but it is still more controlled than production.

Why it matters:

- queue consumers can race
- task status may lag behind UI polling
- retries may overlap with stale reads
- restart recovery becomes testable only when workers are real processes

Recommended:

- run API and grading worker as separate processes
- add tests where the worker starts late, stops mid-run, or restarts after queued tasks exist
- verify authoritative state after refresh or re-login, not only during one live page session

## 3. Expand mock LLM behavior, not just success/failure codes

Mock LLM already provides strong coverage, but it should simulate transport and payload instability more aggressively.

Add cases for:

- connect timeout
- read timeout
- empty response body
- malformed JSON body
- valid HTTP 200 with invalid grading payload
- intermittent 429 then success
- intermittent 5xx then success
- endpoint returns different behavior for concurrent calls
- one endpoint in a group recovers while another remains degraded

Important rule:

- mock helpers used by E2E must preserve production semantics such as timestamps, status transitions, and routing order

## 4. Use outcome-level assertions for distributed behavior

Tests become unrealistic when they overfit internal incidental details.

Prefer asserting:

- one request succeeds and one fails
- the final UI matches backend authoritative state
- no duplicate final rows exist
- the latest valid route or score wins
- remaining quota decreases after a failed reserved path

Avoid asserting:

- exact incidental ordering unless it is product-visible
- cumulative mock request history across reset/reconfigure boundaries
- exact token remainder values unless the product contract exposes them strictly

## 5. Make local Windows runs stable and repeatable

Administrator PowerShell can help with execution stability, but it does not by itself make the simulation much more realistic.

What admin rights help with:

- fewer process and port inspection failures
- easier browser and server startup
- easier log capture and cleanup
- easier local TLS, proxy, or hosts-file experiments

What admin rights do not solve:

- database realism
- worker-process realism
- third-party service realism
- browser behavior differences by device and locale

Recommended:

- use admin PowerShell when local environment friction is blocking test execution
- do not treat elevated shell access as a substitute for production-like architecture

## 6. Add browser-environment realism where it affects UX

Some UI bugs only appear with more realistic client environments.

Recommended:

- keep Playwright browser binaries pinned and locally available
- ensure `tzdata` is installed
- ensure common system fonts are present
- test more than one viewport
- test at least one non-default locale/timezone combination when date or quota logic is visible in UI
- occasionally run with clean browser profiles and no cached state

Optional expansions:

- browser zoom and text scaling
- IME-heavy input flows
- attachment upload from large or malformed files

## 7. Add network-failure realism deliberately

Many user-visible failures are network-shape failures, not logic failures.

Recommended:

- simulate slow API responses
- simulate dropped polling responses
- simulate first-load success followed by follow-up request failure
- simulate reconnect flows after background task success

High-value checks:

- user refreshes after background success and sees the correct final state
- re-login recovers authoritative state after a failed live polling cycle
- UI does not freeze in stale queued or loading states forever

## 8. Test multi-instance and stale-state behavior more explicitly

Real systems fail at the boundaries between instances and stale clients.

Recommended:

- run selected tests with multiple independent browser contexts
- keep stale pages alive while another actor changes data
- verify the system converges instead of producing duplicates, phantom rows, or impossible UI states

Especially important for:

- course selection
- appeals
- notifications
- quota usage
- homework submissions
- grading task repair and regrade

## 9. Keep helper APIs honest

E2E helper endpoints are useful, but they can silently hide real problems if they do less than the production code path.

Rules:

- helper endpoints should update all product-relevant fields
- helper endpoints should preserve ordering and timestamps when tests depend on ordering
- helper endpoints should not grant unrealistic impossible states unless the test is explicitly about corruption recovery

Example:

- forced preset validation must set `validated_at`, not only validation status

## 10. Recommended rollout plan

If time is limited, use this order:

1. Add PostgreSQL-backed E2E or integration runs.
2. Split API and worker into separate test processes.
3. Expand mock LLM failure models.
4. Add more refresh/re-login authoritative-state recovery assertions.
5. Improve Windows execution stability with better shell/process conventions.
6. Add targeted network and locale variation runs.

## Minimal Practical Upgrade Path

If you want the smallest set of changes that gives a large realism gain, do these first:

1. PostgreSQL test database
2. separate worker process
3. richer mock LLM failures
4. authoritative-state assertions after refresh or re-login

Those four changes will improve realism much more than simply installing a few extra packages or always launching PowerShell as administrator.
