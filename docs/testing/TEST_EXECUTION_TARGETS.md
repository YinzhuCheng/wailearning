# Test Execution Targets

## Purpose

This document is the stable explainer for
[`test-execution-targets.csv`](test-execution-targets.csv).

Use it when:

- adding or revising a durable validation target;
- deciding whether a selector registry target should have a `ledger_id`;
- interpreting target metadata without reading the CSV schema ad hoc.

## What The CSV Stores

`test-execution-targets.csv` stores one row per durable validation target,
including:

- target id
- category
- scope
- canonical command
- working directory
- relevant paths
- retest triggers
- last observed result metadata
- pass count
- run count

This is target metadata plus recent durability signals. It is not the
append-only history of every validation attempt.

## When To Update It

Update this CSV when:

- a validation target becomes part of the durable repository target set;
- the canonical command, path surface, or working directory changes;
- the selector registry needs a matching durable ledger row;
- reviewed observed results should update `last_*`, `pass_count`, or
  `run_count`.

## Append / Counting Rules

1. `test_id` is the durable key and should match any non-null `ledger_id` in
   `tests/TEST_SELECTION_TARGETS.json`.
2. `pass_count` increments only for observed `passed` runs.
3. `run_count` increments for any started run with an observed result:
   `passed`, `failed`, `blocked`, `timed out`, `interrupted`, or `skipped`.
4. Keep commands and paths repository-relative or placeholder-safe; do not
   commit private machine paths.

## Related Scripts

- `ops/scripts/dev/lint_validation_registry.py`
- `ops/scripts/dev/select_validation_targets.py`
- `ops/scripts/dev/run_validation_target.py`
- `skills/validation-ledger-maintenance/SKILL.md`

## Common Failure Modes

- `ledger_id` drift between registry and CSV
- stale target metadata after command/path changes
- misleading run/pass counts because blocked runs were omitted
- BOM or encoding damage that breaks header parsing

## Related Files

- [test-execution-targets.csv](test-execution-targets.csv)
- [test-execution-runs.csv](test-execution-runs.csv)
- [TEST_EXECUTION_LEDGER.md](TEST_EXECUTION_LEDGER.md)
