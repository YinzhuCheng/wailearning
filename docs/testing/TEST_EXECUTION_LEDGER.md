# Test Execution Ledger

The detailed execution ledger has been moved to CSV tables under
this directory:

- [`test-execution-targets.csv`](test-execution-targets.csv)
  stores one row per validation target.
- [`test-execution-runs.csv`](test-execution-runs.csv) stores
  append-only observed run history.
- [`test-execution-summary.csv`](test-execution-summary.csv)
  stores the concise recent/important run summary.

Use [`README.md`](README.md) for maintenance rules. Keep this
Markdown file as a stable entry point for existing links and human guidance.

## Counting Semantics

- Increment `run_count` for any started validation command that produced an
  observable result: `passed`, `failed`, `blocked`, `timed out`, `interrupted`,
  or `skipped`.
- Increment `pass_count` only for `passed` target runs.
- Do not record selector recommendations, dry-run planning, grep/static
  inspection, or commands that were written in notes but not executed.

## Current Source Of Truth

For target metadata and last-run fields, use
[`test-execution-targets.csv`](test-execution-targets.csv).
For individual run evidence, use
[`test-execution-runs.csv`](test-execution-runs.csv).
