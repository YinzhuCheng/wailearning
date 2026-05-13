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
| `pitfall-index.csv` | Structured index for pitfalls recorded in Markdown docs. New pitfalls use increasing positive `pitfall_sequence`; legacy Markdown-only entries may use `0` and `Null`. |
| `agent-update-log.csv` | One row per user-visible repository-changing conversation round, starting at sequence 1. Summaries stay short; details remain in docs, ledgers, and commits. |

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
6. Follow the pitfall recording policy in `TEST_EXECUTION_PITFALLS.md` when
   adding or reclassifying a pitfall.
7. Follow the per-round update-log policy in
   `../governance/agent-update-log.md` when appending `agent-update-log.csv`.
