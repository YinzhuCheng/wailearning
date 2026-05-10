# Documentation Governance Handoff

## Branch

- `cursor/repository-normalization`

## Completed

- Repository normalization and documentation-governance pass completed for the
  current scope.
- The worktree is expected to be clean after commit; verify push status
  separately.

## Verification

- `npm.cmd run build` in `apps/web/admin`
- `npm.cmd run build` in `apps/web/parent`
- `python ops/scripts/dev/run_validation_profile.py selector-recommended --worktree --max-risk static`
- `python ops/scripts/dev/check_repository_normalization.py`
- `git diff --check`

## Risks

- `docs/reports/` now holds dated audit / restructure / migration reports.
- `apps/web/admin/public/courseeval-mark.svg` and
  `apps/web/parent/public/courseeval-mark.svg` are the runtime favicon assets.
- `docs/known-issues-and-risks.md` now includes repository-normalization notes
  for future cleanup passes.

## Do Not Revert

- `docs/reports/` directory moves
- favicon wiring in both SPA `index.html` files
- `docs/reports/README.md`
