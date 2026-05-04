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
  inside cards;
- on desktop, the sidebar edge handle must hide the navigation rail completely
  and restore it without leaving the main content offset.

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
- after adding the desktop sidebar edge-handle guard: `5 passed`, runtime about
  `30s`;
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
- if the desktop sidebar handle case fails, inspect `Layout.vue` state
  separation between `isCollapsed` and `isSidebarHidden`, plus the persisted
  `wailearning-admin-sidebar-state` localStorage key;
- this maintained spec complements PostgreSQL-backed screenshot audits. It is a
  fast guard for the responsive layout contract, not a replacement for real
  browser observation when continuing the larger UI/UX optimization task.

## Sidebar Hidden / Pull-Out Interaction Follow-Up

The shared admin shell now supports a more explicit hide-and-pull interaction
for the sidebar in addition to the original icon-collapsed state.

Implemented behavior:

- desktop users can still use the in-sidebar circular collapse button to switch
  between expanded navigation and the icon-only rail;
- desktop users can use the fixed left-edge handle to hide the sidebar
  completely, allowing the main content container to start at the viewport edge;
- clicking the same edge handle restores the sidebar to the expanded state;
- desktop sidebar preference is persisted in localStorage under
  `wailearning-admin-sidebar-state`, with values conceptually matching
  `expanded`, `collapsed`, and `hidden`;
- mobile users keep the overlay drawer behavior from the responsive repair pass;
- on mobile, the same edge handle opens or closes the drawer and never reserves
  document-flow width;
- route changes close the mobile drawer so a navigation click does not leave the
  next page covered by the sidebar.

Implementation notes:

- `Layout.vue` now separates `isCollapsed` from `isSidebarHidden`; avoid
  re-merging those concepts into one boolean because "icon rail" and "fully
  hidden" have different layout implications;
- `sidebarWidth` returns `0px` only for mobile-closed or desktop-hidden states;
- the edge handle is a native `button` with `aria-label`, `title`, a stable
  `data-testid`, and an Element Plus arrow icon;
- the handle is deliberately small and rail-like rather than a text button, so
  it remains available without becoming another toolbar item;
- the handle position follows the current sidebar width on desktop and follows
  the drawer edge on mobile.

Validation:

- `tests/e2e/web-admin/ui-responsive-layout-regression.spec.js` includes a
  desktop handle test that verifies the sidebar width collapses to zero and the
  main container x-position returns to the viewport edge;
- the same spec still verifies the mobile course-page and table-heavy-page
  no-overflow invariants after the shell change.

## Course Materials Outline Expand / Collapse Follow-Up

The first maintained multi-level directory interaction now lives on the course
materials page:

- `apps/web/admin/src/views/Materials.vue`;
- maintained guard: `tests/e2e/web-admin/ui-materials-outline-regression.spec.js`.

Before this pass, the materials chapter tree used Element Plus `el-tree` with
`default-expand-all`, which made every branch open by default. That was workable
for small seeds, but it does not scale to course outlines with many chapters,
subchapters, and material references.

Implemented behavior:

- the chapter sidebar header now includes icon-only controls for "expand all"
  and "collapse all";
- both controls use native button semantics through Element Plus buttons,
  tooltips, `aria-label`, and stable `data-testid` hooks;
- the old root-chapter creation action remains available to teachers/admins in
  the same header action group;
- `default-expand-all` was removed;
- the tree now uses an explicit `expandedChapterKeys` state;
- expand/collapse events update `expandedChapterKeys`;
- the selected chapter path is expanded when the user selects a nested chapter
  or when a selected chapter is restored from page state;
- "collapse all" sets the expanded key set to an empty array. This matters
  because Element Plus treats entries in `default-expanded-keys` as nodes whose
  children are open; putting top-level ids in the array keeps their children
  visible and is not a true collapsed outline;
- "expand all" uses all chapter ids from the current tree;
- per-course outline state is persisted in localStorage under
  `wailearning-materials-expanded-chapters:<subject-id>`.

Validation:

- `ui-materials-outline-regression.spec.js` creates a parent and child chapter
  through the API for the seeded required course;
- the spec enters the seeded required course before visiting `/materials`,
  because teacher accounts can otherwise default to another course context;
- it verifies the parent and child are initially visible, collapse-all hides the
  child while leaving the parent reachable, expand-all restores the child, and a
  reload preserves the expanded state.

Maintenance guidance:

- do not restore `default-expand-all`; use explicit expanded-state management so
  large outlines remain scannable;
- if additional pages gain tree/outline controls, prefer the same interaction
  vocabulary: chevron-like expand/collapse icons, stable test ids, selected-path
  expansion, and per-context persistence;
- if a future mobile-specific materials layout is introduced, keep these outline
  controls available in the sidebar/drawer rather than hiding the tree state
  behind route changes.

## Course Materials Node-Level +/- Follow-Up

The follow-up pass keeps the existing explicit `expandedChapterKeys` state model
and adds a visible per-node affordance. The goal is not to create a second
outline implementation; it is to make the existing multi-level course-materials
tree discoverable to users who expect a `+` / `-` control beside expandable
items.

Implementation details:

- `apps/web/admin/src/views/Materials.vue` now renders the `el-tree` default
  slot with both `node` and `data` so the visual control can reflect the current
  Element Plus node state;
- parent nodes render a stable `button.chapter-node-toggle` before the chapter
  title;
- expanded parent nodes show the Element Plus `Minus` icon, collapsed parent
  nodes show the Element Plus `Plus` icon;
- leaf nodes render `chapter-node-toggle-spacer` so title alignment stays stable
  across mixed parent/leaf lists;
- the default Element Plus caret is hidden for this tree only, preventing two
  competing disclosure controls from appearing in the same row;
- clicking the `+` / `-` button calls `toggleChapterExpansion(data)` and stops
  propagation, so it does not select the chapter and does not trigger teacher
  management actions;
- clicking the chapter title still selects the chapter and expands the selected
  ancestor path through the existing `ensureSelectedChapterPathExpanded()`
  contract;
- the node-level toggle updates `expandedChapterKeys`, calls
  `syncTreeExpandedState()`, and persists the result under the same
  `wailearning-materials-expanded-chapters:<subject-id>` localStorage key used
  by the expand-all/collapse-all buttons;
- the per-node button exposes `aria-label`, `title`, and a stable
  `data-testid="materials-chapter-toggle-<chapter-id>"` hook.

Visual contract:

- the disclosure button is intentionally small but not text-like: it has a
  fixed `24px` square footprint, a `7px` radius, translucent blue background,
  light border, and a restrained shadow;
- hover uses a stronger blue tint, slightly higher shadow, and a small scale
  transform so the row has a tangible interactive response without causing the
  surrounding tree text to reflow;
- focus-visible has an explicit outline so keyboard users can operate the same
  control;
- the spacer keeps title x-position stable when sibling rows alternate between
  expandable and leaf chapters;
- the tree content keeps `min-height: 32px`, which is enough for dense desktop
  sidebar scanning while still giving the explicit icon button a reliable mobile
  tap target.

Regression guard:

- `tests/e2e/web-admin/ui-materials-outline-regression.spec.js` still verifies
  the bulk collapse/expand path;
- the same spec now also clicks the parent node's
  `materials-chapter-toggle-<id>` control, verifies the child is hidden, clicks
  it again, and verifies the child is visible;
- this matters because the node-level control and the bulk toolbar controls
  share `expandedChapterKeys`, and a future refactor must keep both entry
  points synchronized instead of allowing one of them to become a purely visual
  toggle.

Guidance for future multi-level content surfaces:

- prefer one explicit expansion state source per page or component;
- keep "select/open item" separate from "expand/collapse children" when the row
  also navigates or filters content;
- if a tree has bulk expand/collapse actions, reuse the same state and
  persistence contract for per-node toggles;
- provide a stable spacer for leaf rows when using custom disclosure controls;
- hide framework-native caret controls only inside the local tree scope, never
  globally;
- add `data-testid` hooks on the disclosure controls rather than asserting
  against icon SVG internals.

## Admin Radius Hierarchy Follow-Up

The admin SPA now has a small shared radius vocabulary for future visual work:

- `--wa-radius-xs: 4px`;
- `--wa-radius-sm: 6px`;
- `--wa-radius-md: 8px`;
- `--wa-radius-lg: 12px`;
- `--wa-radius-xl: 16px`;
- `--wa-radius-2xl: 20px`;
- `--wa-radius-pill: 999px`.

The tokens live in:

- `apps/web/admin/src/style.css`.

Reasoning:

- the admin app should not become uniformly rounded, because it is an
  information-dense teaching-management tool;
- table-heavy operational pages need restrained surfaces so rows, form fields,
  and actions remain easy to scan repeatedly;
- object-focused student surfaces, course cards, quota blocks, and course
  sections can be softer because they represent individual course objects or
  student-facing summary cards;
- utility controls such as icon buttons, tags, progress bars, and side handles
  can use circular or pill radii because their shapes carry control affordance
  rather than document structure.

Implemented hierarchy:

- Element Plus card shells default to `--wa-radius-lg` so form/table containers
  are no longer visually too square, but still read as dashboard work surfaces;
- standard buttons and form controls default to the smaller `--wa-radius-sm`;
- tags use the pill token, matching their status-label role;
- table internals stay almost square via `--wa-radius-xs`, because rounding each
  row or cell would weaken table alignment;
- settings section cards and the settings section navigator use `--wa-radius-lg`;
- settings navigator items and preview-image containers use `--wa-radius-md`;
- the login preview background uses `--wa-radius-xl`, while the nested login
  form box uses `--wa-radius-lg`, producing a visible parent/child radius
  distinction;
- materials course cover banners use `--wa-radius-xl`, while the chapter sidebar
  uses `--wa-radius-lg`;
- student course sections retain the larger `--wa-radius-2xl` on desktop and
  `--wa-radius-xl` on mobile because those areas are object collections, not
  dense table shells;
- individual course cards use `--wa-radius-xl`, with matching top cover radii.

Sidebar handle refinement:

- screenshot review after the radius pass showed that the desktop sidebar edge
  handle, while functional, could visually intrude into the main content title
  area when positioned fully outside the sidebar width;
- `Layout.vue` now keeps the handle half-embedded at the sidebar boundary:
  - desktop expanded/collapsed: `left: calc(<sidebarWidth> - 14px)`;
  - desktop hidden: `left: 0px`;
  - mobile open: `left: 226px` for a `240px` drawer;
  - mobile closed: `left: 0px`;
- this preserves the pull-out affordance without covering page headings.

Validation:

- `git diff --check` passed;
- `npm.cmd run build` passed, with only the existing Vite CJS API and large
  chunk warnings;
- PostgreSQL-backed screenshots were captured with
  `UI_UX_AUDIT_PREFIX=after-radius` and again with
  `UI_UX_AUDIT_PREFIX=after-radius-handle` after adjusting the sidebar handle;
- the reviewed screenshots included:
  - `after-radius-handle-admin-settings-postgres.png`;
  - `after-radius-handle-student-courses-postgres.png`;
  - `after-radius-handle-mobile-student-courses-postgres.png`;
- the screenshot review confirmed the new radius hierarchy is visible without
  making the operational pages look like card-heavy marketing screens, and the
  adjusted sidebar handle no longer overlaps the main page title area.

Maintenance guidance:

- prefer the shared `--wa-radius-*` tokens over new literal radius values;
- use `4px` to `8px` for small internal table/form details;
- use `12px` for standard dashboard shells and contained panels;
- use `16px` to `20px` only for object cards, visual previews, course sections,
  and mobile/student-facing collection surfaces;
- keep pill/circle radii for tags, progress bars, avatars, icon buttons, and
  explicit tool handles;
- do not globally force all Element Plus components to large radii;
- when future screenshots reveal a collision between a floating control and page
  content, adjust the control position first before increasing page padding.

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

## Admin Theme And Token Foundation

The next continuation pass addressed the previously open theme/token item
without attempting a page-by-page visual rewrite. The goal was to create a
working foundation that future agents can extend safely:

- blue remains the default theme;
- green, warm, and grayscale variants are now available;
- Element Plus primary color variables are connected to the shared theme tokens;
- core background, surface, text, border, state, shadow, radius, and type tokens
  now live in the global admin stylesheet;
- the main application shell, login default background, and student course home
  local variables now consume the shared token layer.

Files changed:

- `apps/web/admin/src/utils/theme.js`;
- `apps/web/admin/src/App.vue`;
- `apps/web/admin/src/style.css`;
- `apps/web/admin/src/views/Layout.vue`;
- `apps/web/admin/src/views/Login.vue`;
- `apps/web/admin/src/views/StudentCourseHome.vue`.

Runtime behavior:

- `App.vue` applies the theme to `document.documentElement.dataset.waTheme`;
- the accepted canonical theme names are `blue`, `green`, `warm`, and
  `grayscale`;
- aliases such as `default`, `primary`, `teal`, `emerald`, `orange`, `amber`,
  `neutral`, `gray`, and `grey` are normalized before application;
- system settings may provide `admin_theme`, `theme`, `theme_color`, or
  `color_theme`;
- `localStorage.wailearning-admin-theme` can temporarily override the system
  setting for inspection or local audit work.

Important boundary:

- this pass provides theme infrastructure and a few high-visibility consumers;
- it does not yet replace every hard-coded page-level color literal;
- it does not add a settings-page control for theme selection;
- it does not introduce dark mode;
- it intentionally avoids touching Chinese template text because PowerShell may
  display UTF-8 source as mojibake in this local environment.

Validation:

- `git diff --check` passed;
- `npm.cmd run build` passed, with only the existing Vite CJS API deprecation
  warning and large chunk warnings.

Maintenance guidance:

- use `--wa-color-primary-*` for brand/action emphasis;
- use `--wa-color-accent-*` for secondary contextual chips and non-primary
  highlights;
- use `--wa-color-text*`, `--wa-color-bg*`, `--wa-color-surface*`, and
  `--wa-border-*` before adding new literal slate/gray colors;
- keep page-specific semantic variables when a view already has them, but map
  them to global `--wa-*` tokens as done in `StudentCourseHome.vue`;
- when adding a user-facing theme picker later, persist one of the canonical
  values listed above and let `theme.js` handle normalization.

## Configurable Appearance Styles Follow-Up

The next continuation pass promoted the earlier token foundation into a
user-configurable appearance system. This section is intentionally detailed
because future agents should be able to extend or debug the appearance surface
without rediscovering the data-priority model, encoding constraints, and
screenshot validation workflow.

### Product model

The appearance system now has four layers:

1. Built-in system default behavior, currently `professional-blue`.
2. Official presets, maintained as recommended combinations.
3. A user's current unsaved custom combination, applied immediately in the
   browser for preview only.
4. A user's saved personal styles, owned by that user and named by that user.

Official presets are not the full design space. They are curated examples that
cover practical combinations of:

- `primary` color;
- `accent` color;
- `texture`;
- `shadow`;
- `transparency`;
- `radius`;
- `density`.

The custom model deliberately does not allow arbitrary CSS injection. It exposes
controlled tokens only, so user configuration can remain flexible without
letting invalid CSS, unreadable contrast, or layout-breaking values enter the
database.

### Effective style priority

The runtime priority is:

1. selected saved user style;
2. system default preset from `system_settings.appearance_default_preset`;
3. built-in fallback `professional-blue`.

The login page cannot know the user before authentication, so it can only use
public system settings. After login, `App.vue` fetches the logged-in user's
appearance state and reapplies the effective style. When a user switches a style
inside Personal Settings, the client applies the draft immediately so screenshot
review and human inspection show the real token result without waiting for a
full reload.

### Backend implementation

Files:

- `apps/backend/wailearning_backend/db/models.py`;
- `apps/backend/wailearning_backend/api/schemas.py`;
- `apps/backend/wailearning_backend/api/routers/appearance.py`;
- `apps/backend/wailearning_backend/api/routers/settings.py`;
- `apps/backend/wailearning_backend/bootstrap.py`;
- `apps/backend/wailearning_backend/main.py`.

New table:

```text
user_appearance_styles
  id
  user_id
  name
  source
  preset_key
  config
  is_selected
  created_at
  updated_at
```

Important database rules:

- `(user_id, name)` is unique, so one user cannot accidentally save two styles
  with the same visible name;
- different users may use the same style name;
- only one style should be selected per user. The router clears previous
  selected rows before selecting or creating a selected style;
- the config column stores the controlled appearance config as JSON;
- schema repair creates the table and indexes through `ensure_schema_updates()`;
- `DEFAULT_SYSTEM_SETTINGS` now seeds `appearance_default_preset`.

Route family:

```text
GET    /api/appearance/presets
GET    /api/appearance/me
POST   /api/appearance/me/styles
PUT    /api/appearance/me/styles/{style_id}
POST   /api/appearance/me/styles/{style_id}/select
POST   /api/appearance/me/use-system
DELETE /api/appearance/me/styles/{style_id}
```

The system settings router also exposes `appearance_default_preset` through
`GET /api/settings/public`. Admin `POST /api/settings/batch-update` now creates
missing keys instead of silently ignoring unknown keys, which matters for
existing deployments whose `system_settings` rows predate the appearance key.

### Frontend implementation

Files:

- `apps/web/admin/src/utils/theme.js`;
- `apps/web/admin/src/style.css`;
- `apps/web/admin/src/App.vue`;
- `apps/web/admin/src/stores/user.js`;
- `apps/web/admin/src/api/index.js`;
- `apps/web/admin/src/components/AppearanceStylePanel.vue`;
- `apps/web/admin/src/views/PersonalSettings.vue`;
- `apps/web/admin/src/views/Settings.vue`;
- `apps/web/admin/src/views/Layout.vue`.

`theme.js` now owns:

- official preset definitions;
- legacy theme alias compatibility (`blue`, `green`, `warm`, `grayscale`);
- appearance config normalization;
- effective style resolution from system settings plus user state;
- writing color, radius, shadow, transparency, texture, and density tokens to
  `document.documentElement`.

The root element receives data attributes:

```text
data-wa-theme
data-wa-texture
data-wa-shadow
data-wa-transparency
data-wa-radius
data-wa-density
```

The global stylesheet uses those attributes for:

- background texture overlays;
- density font-size adjustments;
- Element Plus primary-color variables;
- shared surface/object shadows;
- radius scale changes.

The Personal Settings page now contains:

- official preset cards with swatches;
- custom controls for color, texture, shadow, transparency, radius, and density;
- a preview surface that shows sidebar, toolbar, cards, and table-like rows;
- save-and-use behavior for named styles;
- one-session preview behavior that does not persist;
- saved style list with use, load, and delete actions;
- follow-system-default action.

The Settings page contains only the global default selector. Do not move personal
style management into admin system settings; that would mix system policy and
user preference in one surface.

### Official presets

Current official preset keys:

- `professional-blue`;
- `fresh-green`;
- `warm-amber`;
- `minimal-gray`;
- `academic-navy`;
- `high-contrast`.

The visual intent of each preset:

- `professional-blue`: default operational school-management look, blue primary
  plus cyan secondary signal, no texture, restrained shadow, balanced radius.
- `fresh-green`: green primary, blue accent, soft-paper texture, and softer
  radius. This should feel fresher without turning the whole app into one green
  surface.
- `warm-amber`: amber primary, teal accent, subtle grid texture, medium shadow,
  solid surfaces. This is intentionally warmer but must remain table-readable.
- `minimal-gray`: gray primary, violet accent, flat shadow, compact density, and
  smaller radii. This is the most utilitarian preset.
- `academic-navy`: navy primary with amber accent and fine texture. This is a
  formal academic variant.
- `high-contrast`: slate primary, red accent, solid surfaces, stronger shadows,
  and subtle radii. This is not a full dark mode; main content remains readable
  on light operational surfaces.

Maintenance guidance:

- add a new preset only when it demonstrates a genuinely useful combination;
- keep presets as configuration objects, not hand-coded CSS branches;
- avoid one-hue presets where primary, accent, background, and preview all sit
  in the same hue family;
- keep textures subtle enough that table rows, form fields, and long Chinese
  labels remain readable;
- do not make all cards very rounded just because a preset is soft. Dense admin
  surfaces still need table/form discipline.

### Sidebar edge handle refinement

The sidebar edge handle previously used fixed top offsets such as `96px` and
`88px`. After this pass it is vertically centered:

```css
top: 50%;
transform: translateY(-50%);
```

Hover/focus adds only the horizontal affordance:

```css
transform: translateY(-50%) translateX(2px);
```

This makes the pull handle read as a persistent edge control rather than a small
button competing with the page header/title area.

### Screenshot validation evidence

PostgreSQL-backed screenshot audit was run after implementation and again after
the final visual-state fixes:

```powershell
$env:PLAYWRIGHT_BROWSERS_PATH='<user-home>\AppData\Local\ms-playwright'
$env:UI_UX_AUDIT_PREFIX='appearance-final'
node .e2e-run\ui-ux-audit\postgres-ui-audit.cjs
```

The local ignored script was temporarily extended to capture:

- `appearance-final-admin-personal-appearance-postgres.png`;
- one screenshot per official preset;
- existing admin, teacher, student, and mobile audit pages.

Reviewed screenshots:

- `appearance-final-admin-personal-appearance-postgres.png`;
- `appearance-final-admin-appearance-professional-blue-postgres.png`;
- `appearance-final-admin-appearance-fresh-green-postgres.png`;
- `appearance-final-admin-appearance-warm-amber-postgres.png`;
- `appearance-final-admin-appearance-minimal-gray-postgres.png`;
- `appearance-final-admin-appearance-academic-navy-postgres.png`;
- `appearance-final-admin-appearance-high-contrast-postgres.png`;
- `appearance-final-admin-settings-postgres.png`;
- `appearance-final-mobile-student-courses-postgres.png`.

Observed final state:

- preset card highlighting follows the selected draft preset;
- the Personal Settings page is denser and no longer leaves the profile/avatar
  sections as oversized one-column cards on desktop;
- all official presets keep main content readable;
- textures are visible only as background atmosphere and do not invade table or
  form content;
- high contrast produces a stronger shell and controls while keeping the working
  surface light;
- the sidebar edge handle sits near the vertical center and no longer competes
  with page titles;
- the mobile student courses screenshot still avoids document-level horizontal
  overflow.

Artifacts remain ignored under `.e2e-run/` and must not be committed.

### Validation performed

Static and automated validation from this pass:

```powershell
git diff --check
& '<repo>\.venv\Scripts\python.exe' -m pytest tests\backend\user_profile\test_appearance_styles.py -q
cd apps\web\admin
npm.cmd run build
```

Results:

- `git diff --check` passed;
- backend appearance tests passed: `3 passed`;
- frontend production build passed;
- frontend build emitted only the existing Vite CJS API deprecation warning and
  large chunk warnings.

### Encoding and editing notes

This pass touched Vue files with existing Chinese UI text. The edits followed
the repository encoding policy:

- use patch-based structural edits;
- anchor around ASCII identifiers, component names, and stable test IDs when
  possible;
- avoid copying PowerShell-rendered Chinese text back into source;
- treat screenshot text as visual evidence, not as a source for rewriting
  strings.

Future agents extending this area should keep the same discipline. Appearance
work tends to touch text-heavy Vue files, so accidental mojibake is a real risk
if terminal-rendered Chinese is copied back into templates.

## Interaction Polish And Unified Quota Menu Pass

This follow-up pass extended the admin shell interaction model after the
appearance preset work.

Implemented behavior:

- The header user menu now opens on hover instead of requiring a click.
- The dropdown begins with a richer profile block that shows a larger avatar,
  display name, role, username, and an LLM token progress indicator.
- Student users load their own LLM quota summary through
  `GET /api/llm-settings/courses/student-quotas` when the menu opens.
- Non-student users see that LLM token quota is system-managed rather than
  course-managed.
- Sidebar menu items and top-context chips use subtle scale on hover. This is
  intentionally restrained so the navigation feels more responsive without
  shifting the page layout.
- Global Element Plus buttons now add a small text glow and shadow on hover,
  preserving readability for primary and plain buttons.

Screenshot validation evidence from this pass:

```powershell
$env:PLAYWRIGHT_BROWSERS_PATH='<user-home>\AppData\Local\ms-playwright'
$env:UI_UX_AUDIT_PREFIX='interaction-quota'
node .e2e-run\ui-ux-audit\postgres-ui-audit.cjs
```

Reviewed screenshot:

- `interaction-quota-admin-settings-postgres.png`

Observed state:

- the admin Settings page shows the LLM quota block as `LLM 用量与额度（全平台）`;
- quota timezone, character/token estimation, image-token estimation, default
  daily cap, and grading concurrency are visually grouped in one system-level
  form;
- the sidebar edge handle remains vertically centered;
- the sidebar and button hover styling does not create obvious layout overlap
  in the captured desktop settings view.

Quota wording in the UI now follows the unified-pool model:

- the student course page shows one daily LLM pool plus course attribution;
- the course LLM dialog no longer exposes course-level quota timezone or token
  estimation fields;
- the admin Settings page owns quota timezone, token estimation parameters,
  default student cap, and grading concurrency.

Important editing note:

- During this pass, `Layout.vue` was restored after a partial template edit
  risked writing terminal-rendered mojibake back into the file. Future work in
  this area should prefer small structural patches and should not copy Chinese
  strings from PowerShell output into Vue templates.

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
