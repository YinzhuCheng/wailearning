# Test Execution Runs

## Purpose

This document is the stable explainer for
[`test-execution-runs.csv`](test-execution-runs.csv).

Use it when:

- appending observed validation evidence;
- deciding whether a blocked or failed run belongs in durable history;
- interpreting what a run row does and does not prove.

## What The CSV Stores

`test-execution-runs.csv` is the append-only observed run history.

Each row records a real validation attempt with fields such as:

- target id
- date
- branch
- source commit
- observed command
- result
- summary
- notes

This is the durable execution log, not just a list of successful runs.

## When To Update It

Append a row when a validation command actually executed and produced an
observable outcome.

Record:

- `passed`
- `failed`
- `blocked`
- `timed out`
- `interrupted`
- `skipped`

Do not record selector recommendations, dry-run planning, or commands that
never ran.

## Append Rules

1. Append rows; do not rewrite history unless correcting a transcription error.
2. Keep summaries short and factual.
3. Put long narratives in Markdown docs or handoffs, not in the CSV cell.
4. Keep private paths redacted or replaced with placeholders such as `<repo>`
   or `<local-port>`.

## Related Scripts

- `ops/scripts/dev/run_validation_target.py`
- `ops/scripts/dev/run_validation_profile.py`
- `skills/validation-ledger-maintenance/SKILL.md`
- `skills/security-redteam-iteration/scripts/append_run_ledger.py`

## Common Failure Modes

- only green runs were recorded, making the history misleading
- environment failures were summarized as product failures
- shell quoting damaged the command field
- private paths leaked into committed notes

## Related Files

- [test-execution-runs.csv](test-execution-runs.csv)
- [test-execution-targets.csv](test-execution-targets.csv)
- [test-execution-summary.csv](test-execution-summary.csv)
- [TEST_EXECUTION_LEDGER.md](TEST_EXECUTION_LEDGER.md)
