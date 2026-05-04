# UI/UX Audit And Responsive Repair Notes

## Purpose

This document records the current UI/UX audit workflow and the first responsive
repair pass for the admin SPA. It is written for future LLM coding agents first:
it intentionally preserves operational detail, environment assumptions,
validation evidence, and remaining follow-up context instead of compressing the
work into a short human-facing changelog.

The specific repair pass documented here targeted visual overflow and layout
misalignment found in PostgreSQL-backed Playwright screenshots. The highest-risk
failure was the student courses page on a 390 px mobile viewport: the dark
sidebar remained in the document flow at collapsed width, the main content was
compressed, and student course cards overflowed their white section container.

## Required Reading Before Continuing UI Work

Before continuing UI/UX work in this repository, read these files in order:

1. `README.md`
2. `docs/README.md`
3. `docs/architecture/REPOSITORY_STRUCTURE.md`
4. `docs/architecture/SYSTEM_OVERVIEW.md`
5. `docs/development/DEVELOPMENT_AND_TESTING.md`
6. `docs/development/TEST_EXECUTION_PITFALLS.md`
7. `docs/development/ENCODING_AND_MOJIBAKE_SAFETY.md`
8. this document

Rationale:

- the admin SPA is only one part of a larger FastAPI + Vue + PostgreSQL system;
- local artifact directories such as `.e2e-run/`, `frontend/`, `dist/`, and
  Playwright screenshots are not source layout;
- Windows + PowerShell can mis-render tracked UTF-8 Chinese text even when file
  content is valid, so do not copy terminal-rendered Chinese strings back into
  source files;
- serious browser UI evidence should use a PostgreSQL-backed backend, not the
  default SQLite-backed Playwright fast path, when the result is used as a
  production-aligned signal.

## Evidence Source And Scope

The UI observations in this pass came from real Playwright screenshots against:

- admin frontend: `apps/web/admin`;
- backend entrypoint: `apps.backend.wailearning_backend.main:app`;
- database: a disposable local PostgreSQL database;
- seed route: `POST /api/e2e/dev/reset-scenario`;
- roles observed: admin, teacher, and student;
- viewport sizes:
  - desktop pages around `1440 x 1000`;
  - mobile student courses page at `390 x 844`.

The audit did not rely on static code reading alone. Static inspection was used
to identify the implementation source of the screenshot failures, but browser
screenshots were the deciding evidence for layout behavior.

## Local Artifact Contract

The audit workflow creates local files under `.e2e-run/`. This directory is
ignored by git and must stay out of tracked source.

Common local artifact categories:

- local PostgreSQL binary runtime;
- local PostgreSQL data directory;
- PostgreSQL, backend, and Vite logs;
- Playwright screenshots;
- Playwright DOM/text snapshots;
- local handoff notes;
- one-off audit launch scripts.

Tracked documentation must not include machine-specific absolute paths. Use
portable placeholders such as:

- `<repo>`;
- `<user-home>`;
- `<artifact-dir>`;
- `<api-port>`;
- `<ui-port>`;
- `<postgres-port>`.

Local handoff files inside `.e2e-run/` may contain real paths when the next
operator is on the same machine and needs exact locations.

## PostgreSQL-Backed Screenshot Workflow

The recommended serious-audit shape is:

1. Start a throwaway PostgreSQL cluster or use a known disposable local
   PostgreSQL database.
2. Start the backend with `DATABASE_URL` pointing at that disposable database.
3. Enable only the guarded E2E seed route:
   - `E2E_DEV_SEED_ENABLED=true`;
   - `E2E_DEV_SEED_TOKEN=<test-token>`.
4. Disable unrelated runtime noise:
   - `INIT_DEFAULT_DATA=false`;
   - `ENABLE_LLM_GRADING_WORKER=false`.
5. Start Vite from `apps/web/admin` with `VITE_PROXY_TARGET` pointing at the
   backend.
6. Reset the scenario with the same E2E seed token.
7. Capture screenshots for the target role/page/viewport combinations.
8. Store screenshots under `.e2e-run/` and keep them untracked.

The local audit script used in this pass follows that shape. It supports a
filename prefix environment variable so before and after screenshots can coexist:

```powershell
$env:PLAYWRIGHT_BROWSERS_PATH='<user-home>\AppData\Local\ms-playwright'
$env:UI_UX_AUDIT_PREFIX='after'
node .e2e-run\ui-ux-audit\postgres-ui-audit.cjs
```

Notes for future agents:

- `.e2e-run\ui-ux-audit\postgres-ui-audit.cjs` is a local ignored script, not a
  maintained test suite file.
- The script starts PostgreSQL, the backend, Vite, and Playwright in one process
  lifetime because background processes were unreliable across separate
  sandboxed tool calls on Windows.
- In the observed Windows automation environment, Node child-process spawning
  required execution outside the default sandbox; otherwise Vite, esbuild, or
  Playwright can fail with `spawn EPERM`.
- The local script defaults to `UI_UX_AUDIT_PREFIX=before` when the variable is
  absent. Set the prefix explicitly for after screenshots so the original
  baseline remains available.

## Screenshot Set Used In This Repair Pass

The baseline and after screenshots used this naming pattern:

```text
<prefix>-login-postgres.png
<prefix>-admin-students-postgres.png
<prefix>-admin-settings-postgres.png
<prefix>-teacher-dashboard-postgres.png
<prefix>-teacher-homework-postgres.png
<prefix>-student-courses-postgres.png
<prefix>-student-course-home-postgres.png
<prefix>-mobile-student-courses-postgres.png
```

The matching JSON snapshots use the same base names with `.json`.

The highest-value comparison in this pass was:

- `before-mobile-student-courses-postgres.png`;
- `after-mobile-student-courses-postgres.png`.

## Findings From The Baseline Mobile Screenshot

The original mobile student courses screenshot showed these concrete issues:

1. The dark left sidebar still consumed layout width at `390 px`.
2. The main content was squeezed into the remaining width instead of using the
   full viewport.
3. The current-course header chip had very little horizontal room for a long
   seeded course name.
4. The LLM quota card remained readable, but it was unnecessarily cramped by the
   sidebar.
5. The school-wide course catalog table collapsed poorly on mobile.
6. The active course card overflowed horizontally from its white section
   container.
7. Long seeded course names and metadata were able to force awkward wrapping
   without enough `min-width: 0` protection.
8. The primary course action button was visually pushed toward the edge and in
   the baseline screenshot appeared partially inaccessible.

The observed cause was not one single CSS rule. It was the combination of:

- `Layout.vue` treating mobile as the same collapsed-sidebar layout used on
  desktop;
- flex/grid children missing `min-width: 0`;
- table components being allowed to participate in page-level width calculation;
- course cards using `minmax(280px, 1fr)` and internal horizontal title/tag
  layout without a small-screen fallback;
- long seeded names exposing width assumptions that shorter hand-entered names
  might hide.

## Source Changes Made

### `apps/web/admin/src/views/Layout.vue`

The shared shell was updated so mobile side navigation no longer consumes normal
document-flow width.

Key changes:

- added `isMobile`;
- added computed `sidebarWidth`;
- mobile width now becomes `0px` when collapsed and `240px` when open;
- desktop behavior remains `72px` collapsed and `240px` expanded;
- added a mobile menu button in the header;
- added an overlay backdrop when the mobile sidebar is open;
- made the mobile sidebar fixed-position with a shadow;
- added `min-width: 0` to the main nested container, header groups, and main
  content;
- constrained and ellipsized long current-course/class context text.

Behavioral intent:

- mobile users should get the full viewport width for content by default;
- the sidebar should be available as an overlay, not as a permanent column;
- desktop users should keep the existing collapsible sidebar behavior.

### `apps/web/admin/src/views/MyCourses.vue`

The student/teacher course selection page received the largest responsive
repair because it contained the visible mobile overflow.

Key changes:

- added page-level `overflow-x: hidden` and `min-width: 0` protection;
- made quota card header and quota rows wrap safely;
- kept the desktop course catalog table but prevented it from expanding the
  page width;
- added a mobile-only course catalog card list;
- hid the Element Plus table on mobile and displayed mobile catalog cards
  instead;
- changed course grid columns from `minmax(280px, 1fr)` to
  `minmax(min(280px, 100%), 1fr)`;
- added `min-width: 0` and `overflow-wrap: anywhere` to card titles, metadata,
  descriptions, and quota labels;
- stacked course-card title/tags on mobile;
- made course action buttons fill the card width on mobile.

Behavioral intent:

- desktop keeps the information-dense table;
- mobile gets scannable course cards with the same enroll/drop actions;
- long seeded names are treated as realistic stress input, not as an excuse to
  let layout overflow.

### `apps/web/admin/src/views/Homework.vue`

The teacher homework page was not the primary overflow failure, but the baseline
screenshot showed a weak empty table experience.

Key changes:

- added `homework-list-card` around the homework table;
- constrained the table to card-internal horizontal scrolling;
- added a custom table empty slot;
- teacher empty state now explains that submissions, grading tasks, and batch
  policies will appear after the first assignment;
- teacher empty state includes a primary `homework-empty-create` button;
- student empty state uses student-appropriate waiting copy;
- mobile card padding is reduced and page overflow is constrained.

Behavioral intent:

- empty teacher pages should still explain the next useful action;
- wide assignment tables should not break the page container on smaller screens.

### `apps/web/admin/src/views/Settings.vue`

The admin settings page is long and dense. This pass did not perform a full
tabbed information-architecture refactor, but it added containment rules so the
existing layout behaves better across widths.

Key changes:

- added page-level `min-width: 0` and `overflow-x: hidden`;
- constrained card body, form, upload blocks, preview image, and preview login
  box widths;
- made card headers wrap instead of forcing horizontal overflow;
- made LLM preset tables scroll within the card body;
- changed mobile form layout so labels and controls stack vertically;
- reduced mobile settings padding;
- made login preview height flexible on mobile.

Behavioral intent:

- preserve the existing admin precision and detailed settings surface;
- prevent tables, preview cards, and long headers from creating page-level
  horizontal overflow;
- leave a larger settings-page restructuring for a dedicated pass.

### Follow-up: settings section navigation

A subsequent incremental pass added a compact settings-section navigator at the
top of `Settings.vue`.

Key changes:

- added four section buttons:
  - system identity;
  - login preview;
  - LLM endpoint presets;
  - LLM quota and usage policy;
- assigned stable section ids to the existing settings cards;
- added a `settingsSections` metadata array and `scrollToSettingsSection`
  helper;
- used `scrollIntoView({ behavior: 'smooth', block: 'start' })` for in-page
  jumps;
- kept the controls as native `<button>` elements instead of turning the page
  into a tabbed state machine;
- kept all existing settings content visible in the document flow;
- added sticky, compact, responsive styling so desktop uses four columns and
  mobile uses two columns.

Reasoning:

- the settings page is an operational surface, so the change should help
  scanning without hiding detailed configuration behind new state;
- anchoring existing cards avoids changing data loading, form submission, LLM
  preset validation, or quota behavior;
- native buttons preserve keyboard reachability without introducing Element Plus
  tab state that would need additional persistence and test coverage;
- this is an intermediate improvement, not a substitute for a future full
  settings information-architecture pass.

## Validation Performed

### Static patch validation

Run from repository root:

```powershell
git diff --check
```

Result:

- passed.

### PostgreSQL-backed Playwright screenshot audit

Run from repository root with local Playwright browser cache and the local
ignored audit script:

```powershell
$env:PLAYWRIGHT_BROWSERS_PATH='<user-home>\AppData\Local\ms-playwright'
$env:UI_UX_AUDIT_PREFIX='after'
node .e2e-run\ui-ux-audit\postgres-ui-audit.cjs
```

Result:

- PostgreSQL started on the local audit port;
- backend started on the local audit API port;
- Vite started on the local audit UI port;
- E2E seed reset succeeded;
- all eight after screenshots were captured.

Observed after-state:

- the `390 x 844` student courses page no longer has a persistent left sidebar
  consuming width;
- active course cards remain within their section container;
- school-wide course catalog uses mobile cards instead of a crushed table;
- the settings page remains long but no longer depends on page-level overflow
  for its LLM table;
- the settings page now exposes a compact top section navigator for system
  identity, login preview, LLM endpoints, and quota policy;
- the teacher homework page shows a purposeful empty state with a primary next
  action.

### Admin frontend production build

Run from `apps/web/admin`:

```powershell
npm.cmd run build
```

Result:

- Vite build completed successfully;
- `2363` modules transformed;
- build emitted only existing category warnings:
  - Vite CJS Node API deprecation warning;
  - large chunk warnings over `500 kB`.

The warnings were not introduced as functional build failures by this responsive
repair pass. They remain possible future optimization work, especially around
large shared chunks and dependencies such as rich markdown rendering and xlsx.

## What This Pass Does Not Claim

This pass does not claim a full UI redesign.

It does not implement:

- the requested blue/green/warm/grayscale theme system;
- a full settings-page tabs or section-navigation refactor;
- a new global design-token architecture;
- a full audit of every admin page at every breakpoint;
- accessibility remediation beyond layout and basic responsive containment;
- parent portal UI work.

It does claim that the specific screenshot-observed mobile overflow and card
misalignment problems on the student courses page were addressed and verified
with after screenshots.

## Remaining Follow-Ups

Recommended next UI/UX work, in order:

1. Formalize admin SPA design tokens:
   - spacing scale;
   - radius scale capped at practical dashboard values;
   - shadow levels;
   - typography sizes for dashboard surfaces;
   - status colors;
   - theme variants for blue, green, warm, and grayscale.
2. Refactor settings into tabs or anchored sections:
   - a compact anchored-section navigator now exists;
   - remaining work is a deeper information-architecture pass if maintainers
     want progressive disclosure, per-section save affordances, or persistent
     active-section state;
   - do not remove detailed LLM explanations when restructuring, because they
     encode operational constraints future agents need.
3. Add maintained Playwright assertions for the mobile layout regressions:
   - mobile sidebar does not reduce main content width when closed;
   - `.course-card` bounding boxes stay within viewport;
   - mobile catalog cards are visible on `/courses`;
   - desktop catalog table remains visible on desktop.
4. Review additional table-heavy pages for the same pattern:
   - `Students.vue`;
   - `Subjects.vue`;
   - `Users.vue`;
   - `Scores.vue`;
   - `Attendance.vue`.
5. Consider a maintained screenshot smoke script or Playwright spec instead of
   relying on a local ignored audit script for future visual checks.
6. Continue encoding cleanup separately. This pass deliberately avoided touching
   existing mojibake-like tracked Chinese strings except where new UI text was
   necessary and inserted directly through patching.

## Incremental Pitfalls And Resolutions From The Follow-Up Pass

This section records additional pitfalls encountered after the first responsive
repair commit. It is intentionally additive and does not replace the earlier
PostgreSQL-backed audit notes in this document or
`docs/development/TEST_EXECUTION_PITFALLS.md`.

### Pitfall: the local audit script originally overwrote baseline screenshots

Observed:

- the local ignored screenshot script initially hard-coded names such as
  `before-mobile-student-courses-postgres.png`;
- rerunning it after code changes would overwrite the baseline evidence unless
  the operator manually copied files elsewhere first.

Resolution:

- the local ignored script under `.e2e-run/` was changed to accept an
  environment-controlled screenshot prefix;
- use `UI_UX_AUDIT_PREFIX=after` for post-change screenshots;
- keep `before-*` and `after-*` screenshots side by side in the ignored artifact
  directory;
- do not track the script or screenshots unless maintainers deliberately promote
  the workflow into a maintained test or tool.

Portable command shape:

```powershell
$env:PLAYWRIGHT_BROWSERS_PATH='<user-home>\AppData\Local\ms-playwright'
$env:UI_UX_AUDIT_PREFIX='after'
node .e2e-run\ui-ux-audit\postgres-ui-audit.cjs
```

### Pitfall: desktop containment fixes were not enough for mobile course catalog UX

Observed:

- adding `overflow-x: auto` to the course catalog table stopped page-level
  horizontal overflow;
- however, on a `390 px` mobile viewport, the catalog was still a compressed
  table and was hard to scan;
- the page was technically contained, but the user experience remained too close
  to "desktop table squeezed into a phone."

Resolution:

- the desktop Element Plus table was retained for information-dense desktop use;
- a mobile-only catalog card list was added below the table markup;
- CSS hides the table on mobile and shows the card list instead;
- the card list reuses the same enrollment/drop business logic already used by
  the table, avoiding duplicate API behavior;
- mobile course names, class names, teacher names, and enrollment hints use
  `min-width: 0` plus wrapping to handle seeded long names.

### Pitfall: settings-page density needed navigation before a full IA rewrite

Observed:

- the settings page contains system identity controls, login preview, LLM
  endpoint presets, quota policy, and bulk quota override in one long document;
- a full tabbed rewrite would be larger and would introduce new state-management
  and test coverage requirements;
- hiding detailed LLM explanations would be harmful because those explanations
  encode operational constraints future agents need.

Resolution:

- a compact anchored section navigator was added at the top of `Settings.vue`;
- existing cards stayed in the document flow;
- each card received a stable section id;
- native `<button>` controls call `scrollIntoView` for smooth in-page jumps;
- the navigator uses four columns on desktop and two columns on mobile;
- this improves scanability without changing API calls, save behavior, LLM
  preset validation, or quota behavior.

### Pitfall: Vite/esbuild build validation can fail under restricted process spawning

Observed:

- `npm.cmd run build` can fail in the default restricted execution environment
  with `spawn EPERM` while loading Vite/esbuild;
- the failure is an execution-environment problem, not direct evidence of a
  Vue/CSS compile error.

Resolution:

- rerun the same build command in the approved execution context when validation
  matters;
- treat a successful production build as the syntax/compile gate for Vue template
  and CSS changes;
- continue to note large chunk warnings separately from build failures.

Validated result:

- `npm.cmd run build` completed successfully after the responsive and settings
  navigation changes;
- the build emitted only existing category warnings:
  - Vite CJS Node API deprecation;
  - chunks larger than `500 kB`.

### Pitfall: Windows PowerShell output can display mojibake for tracked Chinese text

Observed:

- reading Vue files through PowerShell can display Chinese text as mojibake even
  when the underlying tracked file content is valid;
- patching around those strings by copying terminal output risks corrupting
  source text.

Resolution:

- avoid rewriting existing Chinese copy when the task is unrelated to encoding
  cleanup;
- anchor patches on ASCII identifiers, class names, component names, ids,
  `data-testid` values, and nearby stable structure;
- when new UI text is necessary, insert it deliberately through patching rather
  than copying from terminal-rendered existing text;
- leave broader mojibake cleanup for a dedicated encoding-safe task.

### Pitfall: local artifact paths are useful for handoff but unsafe for tracked docs

Observed:

- future local agents need exact screenshot, PostgreSQL runtime, browser cache,
  and handoff paths to resume quickly on the same machine;
- tracked documentation should not expose user-specific absolute paths.

Resolution:

- tracked docs use placeholders such as `<repo>`, `<user-home>`,
  `<artifact-dir>`, `<api-port>`, and `<ui-port>`;
- local handoff documents under `.e2e-run/` may include exact absolute paths;
- `.e2e-run/`, Vite `dist/`, logs, screenshots, PostgreSQL binaries, and local
  data directories remain ignored and must not be staged.

## Maintained Responsive Regression Spec

The screenshot audit remains useful for visual inspection, but the mobile
overflow repairs now also have a maintained Playwright spec:

- `tests/e2e/web-admin/ui-responsive-layout-regression.spec.js`

This spec is intentionally narrow. It does not perform screenshot comparison and
does not attempt to certify every visual state of the admin SPA. It checks the
layout invariants that failed in the original mobile screenshot:

- on a `390 x 844` mobile viewport, the collapsed sidebar must not reserve
  document-flow width;
- the page must not have document-level horizontal overflow;
- visible `article.course-card` boxes must remain within the viewport;
- visible `.catalog-mobile-item` boxes must remain within the viewport;
- the mobile course catalog card list must be visible while the desktop Element
  Plus catalog table is hidden;
- on a desktop viewport, the Element Plus catalog table must remain visible and
  the mobile card list must remain hidden;
- on a `390 x 844` mobile viewport, the table-heavy `/students`, `/users`,
  `/subjects`, `/scores`, and `/attendance` pages must not create document-level
  horizontal overflow after their wide table or grid surfaces are contained
  inside cards.

Preferred targeted command from `apps/web/admin`:

```powershell
$env:PLAYWRIGHT_BROWSERS_PATH='<user-home>\AppData\Local\ms-playwright'
$env:E2E_API_PORT='8112'
$env:E2E_UI_PORT='3112'
npx.cmd playwright test ui-responsive-layout-regression.spec.js
```

Why the example uses isolated ports:

- the default managed Playwright ports in this branch are `8012` for the API and
  `3012` for the admin UI;
- on Windows, stale server state or readiness timing can make those defaults
  fail before any test body runs;
- in the validation session that added this spec, the default-port run reached
  the approved execution context but timed out waiting for `webServer` health,
  while the same spec passed on isolated ports `8112` and `3112`.

Validated result in the adding session:

- initial responsive-course version: `3 passed`, runtime about `17s`;
- after adding the table-heavy page guard: `4 passed`, runtime about `20s`;
- only the existing Vite CJS Node API deprecation warning was emitted by the
  web server.

Interpretation guidance:

- if this spec fails inside the default sandbox with `spawn EPERM`, rerun in the
  approved execution context before diagnosing product code;
- if this spec times out waiting for `webServer` before tests start, check stale
  ports and rerun with isolated `E2E_API_PORT` / `E2E_UI_PORT`;
- if the tests start and then fail on bounding boxes, overflow, or visibility,
  treat that as a real regression candidate in `Layout.vue` or `MyCourses.vue`;
- if the table-heavy page case fails only on one route, inspect that route's
  outer page container, card body containment, toolbar wrapping, and any
  fixed-width grid/table implementation before changing global layout;
- this maintained spec complements PostgreSQL-backed screenshot audits. It is a
  fast guard for the responsive layout contract, not a replacement for real
  browser observation when continuing the larger UI/UX optimization task.

## Table-Heavy Page Containment Follow-Up

After the course-page mobile repair, the next broad responsive risk was the
family of admin/teacher pages whose primary surface is a wide Element Plus table
or custom grid:

- `apps/web/admin/src/views/Students.vue`;
- `apps/web/admin/src/views/Users.vue`;
- `apps/web/admin/src/views/Subjects.vue`;
- `apps/web/admin/src/views/Scores.vue`;
- `apps/web/admin/src/views/Attendance.vue`.

The first follow-up pass deliberately avoided replacing these tables with
mobile-specific card lists. The goal was narrower: prevent any single wide data
surface from increasing the document width while preserving the desktop
information architecture and existing table behavior.

Conservative containment changes applied:

- page roots now use `min-width: 0` plus `overflow-x: hidden`;
- page-owned `el-card` instances now have `min-width: 0`;
- page-owned `el-card__body` containers now allow horizontal scrolling inside
  the card instead of letting tables push the whole page wider;
- mobile page padding was reduced to match the responsive course/settings work;
- selected toolbar/header rows gained `min-width: 0`, wrapping, or stretched
  mobile alignment so action clusters do not force the viewport wider;
- the attendance sheet keeps its intentionally wide grid, but `.sheet-scroll`
  is explicitly capped to `max-width: 100%` and scrolls internally.

Important limitation:

- this is a containment pass, not a full mobile information-architecture pass;
- some pages may still deserve mobile-native card/list representations later,
  especially if the table is hard to scan on a phone;
- when making that deeper change, preserve the same business actions and stable
  `data-testid` hooks used by the existing E2E suite.

## Commit Hygiene For This Work

Do include:

- source changes under `apps/web/admin/src/views/`;
- maintained Playwright specs under `tests/e2e/web-admin/` when a local
  screenshot finding is promoted into a regression guard;
- this documentation file;
- documentation index links.

Do not include:

- `.e2e-run/`;
- Playwright screenshots;
- PostgreSQL binaries or data directories;
- Vite `dist/`;
- local logs;
- local handoff files.
