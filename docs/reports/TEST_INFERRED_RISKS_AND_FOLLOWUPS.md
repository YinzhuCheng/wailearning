# Test-Inferred Risks And Follow-Ups

## Purpose

This document records repository weaknesses, suspected bugs, and structural risks inferred during the May 1, 2026 repository-refactor validation pass.

Historical note:

- items that discuss the old root-level `app/` compatibility package are now historical,
- the repository has since completed the namespace migration to `apps.backend.courseeval_backend`,
- those entries remain here because they explain why the migration was necessary.

A later full-suite repair pass (May 2026, Linux/CI-style execution with Playwright + pytest) added a few more items: same schema as below—`Observed`, `Strong inference`, or `Structural risk`—and the same disclaimer: not a confirmed defect list.

This is not a list of confirmed product defects. It is a focused backlog of areas that felt risky under real test pressure and therefore deserve deliberate follow-up.

Where possible, each item is labeled as one of:

- `Observed`: directly seen in tests or runtime behavior
- `Strong inference`: not proven in isolation, but strongly suggested by behavior or structure
- `Structural risk`: maintainability or correctness risk implied by current code shape

## Priority Interpretation

- `P1`: likely user-facing correctness risk or important flake source
- `P2`: meaningful technical risk that can hide future bugs
- `P3`: structural debt worth scheduling but not necessarily urgent

## P1: notification mark-all-read dual-tab convergence remains suspicious

### Type

`Observed`

### Evidence

During the full Playwright validation after the repository restructure, exactly one scenario failed:

- `tests/e2e/web-admin/e2e-scenario-resilience.spec.js`
- scenario: `dual-tab student mark-all-read leaves every fresh course notification read`

The failure mode was:

- the expected read/mark button remained disabled long enough to hit the test timeout

The same scenario passed immediately when rerun in isolation on a fresh isolated stack.

### Interpretation

This looks like one of the following:

- a genuine race in notification read-state convergence,
- UI state derived from stale store/cache state,
- insufficient server-side idempotency under concurrent read operations,
- or a flaky test that is exposing a real timing sensitivity in the product.

### Why this matters

This scenario is exactly the kind of state-convergence bug that real users hit in multiple tabs.

### Follow-up

- instrument notification mark-all-read server responses under concurrent access
- inspect frontend disabled/enabled state transitions around the read action
- verify whether the authoritative backend state was actually correct when the UI timed out
- run this scenario repeatedly in isolation and in-suite to measure flake rate

**Update (Round-4 continuation, 2026-05):** `POST /api/notifications/mark-all-read` was hardened server-side for **SQLite and PostgreSQL** by batching `notification_reads` updates with `INSERT .. ON CONFLICT DO UPDATE` on the composite unique key `(notification_id, user_id)`, plus a regression test `test_c7b_concurrent_dual_mark_all_read_no_integrity_errors`. This removes a common `IntegrityError` race when two tabs or threads mark-all-read concurrently; UI-level convergence and other client races remain worth monitoring.

## P1: backend import/startup path is too side-effect-heavy

### Type

`Strong inference`

### Evidence

The backend still depends on `uvicorn apps.backend.courseeval_backend.main:app`, but importing the process entrypoint module is not a cheap or purely declarative step:

- database setup behavior exists at module import time
- startup-related code paths are tightly coupled to database availability
- the application object is still imported directly from a process entrypoint module instead of a lighter factory boundary

### Why this matters

Heavy import-time side effects make all of these harder:

- testing
- scripting
- background worker separation
- migration to cleaner package layouts
- isolated imports for tooling

### Follow-up

- remove nontrivial side effects from module import paths
- ensure app construction is separate from schema/bootstrap activity
- make `app.main` import-safe without requiring environment assumptions

## P1: backend startup and bootstrap concerns are too intertwined

### Type

`Structural risk`

### Evidence

From the code shape and startup behavior:

- schema updates
- normalization jobs
- data backfills
- roster reconciliation
- optional demo seed
- optional LLM worker startup

are all clustered around startup/bootstrap flow.

### Why this matters

This increases the chance of:

- startup regressions that are hard to isolate
- order-dependent bugs
- environment-sensitive behavior differences between tests, local dev, and production
- one-off fixes being added to startup until it becomes unreasonably fragile

### Follow-up

- split bootstrap responsibilities into explicit phases
- separate one-time repair tasks from every-startup tasks
- define which startup behaviors are safe in production, in tests, and in seed-only flows

## P1: the LLM subsystem is functionally rich but structurally too concentrated

### Type

`Structural risk`

### Evidence

`apps/backend/courseeval_backend/llm_grading.py` is very large and sits in the middle of:

- grading execution
- attachment handling integration
- retry behavior
- routing
- quota interactions
- worker behavior
- persistence/state transitions

### Why this matters

Large central modules tend to accumulate hidden coupling and make bug isolation expensive.

### Likely symptom class

- fixes in one branch of grading logic accidentally affecting another
- recovery/retry paths diverging from first-pass grading behavior
- hard-to-predict behavior under concurrent or partial-failure conditions

### Follow-up

- identify coherent submodules such as worker orchestration, grading normalization, endpoint execution, and persistence transitions
- shrink the public surface of the central grading module
- add narrower unit tests around extracted sub-behaviors

## P2: Windows test stability currently depends on repository-side pytest workarounds

### Type

`Observed`

### Evidence

The full backend suite only became stable on this machine after adding Windows-specific temp-directory handling in repository-level test bootstrap.

### Interpretation

Even if these workarounds are acceptable for this environment, they are a signal that the current test harness is sensitive to platform-specific runner behavior.

### Why this matters

Fragile test infrastructure can mask real regressions by flooding maintainers with environmental failures.

### Follow-up

- decide whether these Windows test bootstrap workarounds should remain long-term
- document the intended Windows support level explicitly
- consider whether CI should exercise Windows regularly if Windows remains a first-class development environment

## P2: frontend and E2E coupling is still operationally complex

### Type

`Strong inference`

### Evidence

To get reliable Playwright runs, the current setup needs careful control of:

- backend process startup
- Vite startup
- browser cache path
- API URL
- base URL
- worker mode
- external-server mode

### Why this matters

The more fragile the boot choreography is, the easier it is for real regressions to be hidden by harness noise.

### Follow-up

- simplify the browser-test startup contract
- reduce hidden assumptions in Playwright config
- consider a documented "known-good" local E2E launcher script for Windows

## P2: notification and appeal concurrency should remain a dedicated audit area

### Type

`Strong inference`

### Evidence

The test suite spends notable effort on:

- duplicate appeal creation
- read-state convergence
- concurrent actions from stale pages
- eventual authoritative state after retries/failures

That concentration usually means the codebase has already had to defend itself against concurrency-sensitive edge cases.

### Interpretation

Even where tests pass, these areas are likely to remain fragile and deserve ongoing regression attention.

### Follow-up

- keep concurrency scenarios in every serious regression pass
- inspect whether frontend optimistic state and backend authoritative state can temporarily diverge in user-visible ways
- audit whether conflict responses are consistently meaningful across related endpoints

## P2: route files still look too heavy in some domains

### Type

`Structural risk`

### Evidence

Several route modules remain large after the directory restructure, for example:

- homework
- scores
- subjects
- users

### Why this matters

Large route files often indicate mixed concerns:

- request validation
- authorization
- business rules
- persistence orchestration
- response shaping

### Follow-up

- keep moving business logic out of route modules
- use the new directory layout as an opportunity to continue domain extraction instead of stopping at filesystem renaming

## P2: historical note on the removed `app` compatibility shim

### Type

`Observed`

### Evidence

At the time of the original refactor pass, the repository used a thin root-level `app` package shim to preserve existing import paths while the real backend package lived under `apps/backend/courseeval_backend/`.

### Interpretation

That was the right move for a safe migration, but it was transitional architecture.

### Why this matters

If left indefinitely, it would have kept:

- packaging intent remains ambiguous
- import ownership stays conceptually split
- future tooling may continue to assume the old layout

### Follow-up

- completed in May 2026 by migrating to the canonical namespace `apps.backend.courseeval_backend`
- keep this note as a reminder not to recreate compatibility import layers casually

## P3: documentation and script path correctness will drift unless enforced

### Type

`Observed`

### Evidence

The repository reorganization required touching many docs and scripts because paths were hardcoded in:

- README content
- deployment docs
- git workflow docs
- Playwright config
- deploy scripts
- CI files

### Why this matters

The next layout change will create similar drift unless path assumptions are centralized or verified.

### Follow-up

- prefer shared variables or clearer conventions in scripts
- consider lightweight doc/script path checks in CI

## P2: Element Plus default locale can disagree with Chinese UI copy and tests

### Type

`Observed`

### Evidence

On a stock `app.use(ElementPlus)` setup without an explicit `locale`, `ElMessageBox` confirm/cancel may render English **OK** / **Cancel** while the rest of the app uses Chinese copy. E2E tests that target `确定` or disambiguate `关闭` can then fail for locale reasons, not product logic.

### Why this matters

- false failures in message-box flows (delete, confirm, etc.)
- dual close affordances in dialogs (header "close this dialog" vs footer primary button) already complicate `getByRole` matching

### Follow-up

- register a single application-wide Element Plus locale consistent with the product language, or
- make E2E match `aria` names from the active locale, or
- add `data-testid` on critical dialog actions if copy-based matching remains brittle

## P2: `course_enrollments` duplicate inserts can surface under startup reconciliation (especially SQLite)

### Type

`Observed` (during a May 2026 full-suite pass, fixed defensively in code) / `Strong inference` for long-term data model

### Evidence

Application lifespan runs `reconcile_student_users_and_roster`, which can invoke `prepare_student_course_context` / enrollment sync from multiple directions close together. In SQLite-heavy runs this produced `UNIQUE constraint failed: course_enrollments.subject_id, course_enrollments.student_id` during startup.

### Interpretation

Insertion paths were not all mutually aware of in-flight rows in the same session; relying on application-level "already enrolled" checks alone is brittle under parallel reconciliation.

### Why this matters

- startup failure blocks every endpoint including health checks and Playwright boot
- Postgres might mask different races than SQLite

### Follow-up

- consider DB-level idempotency (`INSERT OR IGNORE` semantics / upserts) where appropriate for enrollments
- audit all callers of enrollment sync for redundant work in one transaction
- keep SQLite in CI or smoke paths if it remains a supported dev/test database

## P2: client request `page_size` can drift above FastAPI validation limits

### Type

`Strong inference`

### Evidence

The materials list UI requested `page_size` larger than the route allows (`Query(..., le=100)` pattern). The failure mode was an empty UI table rather than an obvious inline validation message—easy to misread as "seed broken".

### Follow-up

- share numeric bounds between OpenAPI schema and frontend constants where feasible
- surface list API errors in UI dev flows when responses are 422

## P3: homework submit page places discussion textarea above submission textarea

### Type

`Structural risk`

### Evidence

Automations using `textarea:first()` targeted the discussion draft control instead of the homework submission body (`homework-submit-content`), producing confusing outcomes (no submission recorded).

### Follow-up

- treat `data-testid="homework-submit-content"` (and related submit affordances) as the stable contract for E2E
- consider a short note in teacher/student UI docs that two text areas exist on the same view

## Next full regression pass — extra focus (May 2026 addendum)

When re-running the full stack after changes to enrollment, materials, or internationalization:

1. **Startup / SQLite**: cold start or fresh E2E DB file after many `reset-scenario` cycles; watch for duplicate enrollment during `reconcile_student_users_and_roster`.
2. **Playwright + `webServer` on Linux/CI**: confirm the backend process uses the same Python environment as `pytest` (see [../development/TEST_EXECUTION_PITFALLS.md](../development/TEST_EXECUTION_PITFALLS.md) Pitfall 11).
3. **Message-box flows**: any change to Element Plus upgrade or locale config—re-smoke delete/confirm paths in admin.
4. **Homework + discussion**: any change to `HomeworkSubmission` layout—re-run a small E2E that both posts a discussion line and submits homework text.
5. **Materials list**: any change to list API limits or `Materials.vue` list parameters—verify a non-empty table with >0 materials for a seeded course.
6. **PostgreSQL-only pytest**: if schema columns are in scope, run with `TEST_DATABASE_URL` (or project Postgres) so `test_r3` in `test_regression_llm_quota_behavior` is not skipped by accident.

## P3: CI definitions were previously stale enough to reference invalid startup behavior

### Type

`Observed`

### Evidence

The previous pipeline files were not aligned with the current project shape and had to be rewritten during the restructure.

### Interpretation

CI drift had already accumulated before this change.

### Follow-up

- verify the rewritten CI definitions on the actual target CI platform
- ensure CI runs reflect the same entrypoints developers actually use

## May 2026: follow-up from tier-4 stress E2E implementation (test pressure)

This section adds **incremental** risk notes from implementing and stabilizing `tests/e2e/web-admin/e2e-tier4-stress-backlog.spec.js`. It does not replace earlier items; it classifies what turned out to be **test-side** vs **product-side** under pressure.

### Dominant failure mode during triage

- **Most red runs** were **test or harness mistakes**: wrong REST paths, assumed JSON fields not in response models, invalid edge values vs Pydantic `ge=` / min-length validators, fragile UI selectors, or URL construction bugs in helpers.
- **Fewer but higher-impact** failures were **real product gaps**: for example JWTs remaining valid after password change until explicit invalidation was added, and attachment download-by-name not considering **user avatar** URLs in DB lookup (fixed). Those are worth tracking as product work when encountered.

### Residual product concerns (still worth monitoring)

- **Session / token model**: any future auth feature (refresh tokens, device revoke) must stay consistent with **`token_version`** (or equivalent) so “change password” and “logout everywhere” semantics remain testable and secure.
- **Endpoints that 500 on bad input**: if a malformed JSON body produces **500** instead of **422**, treat as **hardening** backlog — tests should not rely on that behavior.
- **SQLite concurrency**: idempotent inserts help; **lost updates** on counters or read-modify-write paths remain a structural risk under parallel requests (see Pitfall 24 in [../development/TEST_EXECUTION_PITFALLS.md](../development/TEST_EXECUTION_PITFALLS.md)).
- **Notification read-state under concurrency**: dual-tab mark-all-read remains the flagship **P1** flake/risk (see above); tier-4 did not retire that concern.
- **LLM subsystem**: large routers, worker coupling, and quota paths — **P1/P2** items elsewhere in this file still apply; stress E2E increases confidence but does not prove correctness under all production timings.

### Source of “potential bugs” vs “test bugs” (rule of thumb)

| Source | Typical signal |
| --- | --- |
| **Test / contract mismatch** | Immediate `404`/`422` with a clear FastAPI detail; wrong path in test; field name absent in schema. |
| **Product defect** | Same steps manually or via minimal `curl` reproduce wrong business state; security expectation (invalidated session) violated; 500 on valid input; data integrity after single-threaded API sequence. |

When triaging, fix **contract mismatches in tests first**; if minimal reproduction still fails, escalate to product.

## May 2026: concerns surfaced during a full admin E2E + pytest pass (agent)

This section records **residual risk and suspected sources** after a long full-suite run. It is **incremental** with earlier P1/P2 items (e.g. dual-tab mark-all-read, startup coupling): those remain authoritative until closed.

### Harness / environment (not product defects, but they hide real bugs)

- **Vite dev server under Playwright `webServer`**: hot reload and chained navigations can cause **`ERR_ABORTED`**, **interrupted navigation**, or **destroyed execution context** during `login()` helpers. **Source**: dev-mode SPA + aggressive `goto`/`evaluate` sequencing. **Mitigation**: see Pitfall **37** in [../development/TEST_EXECUTION_PITFALLS.md](../development/TEST_EXECUTION_PITFALLS.md); prefer stable preview builds in CI if flaking persists.
- **Port reuse**: stale **`node` / `chrome`** on `E2E_API_PORT` / `E2E_UI_PORT` after aborted runs prevents `webServer` startup. **Source**: process cleanup, not application logic.
- **SQLite + long E2E**: many `reset-scenario` cycles and concurrent tabs stress the same file DB as pytest defaults; **duplicate enrollment** and timing sensitivity are already called out elsewhere (P2 / Pitfall 16). Re-validate critical enrollment fixes on Postgres when possible.

### Product-adjacent UX / state that can look like bugs under automation

- **Elective 退选 disabled until `courses` loads**: the UI intentionally disables **退选** until the client believes the row is an elective enrollment. **Source**: `MyCourses.vue` coupling catalog flags to **`courses`** store. Slow networks can widen the window; tests must **`toBeEnabled`** before click. Whether to relax UX (e.g. spinner instead of disabled) is a **product** decision, not a test requirement.
- **MessageBox accessibility**: if product teams need strict `getByRole('dialog', { name })` in tests, consider **explicit `aria-labelledby`** or documented testids on confirm dialogs — today, tests work around Element Plus markup (Pitfall 32).

### Ongoing product-risk themes (unchanged priority, reinforced by the pass)

- **Notification read-state under concurrency** (existing **P1**): still the highest-value area to classify as product race vs test flake.
- **Backend import/startup coupling** (existing **P1/P2**): heavy lifespan work magnifies any flake in long E2E runs.
- **Enrollment reconciliation on SQLite** (existing **P2**): keep watching for `IntegrityError` on `course_enrollments` under parallel or rapid reset scenarios.

### How to use this subsection when filing issues

- If **`curl` / minimal pytest** reproduces wrong state → **product** issue (file with repro DB dialect).
- If only **Playwright + Vite** shows the failure and **`domcontentloaded` + retry** stabilizes it → start as **harness**; still worth CI hardening so noise does not mask regressions.

### May 2026 (second pass): pagination contract drift across routers

**Concern:** Admin and teacher UIs call many list endpoints with `page_size`. FastAPI validates **`le=` per route**; some lists allow **1000** (e.g. students) while others cap at **100** (logs, points exchanges/records, parent portals, homework submission grids). **Source:** independent `Query` defaults in `apps/backend/courseeval_backend/api/routers/*.py`.

**Risk:** A future UI change that sends a **single global `page_size`** (or copies a constant from one screen) could yield **422** on some pages while others silently cap or error — hard to spot without route-level contract tests.

**Mitigation (engineering):** when changing pagination defaults, grep **`page_size`** across routers and the admin `src/api` client together; keep at least one **per-family** API test (see `e2e-pitfall-guard-rails-batch2.spec.js`) or pytest parametrics so drift is caught early.

### May 2026: class-teacher visible-course management boundary

**Concern:** The class-teacher role has legitimate course visibility through
`subject_class_links`, but that visibility must not become write authority over
another teacher's course-owned state.

**Evidence:** Repeated security hardening runs on
`tests/security/test_security_hardening_followup.py` exposed real gaps before
the current fixes: class teachers could mutate teacher-owned visible courses
through subject management, cover uploads, roster operations, material/homework
creation, scores and grade schemes, attendance writes, notification publishing,
discussion deletion, material chapter movement/linking, score appeal response,
parent-code revocation for foreign-class students visible only through linked
courses, dashboard course-scope aggregation, and course LLM config.

**Current mitigation:** The affected routers now layer
`is_course_instructor(...)` or equivalent route-local wrappers after
`ensure_course_access_http(...)` for course-owned writes. The focused backend
security file and `tests/e2e/web-admin/e2e-security-hardening-followup.spec.js`
cover the red-to-green boundary.

**Residual risk:** Future feature work can reintroduce the same mistake by
copying a read/list pattern into a write route. Any new route that writes
course-owned data should include a direct class-teacher visible-course denial
test before it is treated as secure.

**Parent-code residual risk:** This round fixed the confirmed class-teacher
case: a class teacher may manage parent codes only for students in their direct
assigned class, not for foreign classes that become visible through a linked
course. Regular `teacher` users still use `get_accessible_class_ids_from_courses(...)`
for parent-code management. That may be an intended course-teacher workflow, but
it is a policy point worth confirming before claiming the parent-code surface is
fully narrowed.

**Parent portal read residual risk:** A later hardening round found and fixed a
different parent-code issue: `/api/parent/homework` and
`/api/parent/notifications` previously trusted same-class visibility for rows
with `subject_id`, which leaked same-class elective homework and course
notifications to guardians of students who were not enrolled in that elective.
The parent router now keeps class/global rows visible when `subject_id IS NULL`
but requires a matching `CourseEnrollment` for subject-scoped rows. The backend
regressions are `test_hard53` and `test_hard54`; the browser-backed direct-API
regressions are cases 13 and 14 in
`tests/e2e/web-admin/e2e-security-hardening-followup.spec.js`.

**This round's additional coverage:** The hardening file now also asserts
class-teacher batch parent-code generation skips linked foreign-class students,
parent score/stat reads ignore other students in the same class, score-appeal
second submissions after resolved/rejected history keep only one pending appeal,
and dashboard subject rankings/trends/analysis do not mix another course.

**Next concerns:** The next most valuable tests should target parent portal UI
state, parent-code expiry/rate-limit behavior under repeated invalid codes,
teacher-role parent-code policy (as distinct from class-teacher visibility),
student notification read-state isolation between parent and admin SPA, and
PostgreSQL-backed confirmation of the parent subject-scope query shape.

**Follow-up parent portal UI round:** The next hardening round added real
parent SPA coverage for code binding/login plus homework and notification lists
that must hide same-class elective content when the child is not enrolled in
that subject. The first browser run exposed a true E2E seed/front-end contract
bug: `/api/e2e/dev/reset-scenario` returned a parent code longer than the parent
login input's `maxlength=8`, so the SPA truncated the code and stayed on
`/login`. The seed now emits an 8-character code. Backend `hard61`-`hard68`
also cover invalid-code rate limiting, expired-code read denial, code rotation,
regular-teacher vs unrelated-teacher parent-code access, class-teacher linked
foreign-class denial, classwide-vs-subject parent read scoping, and revoke
expiry cleanup.

**Remaining risk after that round:** PostgreSQL-backed execution is still the
largest unclosed item. The new `pg21` guard asserts that parent homework and
notifications keep `subject_id IS NULL` rows while filtering subject-scoped rows
by the child's enrollments, but the local command skipped because
`TEST_DATABASE_URL` was not configured. The parent-code rate limiter remains
process-local and should not be treated as distributed brute-force protection.
The regular-teacher parent-code policy is now covered as current behavior, not
as final product approval. Notification read-state isolation between parent
portal and admin/student surfaces remains worth a dedicated browser-backed
round if parent read/unread UX grows beyond the current list-only parent API.

**Notification and parent-session follow-up round:** The next red-team batch
added backend `hard69`-`hard76` plus parent SPA cases 04-06. It found and fixed
three concrete issues. First, `POST /api/notifications/{id}/read` accepted an
existing notification id without proving the current JWT user could see that
notification, so hidden targeted or foreign-user notices could receive read
rows. It now reuses `_visible_notifications_query(...)` and returns 403 without
creating `notification_reads` for existing but invisible ids. Second, the
student notification visibility helper did not apply the same enrollment
subject-scope as parent notification reads, so same-class unenrolled elective
notifications could appear in student list/mark-all-read flows. Student
notification list, single read, and mark-all-read now require `subject_id IS
NULL` or an enrolled subject. Third, parent batch code generation processed
duplicate student ids independently, rotating the same code more than once in a
single request. The batch endpoint now deduplicates ids before authorization and
generation.

The browser-backed parent SPA round also verified that invalid codes do not
bind local storage, revoked stored codes clear the parent session and redirect
protected routes to `/login`, and student JWT read-state does not hide parent
portal notification list rows. Parent read-state remains list-only; add new
cross-surface tests if parent-side read/unread mutations are introduced.

**Subject-scoped broadcast follow-up round:** The next red-team batch added
backend `hard77`-`hard84` plus parent SPA cases 07-08. It found that
`GET /api/notifications?subject_id=...`, `/sync-status?subject_id=...`, and
`POST /api/notifications/mark-all-read?subject_id=...` treated every
`subject_id IS NULL` class broadcast as part of the course-scoped view after
course access was validated. That let another class's broadcast inflate totals,
appear in a course-scoped list, or receive a read row for a student/teacher who
was only looking at one course. The fix keeps course-subject notifications and
global broadcasts visible, but limits class broadcasts to classes linked to the
requested course through `subject_class_links`. The same tests also preserve
same-class broadcasts, global broadcasts, subject rows, and target-student
filters.

The parent SPA additions did not expose a new bug: invalid login attempts now
clear a stale existing parent binding, and protected routes clear partial
bindings that have a `parent_code` but no `student_id`.

**Multi-class notification audience follow-up round:** The next red-team batch
added backend `hard85`-`hard91` plus admin Playwright notification deep-tier
cases 16-18. It found that the previous subject-scoped broadcast fix still
treated every class linked to a multi-class required course as visible to
students and non-instructor class teachers. That let a student in class A see,
count, or mark read a `subject_id IS NULL` broadcast for linked class B after
requesting class A's course. The fix separates course-wide authority from
class-local audience: admin and assigned course teachers still see the whole
course-linked class scope, while students and non-instructor class teachers
only see their own class plus global rows. The browser tests also cover stale
`selected_course` cache and header badge convergence for this boundary.

**Global notification write-scope follow-up round:** The next red-team batch
added backend `hard92`-`hard101` plus admin Playwright notification deep-tier
cases 19-20. It found that teachers and class teachers could create
site-wide notifications by omitting both `subject_id` and `class_id`, and could
also update a class-scoped notice into the same global shape by clearing
`class_id`. Because global rows appear in unscoped notification streams for all
roles, this could inflate unrelated students' header badges or inject another
teacher's unscoped inbox. The router now treats global notification writes as
admin-only: non-admin staff must bind manual notifications to a course or class,
and cannot widen an existing scoped notice into global scope. Admin-created
global notices remain supported and are covered by backend and browser tests.

## Suggested Follow-Up Order

1. Investigate the dual-tab notification mark-all-read scenario until it is clearly classified as either a product race or a flaky test.
2. Reduce import-time and startup-time backend side effects.
3. Break down the LLM subsystem and heavy route modules into smaller, more testable pieces.
4. Decide the long-term fate of the root `app` compatibility layer.
5. Simplify the Playwright boot contract for Windows and document the canonical execution path.
6. Harden course enrollment creation so reconciliation cannot double-insert the same row (see P2 `course_enrollments` item above); re-validate on SQLite and Postgres.
7. Lock Element Plus locale (or E2E strategy) to avoid English message-box affordances in a Chinese UI.
8. After any API pagination limit change, grep the admin SPA for `page_size` and align client requests with server `le=` constraints.
9. For every new course-owned mutation, test `class_teacher` visibility without
   assigned-teacher ownership and require **403** plus unchanged data.
10. Confirm regular-teacher parent-code management policy, then add a regression
    that distinguishes intended course-teacher access from class-linked
    class-teacher visibility.
11. Re-run parent portal subject-scope coverage on PostgreSQL and add a parent
    SPA UI smoke when the separate parent frontend is next in scope.
12. Run `postgres.pytest.package` or `full.pytest.postgres` with a real
    `TEST_DATABASE_URL` to execute the new `pg21` parent subject-scope guard,
    then inspect query plans/index behavior for `subject_id IS NULL OR
    subject_id IN (...)` on realistic homework/notification volumes.
13. If parent notification read-state is added to the parent portal, add a
    cross-surface E2E that marks notifications read in parent SPA and verifies
    admin/student unread state does not leak or disappear across roles.
14. Add a PostgreSQL-backed run for notification visibility/read-state and
    parent-code batch dedup once `TEST_DATABASE_URL` is available; inspect
    query plans for student notification filters that combine class, target,
    and `subject_id IS NULL OR IN (...)`.
15. Continue probing parent-code abuse surfaces around distributed rate limits,
    code guessing telemetry, and stale browser state across multiple tabs or
    multiple children if the product later supports family switching.
16. Add PostgreSQL coverage for course-scoped notification broadcasts and
    inspect the query plan for the role-dependent predicate:
    `subject_id = course OR subject_id IS NULL`, plus class-local restrictions
    for students/class teachers and course-wide restrictions for admin/assigned
    teachers.
17. Browser coverage now exists for three multi-class notification badge
    samples, but a full `e2e-notification-sync-deep-tier.spec.js` run remains
    useful before release because only cases 16-18 were rerun in this round.
18. Continue probing cross-course notification read-state when a single teacher
    owns several multi-class courses and switches rapidly between them; the
    current tests focus on one multi-class required course.
19. Add direct UI composer coverage for notification scope controls. The current
    browser checks use direct API calls plus header badge assertions; a future
    UI regression could still expose a misleading "global" publish affordance to
    normal teachers if the form later adds such a selector.
20. Run PostgreSQL-backed notification authorization tests when a
    `TEST_DATABASE_URL` is available, especially around the global-row predicate
    combined with class, target-user, target-student, and course-scoped filters.

## What This Document Is Not

- It is not a confirmed bug list.
- It is not a substitute for issue tracking.
- It is not a claim that every listed item currently causes user-visible failure.

It is a high-signal memory of where the system felt weakest while subjected to real validation pressure.
