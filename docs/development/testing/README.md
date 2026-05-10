# Structured Test Execution Tables

This directory stores test execution history as CSV tables. The Markdown files
one level up remain human entry points and policy documents; the durable facts
that agents append and tooling parses live here.

## Files

| File | Purpose |
|------|---------|
| `test-execution-targets.csv` | One row per validation target: category, scope, canonical command, last observed result, pass count, run count, relevant paths, and retest triggers. |
| `test-execution-runs.csv` | Append-only observed run history. Add failed, blocked, timed-out, interrupted, and skipped attempts as well as passes. |
| `test-execution-summary.csv` | Short scan aid for recent or important observed validation runs. |

## Rules

1. Record only observed executions. Selector output, dry-run planning, and typed
   but unexecuted commands do not belong in these CSV files.
2. Append run rows; do not rewrite history unless correcting a transcription
   error.
3. Keep committed paths repository-relative. Put private absolute paths and
   machine-local logs under ignored `.agent-run/` or `.e2e-run/` directories.
4. Keep long explanations in Markdown docs such as
   `../TEST_EXECUTION_PITFALLS.md`; keep CSV notes short and factual.
5. Use UTF-8 and the repository safe-text workflow before editing these files
   from Windows PowerShell.
