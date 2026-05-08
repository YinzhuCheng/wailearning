# Homework Table Button Layout Handoff - 2026-05-08

This handoff replaces the previous validation automation handoff content for the
current branch. The active follow-up is the admin homework list action layout.

## Branch And Context

- Worktree: `cursor/discussion-avatar-chat-ui-921d`
- Branch: `cursor/discussion-avatar-chat-ui-921d`
- The user provided a screenshot showing the homework list action buttons in the
  admin SPA. The `查看` and `删除` buttons were visibly clipped inside the
  `操作` column.
- `.agent-run/` is local-only and ignored. Do not commit screenshots, logs, or
  other local evidence from that directory.

## User-Visible Problem

The admin homework table in `apps/web/admin/src/views/Homework.vue` rendered the
action buttons too tightly. In the screenshot:

- the `查看` button label was clipped on the right;
- the `删除` button label was clipped on the right;
- the action area looked cramped and unstable inside the table cell.

The issue is in the table layout and button spacing, not in homework routing or
the underlying API.

## Relevant Files

- `apps/web/admin/src/views/Homework.vue`
  - Owns the homework list table, action column, and table-level spacing.
- `tests/TEST_SELECTION_TARGETS.json`
  - Registry already maps this view to `frontend.admin.build` and the
    homework-related Playwright tier.
- `docs/development/TEST_EXECUTION_LEDGER.md`
  - Execution record for the build and validation steps used in this pass.
- `AGENTS.md`
  - Updated with the change-scoped validation rule requested by the user.

## Fix Implemented

`apps/web/admin/src/views/Homework.vue` was updated in three places:

1. The `操作` column width increased from `280` to `340` for staff rows and
   from `200` to `220` for student rows.
2. The table's minimum width increased from `1060px` to `1160px` to reduce
   pressure on the right-side columns.
3. The action button container now neutralizes the default adjacent button
   margin and gives each button a stable `min-width` and padding, so the labels
   remain fully visible.

These changes keep the action area readable without changing behavior or route
flow.

## Validation Policy Update

`AGENTS.md` now includes a rule stating that, unless the user explicitly asks
for a broader validation level, verification should stay change-scoped:

- run the diff selector first;
- run only the relevant static/targeted targets by default;
- treat `needs_review` and `not_sufficient` as explicit review points;
- do not use the default rule to ignore unmatched paths or high-risk gaps.

That rule is intentionally written to support incremental validation, not to
justify under-testing.

## Validation Performed

1. `select_validation_targets.py --worktree`
   - Result: `needs_review`
   - Relevant targets found:
     - `static.encoding_text_tools`
     - `frontend.admin.build`
     - `admin.e2e.homework_comment_cover_tier4`
   - No unmatched paths.
2. `python -m py_compile` / selector smoke / local selector history checks
   - Already completed in the current branch history and reflected in the
     execution ledger.
3. `npm.cmd install` in `apps/web/admin`
   - Required because the local admin package did not yet have `vite` available.
4. `npm.cmd run build`
   - Passed after install.
5. `npx.cmd playwright test e2e-homework-comment-cover-tier4.spec.js --project=chromium`
   - Blocked before browser assertions because the repository `.venv` is missing
     `uvicorn`:
     `No module named uvicorn`

## Important Environment Note

The Playwright attempt did not reach product assertions. It failed while the
managed backend process was starting. That means the browser test result is an
environment block, not a regression verdict on the homework layout.

## Notes For Next Agent

- Stay on `cursor/discussion-avatar-chat-ui-921d`.
- Do not reuse the previous LaTeX copy/rendering handoff as if it still matches
  the current task; it has been replaced with this homework layout context.
- If you need browser verification for the homework action buttons, install or
  provision the missing backend dependency in `.venv` first so Playwright can
  start `uvicorn`.
- The build is already green, and the validation ledger has been updated with
  the observed result.
