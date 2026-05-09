# Course Learning UI Beautify Handoff - 2026-05-10

This handoff records the current state of the `cursor/beautify-ui` workstream
after the course-learning UI beautification pass. It is intended for the next
agent to continue without rediscovering the same layout, validation, and
Playwright cleanup details.

## Branch And Commit

- Worktree: `cursor/beautify-ui`
- Branch: `cursor/beautify-ui`
- Latest pushed commit: `e72cedf feat: beautify course learning views`
- Worktree state after push: clean
- Remote push: completed to `origin/cursor/beautify-ui`

Local screenshots, run logs, and uploaded reference images live under
`.agent-run/` and must stay local-only. Do not commit `.agent-run/` contents.

## User Direction

The user asked to finish the learning-notes beautification and then migrate the
useful parts to the materials/course-resource area where the UI concepts are
similar. The user also explicitly pointed out that screenshots should be used
frequently to compare layout results.

The most important design feedback from the user:

- Some entries looked too left-aligned compared with the better centered
  screenshot.
- Some title areas and content boxes did not fill the available layout well.
- Different sections did not share a consistent visual language.
- Titles should use more consistent sizing.
- The short explanatory subtitle under every title is not preferred. A future
  dedicated help button or help page is preferred over repeated inline helper
  copy.
- Buttons placed under the title are often more visible than buttons hidden in
  the top-right corner, but this should be decided per case rather than forced
  globally.
- Materials textbook/course catalogs should also support collapse/expand where
  the content can become dense.

## What Was Implemented In This Round

The pushed commit focused on the student-facing course-learning surfaces:

- `apps/web/admin/src/views/LearningNotes.vue`
  - Reworked the learning-notes workspace into a more polished, centered,
    three-column learning surface.
  - Improved note list, note reader/editor, outline/resource sections,
    discussion entry points, and default-private note creation presentation.
  - Restored test-facing tab semantics after an earlier segmented-control
    mismatch was found by Playwright.
  - Suppressed duplicate Markdown title rendering where the note title was
    already shown by the surrounding UI.

- `apps/web/admin/src/views/Materials.vue`
  - Brought the materials area closer to the learning-notes visual language.
  - Restored and stabilized the course-cover banner after a regression was
    found during Playwright target work.
  - Adjusted selectors and visual structure around material cards, dialogs, and
    discussion entry points.

- `apps/web/admin/src/views/MaterialRead.vue`
  - Polished the material reader page and navigation affordances.
  - Aligned reader presentation with the Markdown/LaTeX rendering direction used
    by notes and course discussions.

- `apps/web/admin/src/views/StudentCourseHome.vue`
  - Tuned the course-home learning surface so it fits the updated materials and
    notes treatment.

- `apps/web/admin/src/components/CourseDiscussionPanel.vue`
  - Stabilized the collapsed composer, Markdown/LaTeX preview toggle, long-row
    expansion behavior, and selector expectations for course discussion flows.

- `tests/e2e/web-admin/e2e-course-ui-markdown-reader.spec.js`
  - Updated stale expectations for material reader buttons, collapsed
    discussion composer behavior, preview toggle flow, and long-row expansion.

- `tests/e2e/web-admin/e2e-discussion-cover-llm-tier3.spec.js`
  - Updated stale discussion pagination and composer selectors.
  - Preserved course-cover assertions after the materials banner was restored.

- `docs/development/TEST_EXECUTION_LEDGER.md`
- `docs/development/TEST_EXECUTION_SUMMARY.md`
  - Recorded the observed build, static checks, and Playwright timeout results.
  - Playwright runs were intentionally recorded as `timed out`, not `passed`,
    because the test bodies reached `ok` but the command did not exit cleanly.

## Current UI State

The core beautification pass is implemented and pushed. The current UI direction
is usable and visually closer to the user's preferred screenshots, but it should
not be considered complete. The next pass should specifically look for
cross-page consistency and density problems.

Areas that looked improved in this round:

- Learning notes now read more like a focused learning workspace instead of a
  plain CRUD page.
- Notes, materials, material reader, course home, and discussions now share more
  visual vocabulary.
- Markdown and LaTeX rendering flows are more consistent across notes,
  materials, and discussions.
- Course-cover display was restored in materials after being accidentally
  weakened during layout work.

Areas still needing deliberate visual review:

- The materials textbook/catalog area should get explicit collapse/expand
  behavior for dense course outline/resource lists.
- Repeated title/subtitle/header patterns should be audited. The user's
  preference is to avoid inline explanatory subtitle text when it adds noise.
- Button placement should be made consistent by intent:
  - primary create/edit/action buttons can often sit under the title for
    visibility;
  - small utilities, close buttons, filters, or low-frequency controls may stay
    in the top-right when that better preserves scanability.
- Centering and content width should be reviewed across all item types. Some
  entries can still feel underfilled if their title and body containers do not
  occupy the layout consistently.
- Title scale, card padding, empty states, and section headers should be checked
  side by side across notes, materials, course home, reader, and discussions.

## Recommended Next UI Plan

Start the next round with screenshots, not code edits. Use desktop and at least
one narrower viewport. Compare the current pages against the user's reference
images in `.agent-run/uploads/`.

Recommended sequence:

1. Capture current screenshots for:
   - learning notes list/detail/editor state;
   - public/private note tabs;
   - copied course outline/resources inside a note;
   - materials course catalog;
   - material detail dialog;
   - material reader;
   - student course home;
   - course discussion panel in collapsed composer and preview modes.

2. Audit visual consistency:
   - page title size and placement;
   - whether helper copy under titles is actually useful;
   - primary action placement;
   - card width and content alignment;
   - outline/resource row styling;
   - Markdown body width, spacing, and heading hierarchy;
   - empty/loading/error states.

3. Implement materials collapse/expand:
   - add collapse/expand controls to dense textbook/course catalog sections;
   - persist purely local UI state if needed, but avoid backend changes unless a
     product requirement appears;
   - make collapsed rows still informative enough to scan;
   - keep keyboard/click targets stable for Playwright.

4. Normalize note/material shared patterns:
   - consider a shared local section-header or toolbar pattern only if it
     reduces duplication and matches the current code style;
   - do not introduce a broad design-system refactor unless the duplication
     becomes hard to maintain;
   - prefer small, scoped component extraction over sweeping rewrites.

5. Re-screenshot after each visual edit:
   - compare alignment against the reference where screenshot `2.png` looked
     better than `1.png`;
   - check that the layout remains centered and does not collapse into a
     left-heavy column;
   - check mobile/narrow widths for overflow and text collision.

## Validation Already Performed

Build and static validation:

- `npm.cmd run build` from `apps/web/admin`
  - Passed after the final UI polish round.
  - Known warnings remained: Vite CJS Node API deprecation and large bundle
    chunk-size warnings.

- `git diff --check`
  - Passed.

- `python ops/scripts/dev/check_text_encoding.py ...`
  - Passed for the changed Vue, Playwright, and documentation files.
  - Result recorded as `scanned=9 decode_errors=0 suspicious=0`.

Playwright targets:

- `npx.cmd playwright test e2e-course-ui-markdown-reader.spec.js --project=chromium`
  - All 12 test bodies reported `ok`.
  - The command timed out while managed `webServer` cleanup was happening.
  - Ledger result: `timed out`.

- `npx.cmd playwright test e2e-discussion-cover-llm-tier3.spec.js --project=chromium`
  - All 15 test bodies reported `ok`.
  - The command timed out while managed `webServer` cleanup was happening.
  - Ledger result: `timed out`.

- `npx.cmd playwright test e2e-learning-notes-attendance-cover-tier20.spec.js --project=chromium`
  - All 20 test bodies reported `ok`.
  - The command timed out while managed `webServer` cleanup was happening.
  - A previous run noted that ports `8012` and `3012` had no remaining
    listeners afterward, but do not generalize that observation without
    checking each run.
  - Ledger result: `timed out`.

Important validation interpretation:

- These Playwright runs are useful evidence that the browser assertions reached
  `ok`.
- They are not passing target results because the commands did not exit
  normally.
- Future agents must not change the ledger to `passed` unless a rerun exits
  with a real success status.

## Playwright Cleanup Timeout Finding

Update after follow-up triage on 2026-05-10: the timeout is confirmed as a
Playwright managed-server teardown issue on Windows, not a direct UI assertion
failure. With `DEBUG=pw:webserver`, a focused rerun reached the final test `ok`
line and then stopped at:

```text
pw:webserver Terminating the WebServer
```

It never reached `Terminated the WebServer` before the outer command timeout.
Disabling the real grading worker did not fix the managed `webServer` hang.

A Windows-local workaround is now available:

```powershell
cd apps\web\admin
$env:E2E_USE_REAL_WORKER='false'
npm.cmd run test:e2e:external -- e2e-course-ui-markdown-reader.spec.js --project=chromium
```

This runner starts the API and Vite itself, runs Playwright with
`PLAYWRIGHT_USE_EXTERNAL_SERVERS=true`, then kills only the processes it
started. It bypasses Playwright's managed `webServer` teardown path.

Observed successful reruns after adding the runner:

- `npm.cmd run test:e2e:external -- e2e-course-ui-markdown-reader.spec.js --project=chromium`
  - `12 passed (54.2s)`, command exited `0`.
- `npm.cmd run test:e2e:external -- e2e-discussion-cover-llm-tier3.spec.js --project=chromium`
  - `15 passed (1.2m)`, command exited `0`.
- Post-run port checks showed no listeners on `8012` or `3012`.

The original plain `npx.cmd playwright test ...` managed-server path may still
hang locally on Windows until Playwright's teardown behavior or the local
process topology changes.

Relevant config:

- `apps/web/admin/playwright.config.cjs`
  - Starts backend and frontend through Playwright `webServer` unless
    `PLAYWRIGHT_USE_EXTERNAL_SERVERS=true`.
  - Backend default port: `8012`
  - Frontend default port: `3012`
  - Windows managed-server commands now use Playwright `cwd` and `env` fields
    instead of embedding `set ... && cd ...` chains in the command string.
  - Managed-server child environments force `DEBUG=false` so Playwright
    diagnostic `DEBUG=pw:webserver` does not leak into the backend Pydantic
    boolean `DEBUG` setting.
  - `reuseExistingServer` is true locally because it is set to `!process.env.CI`.
  - `ENABLE_LLM_GRADING_WORKER` is true by default unless
    `E2E_USE_REAL_WORKER=false`.

Likely causes:

- On Windows, Playwright 1.59 managed `webServer` force-kills the spawned
  process tree and then awaits the spawned process `close` event.
- In this repo's local Windows run, the ports and child server processes can be
  gone while Playwright is still waiting inside managed teardown.
- `cmd.exe`, `python -m uvicorn`, `node vite`, Vite file watchers, Uvicorn
  tasks, and inherited stdio handles can all make process close semantics less
  deterministic.
- Local `reuseExistingServer: true` can make ownership less deterministic if a
  server is already listening before the test starts.

Potential risks:

- CI or local validation can fail even when browser assertions pass.
- Ports `8012` and `3012` can remain occupied by stale processes.
- SQLite E2E database files can remain locked or reuse stale state.
- Future runs can accidentally talk to old code if an existing server is
  reused.
- Agents may overclaim validation if they treat `ok` test bodies as a full pass.

Recommended investigation:

```powershell
Get-NetTCPConnection -LocalPort 8012,3012 -ErrorAction SilentlyContinue
```

or:

```powershell
netstat -ano | findstr ":8012 :3012"
```

Run those checks before and after a timed-out Playwright command.

Recommended isolation runs:

```powershell
$env:E2E_USE_REAL_WORKER='false'
npm.cmd run test:e2e:external -- e2e-course-ui-markdown-reader.spec.js --project=chromium
```

Use this Windows-local runner when the managed `webServer` path reports all
test bodies as `ok` but the CLI times out while cleaning up.

Recommended durable fixes:

- Use `npm.cmd run test:e2e:external -- <playwright args>` for local Windows
  validation when a real process exit status is required.
- Keep the runner-level cleanup guarded so it only kills processes spawned by
  the current runner.
- Consider making deterministic local validation opt out of
  `reuseExistingServer`.
- Consider defaulting UI E2E to `E2E_USE_REAL_WORKER=false` unless a target
  specifically validates real worker behavior.
- Document cleanup timeouts as infrastructure failures in
  `docs/development/TEST_EXECUTION_PITFALLS.md` or convert them into runner
  classifications if the issue remains common.

## Files Most Relevant For Continuation

UI files:

- `apps/web/admin/src/views/LearningNotes.vue`
- `apps/web/admin/src/views/Materials.vue`
- `apps/web/admin/src/views/MaterialRead.vue`
- `apps/web/admin/src/views/StudentCourseHome.vue`
- `apps/web/admin/src/components/CourseDiscussionPanel.vue`

Playwright and validation files:

- `apps/web/admin/playwright.config.cjs`
- `tests/e2e/web-admin/e2e-course-ui-markdown-reader.spec.js`
- `tests/e2e/web-admin/e2e-discussion-cover-llm-tier3.spec.js`
- `tests/e2e/web-admin/e2e-learning-notes-attendance-cover-tier20.spec.js`
- `ops/scripts/dev/playwright_preflight.py`
- `ops/scripts/dev/run_validation_target.py`
- `docs/development/TEST_EXECUTION_LEDGER.md`
- `docs/development/TEST_EXECUTION_SUMMARY.md`
- `docs/development/TEST_EXECUTION_PITFALLS.md`

Local-only visual evidence:

- `.agent-run/uploads/1.png`
- `.agent-run/uploads/2.png`
- Any screenshots generated during the previous visual review

Do not commit local screenshots unless the user explicitly asks to track visual
fixtures.

## Specific Warnings For The Next Agent

- Do not treat Playwright `ok` lines as a passing target when the command exits
  by timeout.
- Do not overwrite the ledger with inferred results. Record only observed
  executions.
- Do not copy terminal-rendered Chinese mojibake into committed docs. Use
  UTF-8-safe helpers or ASCII summaries for handoff documentation.
- Do not make broad backend/auth changes for this UI pass. The current work is
  frontend layout and Playwright infrastructure unless the user explicitly
  changes scope.
- Do not delete or reset user changes. Confirm `git status --short` before
  editing and work with any existing local modifications.
- If screenshot review shows that a previous visual change made one page worse,
  tune that page directly instead of forcing a single universal layout.

## Suggested First Commands For Next Agent

From the repository root:

```powershell
git status --short
git branch --show-current
Get-Content AGENTS.md
Get-Content docs\README.md
Get-Content docs\development\UI_BEAUTIFY_HANDOFF_2026-05-10.md
python ops\scripts\dev\select_validation_targets.py --worktree
```

Before Playwright runs:

```powershell
.\.venv\Scripts\python.exe ops\scripts\dev\playwright_preflight.py --json
Get-NetTCPConnection -LocalPort 8012,3012 -ErrorAction SilentlyContinue
```

For frontend build after UI edits:

```powershell
cd apps\web\admin
npm.cmd run build
```

For targeted browser checks, prefer starting with one focused test or one grep
case before running the full target, and capture screenshots between edits.
