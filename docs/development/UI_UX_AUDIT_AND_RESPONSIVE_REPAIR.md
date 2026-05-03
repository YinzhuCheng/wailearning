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
   - system identity;
   - login preview;
   - LLM endpoints;
   - global quota policy;
   - bulk quota override.
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

## Commit Hygiene For This Work

Do include:

- source changes under `apps/web/admin/src/views/`;
- this documentation file;
- documentation index links.

Do not include:

- `.e2e-run/`;
- Playwright screenshots;
- PostgreSQL binaries or data directories;
- Vite `dist/`;
- local logs;
- local handoff files.
