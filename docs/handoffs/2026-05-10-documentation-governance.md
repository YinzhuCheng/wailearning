# Documentation Governance Handoff

## Completed

- Continued the repository normalization line on `cursor/repository-normalization`.
- Confirmed that several apparent mojibake hits in `README.md`, `AGENTS.md`,
  and `docs/README.md` are PowerShell display artifacts when viewed through
  `safe-text-workflow.ps1`; they were not rewritten.
- Extended `check_text_encoding.py` with common Windows/CP936 mojibake markers.
- Added `check_repository_normalization.py` to catch active reintroduction of
  retired project/package/service/domain names while allowing historical ledgers.
- Updated architecture/reference docs so old names are no longer described as
  acceptable current ops paths.
- Updated the PostgreSQL UI audit example database from a retired name to
  `courseeval_uiux_audit`.
- Added the repo-local `repository-normalization` skill and linked it from
  `AGENTS.md` and `docs/README.md`.
- Updated the validation selector registry so root-level `ops/scripts/*.ps1`
  changes map to the static encoding/text tooling target.

## Changed Files

- `AGENTS.md`
- `docs/README.md`
- `docs/architecture/MAINTAINER_AGENT_GUIDE.md`
- `docs/reference/CODE_MAP_AND_ENTRYPOINTS.md`
- `docs/development/ENCODING_AND_MOJIBAKE_SAFETY.md`
- `docs/development/TEST_EXECUTION_PITFALLS.md`
- `docs/handoffs/2026-05-10-documentation-governance.md`
- `ops/scripts/dev/check_repository_normalization.py`
- `ops/scripts/dev/check_text_encoding.py`
- `ops/scripts/setup_git_remotes.ps1`
- `tests/TEST_SELECTION_TARGETS.json`
- `skills/repository-normalization/SKILL.md`

## Verification

- `python -m py_compile ops/scripts/dev/check_text_encoding.py ops/scripts/dev/check_repository_normalization.py` - passed.
- `python ops/scripts/dev/check_repository_normalization.py` - passed; `scanned=376 stale=0 missing_required_paths=0`.
- `python ops/scripts/dev/check_text_encoding.py --fail-on-suspicious <changed files>` - passed; `scanned=11 decode_errors=0 suspicious=0`.
- `python ops/scripts/dev/repo_line_health.py` - passed; tracked health text lines reported successfully.
- `python -m json.tool tests/TEST_SELECTION_TARGETS.json` - passed.
- `python ops/scripts/dev/lint_validation_registry.py` - passed.
- `python ops/scripts/dev/select_validation_targets.py --worktree` - passed with `non_full_validation.status=acceptable`; every changed path matched at least one target.
- `python -m py_compile ops/scripts/dev/select_validation_targets.py ops/scripts/dev/run_validation_target.py ops/scripts/dev/run_validation_profile.py ops/scripts/dev/validation_history.py ops/scripts/dev/lint_validation_registry.py tests/backend/manual/test_validation_selector.py` - passed.
- `python ops/scripts/dev/run_validation_target.py static.validation_selector --dry-run` - passed as a dry-run smoke (`result=skipped`, no command executed).
- `python -m unittest tests.backend.manual.test_validation_selector -v` - passed; 36 tests OK.
- `git diff --check` - passed; Git emitted only the existing CRLF warning for `ops/scripts/setup_git_remotes.ps1`.

## Known Failures

- No verification command failed in this batch.
- A future whole-repository suspicious-marker scan with `--fail-on-suspicious`
  is expected to report existing E2E selector/assertion hotspots in:
  - `tests/e2e/web-admin/e2e-scenario-resilience.spec.js`
  - `tests/e2e/web-admin/e2e-llm-hard-scenarios.spec.js`
- These were not fixed in this batch because selector repairs need targeted
  Playwright validation and should not be bundled with documentation governance.

## Risks

- `check_repository_normalization.py` is intentionally conservative. If it
  reports a historical note outside its allowlist, classify the hit before
  deleting text.
- The new mojibake markers may find real old corruption in test files. Treat
  that as a dedicated test-maintenance task, not as proof this docs batch broke
  encoding.
- No backend business logic was changed in this batch.

## Recommended Next Steps

1. Run the final verification commands and update this handoff if any command fails.
2. Consider a dedicated E2E text-selector cleanup for the two known mojibake
   hotspots, with the affected Playwright specs run afterward.
3. Consider adding `check_repository_normalization.py` to lightweight CI after
   the allowlist has proven stable.
4. Continue deeper docs/code alignment for data migration and permission
   governance in a separate batch.

## Do Not Revert

- Do not restore `wailearning_backend`, old service names, old domain examples,
  or `dd-class`/`ddclass` as current names.
- Do not reintroduce username/student-number guessing as normal student
  identity behavior.
- Do not reintroduce `Subject.class_id` as the normal course/class access
  fallback.
- Do not flatten the CSV validation ledgers back into giant Markdown tables.

## Useful Commands

```powershell
python ops/scripts/dev/check_repository_normalization.py
python ops/scripts/dev/check_text_encoding.py --fail-on-suspicious AGENTS.md docs/README.md
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ops\scripts\windows\safe-text-workflow.ps1 -Path AGENTS.md -FailOnSuspicious
python ops/scripts/dev/select_validation_targets.py --worktree
```
