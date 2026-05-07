# Validation Automation Handoff - 2026-05-08

Branch: `cursor/discussion-avatar-chat-ui-921d`

This handoff describes the committed validation automation work on this branch.
Local `.agent-run/` files contain richer machine-local run artifacts and older
agent notes, but those files are ignored and are not required for takeover.

## Current State

The branch now has a first operational pass of the diff-and-ledger validation
system:

- `ops/scripts/dev/select_validation_targets.py` recommends validation targets
  from changed paths.
- `tests/TEST_SELECTION_TARGETS.json` is the machine-readable mapping from
  repository paths to validation targets.
- `ops/scripts/dev/run_validation_target.py` executes one target and writes
  ignored local run artifacts.
- `ops/scripts/dev/validation_history.py` stores ignored JSONL run history and
  changed-path signatures.
- `ops/scripts/dev/run_validation_profile.py` orchestrates small validation
  profiles over the target runner.
- `tests/backend/manual/test_validation_selector.py` provides standard-library
  smoke/unit coverage for selector, runner, history, JUnit parsing, and profile
  behavior.

The committed docs to read first are:

1. `docs/development/DEVELOPMENT_AND_TESTING.md`
2. `docs/development/TEST_SUITE_MAP.md`
3. `docs/development/TEST_EXECUTION_LEDGER.md`
4. this handoff

## Implemented Capabilities

Selector:

- Reads explicit `--paths`, staged diffs, base/head diffs, or worktree diffs.
- Includes untracked non-ignored files for `--worktree` by default.
- Emits Markdown or JSON.
- Emits `non_full_validation.status` as `acceptable`, `needs_review`, or
  `not_sufficient`.
- Emits per-target `history_status` and `history_reason`.
- Reads the Markdown execution ledger for reviewed target history.
- Reads ignored structured JSONL history unless `--no-history` is supplied.
- Treats structured history as fresh only when the stored changed-path
  signature matches the current selector input.

Target runner:

- Executes a single target from `tests/TEST_SELECTION_TARGETS.json`.
- Writes ignored `run.json`, `ledger-snippet.md`, stdout logs, and stderr logs
  under `.agent-run/logs/`.
- Appends ignored `.agent-run/validation-history.jsonl` unless `--no-history`
  is supplied.
- Uses the repository virtualenv interpreter when present; otherwise falls back
  to the current Python and records that fact.
- Classifies missing pytest/npm/npx/executables or unresolved placeholders as
  `blocked` / environment-or-orchestrator issues.
- For `python -m pytest` targets without `--junitxml`, adds an ignored JUnit XML
  artifact and parses testcase totals/statuses into local run artifacts.
- Redacts private absolute paths in JSON output, including testcase file paths
  parsed from JUnit XML.

Profile runner:

- Supports `static`.
- Supports `selector-recommended`.
- Defaults to `--max-risk targeted`.
- Skips targets with `requires_review_reason` unless
  `--include-review-targets` is passed.
- Treats `non_full_validation.status=not_sufficient` as profile exit code `4`.
- Writes profile summaries under ignored `.agent-run/logs/`.

## Useful Commands

Selector examples:

```powershell
python ops\scripts\dev\select_validation_targets.py --worktree
python ops\scripts\dev\select_validation_targets.py --worktree --json
python ops\scripts\dev\select_validation_targets.py --paths apps\backend\wailearning_backend\api\routers\learning_notes.py --json
```

Target runner examples:

```powershell
python ops\scripts\dev\run_validation_target.py static.validation_selector --timeout-seconds 120
python ops\scripts\dev\run_validation_target.py static.validation_selector --dry-run
python ops\scripts\dev\run_validation_target.py backend.learning_notes.api
```

Profile runner examples:

```powershell
python ops\scripts\dev\run_validation_profile.py static --dry-run --timeout-seconds 120
python ops\scripts\dev\run_validation_profile.py selector-recommended --paths apps\web\admin\src\views\HomeworkSubmissions.vue --dry-run
python ops\scripts\dev\run_validation_profile.py selector-recommended --include-review-targets --max-risk broad --dry-run
```

Core validation for this tooling:

```powershell
python -m py_compile ops\scripts\dev\validation_history.py ops\scripts\dev\select_validation_targets.py ops\scripts\dev\run_validation_target.py ops\scripts\dev\run_validation_profile.py tests\backend\manual\test_validation_selector.py
python -m json.tool tests\TEST_SELECTION_TARGETS.json
python -m unittest tests.backend.manual.test_validation_selector -v
python ops\scripts\dev\run_validation_target.py static.validation_selector --timeout-seconds 120
python ops\scripts\dev\run_validation_profile.py static --dry-run --timeout-seconds 120
python ops\scripts\dev\select_validation_targets.py --worktree --json
git diff --check
```

## Latest Verified Results

Verified on 2026-05-08 on branch `cursor/discussion-avatar-chat-ui-921d`:

- `py_compile` for selector, target runner, profile runner, history helper, and
  selector tests: passed.
- `python -m json.tool tests\TEST_SELECTION_TARGETS.json`: passed.
- `python -m unittest tests.backend.manual.test_validation_selector -v`: 15
  tests passed.
- `python ops\scripts\dev\run_validation_target.py static.validation_selector
  --timeout-seconds 120`: passed.
- `python ops\scripts\dev\run_validation_profile.py static --dry-run
  --timeout-seconds 120`: passed.
- `python ops\scripts\dev\select_validation_targets.py --worktree --json`:
  `non_full_validation.status=acceptable`, `unmatched_paths=[]`.
- `git diff --check`: passed.
- Private-path scan over the committed diff found no local absolute path
  matches.

Environment note: this worktree did not have `<repo>/.venv` at validation time,
so runner smoke commands fell back to the current Python interpreter. That
fallback is expected and recorded in ignored local artifacts.

## Files Changed In This Pass

Committed source/tooling additions:

- `ops/scripts/dev/run_validation_target.py`
- `ops/scripts/dev/run_validation_profile.py`
- `ops/scripts/dev/validation_history.py`
- `tests/backend/manual/test_validation_selector.py`

Committed source/tooling updates:

- `ops/scripts/dev/select_validation_targets.py`
- `tests/TEST_SELECTION_TARGETS.json`

Committed documentation updates:

- `docs/development/DEVELOPMENT_AND_TESTING.md`
- `docs/development/TEST_SUITE_MAP.md`
- `docs/development/TEST_EXECUTION_LEDGER.md`
- `docs/development/VALIDATION_AUTOMATION_HANDOFF_2026-05-08.md`

Ignored local artifacts:

- `.agent-run/validation-history.jsonl`
- `.agent-run/logs/`
- `.agent-run/test-selector-*.jsonl`
- `.agent-run/test-selector-*.xml`

Do not commit ignored `.agent-run/` files.

## Known Limitations And Next Work

Still target-level, not full case-level policy:

- The runner can parse pytest JUnit testcase results, but selector sufficiency
  still uses target-level history.
- Playwright JSON/JUnit parsing is not implemented yet.

Profiles are minimal:

- Existing profiles are `static` and `selector-recommended`.
- PostgreSQL provisioning, frontend build orchestration, Playwright
  browser/port management, and full local release-style profiles remain future
  work.

History is local:

- Structured history is ignored local evidence, not committed project history.
- Reviewed results still need manual updates to
  `docs/development/TEST_EXECUTION_LEDGER.md`.

Recommended next implementation steps:

1. Add Playwright result artifact support to the runner.
2. Add an environment doctor for Python, pytest, npm, npx, Playwright browsers,
   PostgreSQL, and common port conflicts.
3. Add broader profile support such as `frontend-build`, `backend-targeted`,
   `postgres-package`, and `full-local`.
4. Teach selector policy to use parsed testcase results where available.
5. Add CI advisory output for selector recommendations and non-full sufficiency.

## Takeover Notes

- Work only in the `cursor/discussion-avatar-chat-ui-921d` worktree for this
  branch.
- Treat `.agent-run/` as local runtime evidence and handoff noise unless a task
  explicitly asks for machine-local artifacts.
- If `pytest` is unavailable, use `python -m unittest
  tests.backend.manual.test_validation_selector -v`; the tests are intentionally
  standard-library based and pytest-collectable later.
- If selector output reports `not_sufficient`, do not claim targeted validation
  is complete until the full/broad blocker is addressed or explicitly deferred.
- If profile output skips a review-required Playwright target, that is by
  design. Re-run with `--include-review-targets` only when the browser
  environment is ready.
