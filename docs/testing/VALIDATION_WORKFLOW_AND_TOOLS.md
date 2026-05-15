# Validation Workflow And Tools

## Purpose

This document is the focused entrypoint for CourseEval's diff-based validation
workflow, selector/runner/profile tooling, and the evidence rules that govern
how those tools should be interpreted.

Use it when:

- choosing validation scope from a diff;
- running the validation selector, target runner, or profile runner;
- deciding how to record observed validation honestly;
- checking local validation sufficiency before broader suites.

`DEVELOPMENT_AND_TESTING.md` remains the broader development/testing handbook.
This document is the narrower source for validation mechanics.

## Diff-Based Validation Workflow

The diff-based validation tools provide the repository's first standard
incremental validation workflow. Use them after edits to decide what to run
before reaching for full `pytest`, full Playwright, or PostgreSQL-heavy
profiles.

The workflow has three layers:

- selector: recommend targets from changed paths
- target runner: execute one selected target and write local artifacts
- profile runner: execute a small named group of targets

Default agent loop:

1. Review the changed-path recommendation from the repository root:

   ```bash
   python ops/scripts/dev/select_validation_targets.py --worktree
   ```

2. If the output is for automation or you need to inspect exact target IDs, use:

   ```bash
   python ops/scripts/dev/select_validation_targets.py --worktree --json
   ```

3. Use the repository default `strict` workflow unless the user explicitly asks
   for a lighter guided route.

   In the text-first workflow:

   - `strict` means starting from the repository governance entrypoints,
     reading the task-scoped docs and skills, using pitfall search before
     classifying ambiguous failures, and updating docs plus durable ledgers in
     the same repository-changing round
   - `guided` remains a lighter advisory route chosen explicitly by the user,
     but guided evidence must never be reported as strict completion

4. For documentation-only or validation-tooling changes, run the static profile
   first:

   ```bash
   python ops/scripts/dev/run_validation_profile.py static --dry-run --timeout-seconds 120
   ```

   Use the real static target when you need observed evidence rather than a
   profile smoke:

   ```bash
   python ops/scripts/dev/run_validation_target.py static.validation_selector --timeout-seconds 120
   ```

5. For ordinary product or test changes, either run the target IDs shown by the
   selector one by one, or use the selector-recommended profile:

   ```bash
   python ops/scripts/dev/run_validation_profile.py selector-recommended --worktree --max-risk targeted
   ```

6. If the selector recommends a review-required target, decide explicitly
   whether the environment is ready. Browser targets generally need Node,
   `node_modules`, Playwright browsers, clean ports, and a known
   backend/frontend startup mode:

   ```bash
   python ops/scripts/dev/run_validation_profile.py selector-recommended --worktree --max-risk broad --include-review-targets
   ```

7. Read the final selector/profile status before claiming validation coverage:

   - `acceptable`: static/targeted evidence is a reasonable first-pass result
     for the current diff
   - `needs_review`: a broad or review-required target was recommended; either
     run it or state why it was deferred
   - `not_sufficient`: targeted validation is not enough; address the blocker
     or explicitly defer it as unresolved validation

This is a planning and evidence workflow, not a magic minimizer. The selector
is conservative and path-based. It does not understand every semantic
dependency in the product. If the diff touches high-risk behavior and the
recommendation looks too narrow, run the broader target and update
[`tests/TEST_SELECTION_TARGETS.json`](../../tests/TEST_SELECTION_TARGETS.json)
when the gap is repeatable.

## Artifact And Evidence Rules

- `.agent-run/validation-history.jsonl` and `.agent-run/logs/` are ignored
  local evidence. They can help the selector identify fresh local runs for the
  same changed-path signature.
- Do not commit `.agent-run/` artifacts.
- Do not update [`test-execution-runs.csv`](test-execution-runs.csv) for
  selector output, dry-run planning, or commands that were only recommended.
- Do update the CSV ledger manually when an actual target run should become
  durable project history. Review the generated `ledger-snippet.md` first and
  redact any private machine details.
- If a runner result is `blocked`, `timed out`, `interrupted`, or `skipped`, do
  not summarize it as a pass. Record or hand off the unresolved validation
  state.

Windows note: prefer `.venv\Scripts\python.exe` when the repository virtual
environment exists. If it does not, the runner falls back to the current Python
and records that fallback in local artifacts; this is acceptable for selector
smoke work but not proof that the full application dependency environment is
ready.

## Local Pytest SQLite Guardrail

Default pytest runs use a repository-local per-process SQLite file under
`.pytest_tmp/` when no PostgreSQL test URL is configured. Before deleting or
reusing a local `test*.sqlite` artifact after an interrupted run, use the
read-only guardrail:

```bash
python ops/scripts/dev/pytest_sqlite_guard.py
python ops/scripts/dev/pytest_sqlite_guard.py --json
```

For preflight scripts that should stop when another pytest process is already
running, use:

```bash
python ops/scripts/dev/pytest_sqlite_guard.py --fail-on-active-pytest
```

Interpretation:

- `status=pass` means the guardrail did not detect another pytest process
- `status=warn` means it found an active pytest-like process; stop that process
  before deleting or reusing the reported SQLite artifact(s)
- The script is diagnostic only. It does not kill processes and does not delete
  files under `.pytest_tmp/`

## Diff-Based Validation Target Selection

Use the validation selector when you need a conservative first pass for
answering: "Given this diff, which validation targets should I run first?"

The selector is intentionally advisory. It does **not** run tests, does **not**
edit the execution ledger, and does **not** prove that the recommended set is a
mathematically minimal or complete safety proof. It turns the current diff plus
a machine-readable target registry into a reviewable command list with reasons.

Run from repository root:

```bash
python ops/scripts/dev/select_validation_targets.py
python ops/scripts/dev/select_validation_targets.py --base origin/main
python ops/scripts/dev/select_validation_targets.py --base origin/main --head HEAD --json
python ops/scripts/dev/select_validation_targets.py --staged
python ops/scripts/dev/select_validation_targets.py --worktree
python ops/scripts/dev/select_validation_targets.py --paths apps/backend/courseeval_backend/api/routers/learning_notes.py
```

Windows agents should use the venv interpreter when available:

```powershell
.venv\Scripts\python.exe ops\scripts\dev\select_validation_targets.py --base origin/cursor/discussion-avatar-chat-ui-921d --head HEAD
```

Inputs:

- changed paths come from `git diff --name-status --no-renames <base>...<head>`,
  from `git diff --cached --name-status --no-renames` when `--staged` is used,
  from `git diff --name-status --no-renames` when `--worktree` is used, or
  from explicit `--paths`
- `--worktree` includes untracked, non-ignored files by default using
  `git ls-files --others --exclude-standard`; use `--no-include-untracked` if
  you need only tracked worktree modifications
- the machine-readable registry is
  [`tests/TEST_SELECTION_TARGETS.json`](../../tests/TEST_SELECTION_TARGETS.json)
- the script also parses target-level history from
  [`test-execution-targets.csv`](test-execution-targets.csv) so recommendations
  can show the last observed result, last commit, and pass/run count when a
  ledger entry exists
- unless `--no-history` is supplied, the script also reads ignored structured
  local history from `<repo>/.agent-run/validation-history.jsonl`. Structured
  history is treated as fresh evidence only when its changed-path signature
  matches the current selector input; otherwise it is reported as stale

Outputs:

- Markdown by default for agent review
- JSON with `--json` for future automation
- `non_full_validation.status`, one of `acceptable`, `needs_review`, or
  `not_sufficient`
- per-target `history_status`, one of `fresh`, `stale`, `unknown`, or
  `blocked`, or `not-recorded`
- changed paths and statuses
- recommended target IDs, categories, risk levels, working directories, command
  argv arrays, matched paths, selection reasons, coverage tags, review reasons,
  ledger history, and the latest matching structured history record when one is
  available
- unmatched paths, which mean "the first-version registry has no precise rule",
  not "no validation is needed"
- a ledger snippet template for observed results

Operational rules:

- Treat `risk=static` targets as hygiene checks, not product behavior coverage
- Treat `risk=targeted` targets as the normal first pass for bounded code
  surfaces
- Treat `risk=broad` and `risk=full` targets as escalation recommendations.
  They may be expensive or environment-dependent; review the reason before
  starting PostgreSQL or full Playwright
- If a changed path is unmatched, do not silently skip validation. Either add a
  registry rule, run a broader profile, or document why no runtime target is
  appropriate
- If the selector recommends no Playwright target for docs-only diffs, that is
  expected. If it recommends no Playwright target for school UI, E2E fixture,
  Playwright config, route, auth, or seed changes, treat that as a registry gap
- If `non_full_validation.status` is `not_sufficient`, do not present targeted
  validation as complete evidence until the blocking reason is addressed or
  explicitly deferred. Typical blockers are recommended full targets or
  unmatched product source paths
- If `non_full_validation.status` is `needs_review`, targeted validation may
  still be the right first pass, but the output names the expensive or
  environment-sensitive target that needs operator judgment
- `history_status=stale` does not mean a target failed. It means the previous
  ledger or structured run result should not be counted as current evidence for
  this diff
- `history_status=blocked` means the latest structured runner evidence for the
  current changed-path snapshot was blocked by environment or orchestration
  preflight. Treat it as unresolved validation, not a product pass or fail
- Record only tests that actually ran in
  [`test-execution-runs.csv`](test-execution-runs.csv). Selector output and
  `--paths` smoke runs are planning/discovery, not observed test execution

## Validation Target Runner

The runner executes a single target from
[`tests/TEST_SELECTION_TARGETS.json`](../../tests/TEST_SELECTION_TARGETS.json)
and writes local artifacts under the ignored agent workspace:

```bash
python ops/scripts/dev/run_validation_target.py static.validation_selector
python ops/scripts/dev/run_validation_target.py frontend.school.build --timeout-seconds 900
python ops/scripts/dev/run_validation_target.py backend.learning_notes.api
python ops/scripts/dev/run_validation_target.py static.validation_selector --dry-run
```

Windows agents may use the same command with the repository virtual environment
when present:

```powershell
.venv\Scripts\python.exe ops\scripts\dev\run_validation_target.py static.validation_selector
```

The runner is deliberately narrower than the selector:

- it runs one target ID at a time
- it reads the same target registry as the selector
- it resolves the repository virtualenv Python when present, otherwise it uses
  the current interpreter and records that fallback in local artifacts
- it normalizes portable registry command names before execution: `python`
  resolves to the repository virtualenv when available, `npm`/`npm.cmd` and
  `npx`/`npx.cmd` resolve to the platform-appropriate executable
- it writes `<repo>/.agent-run/logs/<timestamp>-<target-id>/run.json`
- it writes `<repo>/.agent-run/logs/<timestamp>-<target-id>/ledger-snippet.md`
- it appends a compact structured record to
  `<repo>/.agent-run/validation-history.jsonl` unless `--no-history` is passed
- it captures per-command stdout/stderr logs under the same artifact directory
- for `python -m pytest` targets that do not already specify `--junitxml`, it
  adds an ignored JUnit XML artifact and records testcase-level totals and case
  statuses in `run.json` and structured history
- for real execution, it classifies missing interpreters, missing pytest,
  missing npm/npx/browser command, or unresolved command placeholders as
  `blocked` rather than product failures
- `--dry-run` is planning-only and does not check whether runtime tools are
  installed; add `--preflight` to a dry-run when the goal is to prove command
  and environment readiness without running the product test command
- it does not provision PostgreSQL, install dependencies, install browsers, or
  mutate the committed execution ledger

Exit codes:

- `0`: target commands passed, or `--dry-run` recorded the target without
  execution
- `1`: target command ran and failed
- `2`: environment or command preflight blocked execution
- `4`: command timed out
- `5`: command was interrupted
- `6`: invalid target, invalid registry, or invalid arguments

Treat runner artifacts as local evidence. If a run should become durable
project history, review the generated `ledger-snippet.md`, redact any private
details if needed, and then update
[`test-execution-runs.csv`](test-execution-runs.csv) and
[`test-execution-targets.csv`](test-execution-targets.csv) manually with the
observed result.

Structured history is a machine-readable local companion to the committed CSV
ledger, not a replacement for it. It records target id, result, failure class,
artifact pointers, changed paths, a changed-path signature, and parsed test
artifact summaries when available so the selector can tell whether a local run
actually covered the current diff. Keep it under ignored `.agent-run/`; do not
commit local history files.

## Validation Profile Runner

The profile runner orchestrates one or more target runner invocations and
writes a profile-level summary under ignored `.agent-run/logs/`:

```bash
python ops/scripts/dev/run_validation_profile.py static
python ops/scripts/dev/run_validation_profile.py selector-recommended --paths apps/web/school/src/views/HomeworkSubmissions.vue --dry-run
python ops/scripts/dev/run_validation_profile.py selector-recommended --worktree --max-risk targeted
python ops/scripts/dev/run_validation_profile.py selector-recommended --include-review-targets --max-risk broad
```

Initial profiles:

- `static`: runs the static selector validation target
- `selector-recommended`: runs selector recommendations for explicit `--paths`
  or the current worktree

Profile safety defaults:

- `--max-risk targeted` is the default; `broad` and `full` recommendations are
  skipped unless explicitly allowed
- targets with `requires_review_reason` are skipped unless
  `--include-review-targets` is passed
- `--dry-run` is useful for proving orchestration and artifact writing without
  executing the underlying commands
- `--dry-run --preflight` keeps the product commands unexecuted but still checks
  command placeholders, Python module availability, and platform executables
- if selector output says `non_full_validation.status=not_sufficient`, the
  profile exits with code `4` even if the runnable subset passed or was skipped

Profile exit codes:

- `0`: no product or environment failure was observed, including dry-run or
  policy-skipped targets
- `1`: at least one executed target failed or timed out
- `2`: at least one executed target was blocked by environment or command
  preflight
- `4`: selector policy says non-full validation is not sufficient
- `6`: profile setup, selector execution, or JSON parsing failed

Known first-version limitations:

- the registry is conservative and incomplete. It covers the high-value targets
  currently represented in the ledger plus maintained Playwright suites,
  important behavior/security pytest targets, and several broad escalation
  rules
- the selector works at target level, not individual `pytest` test item or
  Playwright `test(...)` case level. The runner can now record pytest JUnit XML
  case summaries, but the selector still uses target-level history for
  sufficiency decisions
- CSV ledger parsing is intentionally shallow: it extracts `last_result`,
  `last_commit`, `pass_count`, and `run_count` from
  [`test-execution-targets.csv`](test-execution-targets.csv). The
  machine-readable registry remains the source for selection rules
- Python `fnmatch` treats `**` as a glob pattern, not as a full
  gitignore-style recursive operator with every edge case. When writing
  registry rules, include both one-level and recursive patterns if both are
  required, for example `apps/backend/courseeval_backend/*.py` and
  `apps/backend/courseeval_backend/**/*.py`
- this tool is not a replacement for reading task-scoped docs. It makes the
  first recommendation easier to audit; it does not understand every semantic
  dependency in the application
- the runner is a first operational layer, not a full validation orchestrator.
  PostgreSQL lifecycle management, Playwright port isolation, browser install
  detection beyond executable preflight, and machine-readable
  pytest/Playwright item-level result parsing remain follow-up work

## Related Files

- [`DEVELOPMENT_AND_TESTING.md`](DEVELOPMENT_AND_TESTING.md)
- [`CI_AND_VALIDATION.md`](CI_AND_VALIDATION.md)
- [`TEST_EXECUTION_PITFALLS.md`](TEST_EXECUTION_PITFALLS.md)
- [`../../skills/validation-selection/SKILL.md`](../../skills/validation-selection/SKILL.md)
- [`../../skills/validation-ledger-maintenance/SKILL.md`](../../skills/validation-ledger-maintenance/SKILL.md)
- [`../../ops/scripts/dev/select_validation_targets.py`](../../ops/scripts/dev/select_validation_targets.py)
- [`../../ops/scripts/dev/run_validation_target.py`](../../ops/scripts/dev/run_validation_target.py)
- [`../../ops/scripts/dev/run_validation_profile.py`](../../ops/scripts/dev/run_validation_profile.py)
