---
name: validation-ledger-maintenance
description: Use this when adding or revising CourseEval validation targets, wiring ledger_id, updating test-execution CSV ledgers, correcting selector history drift, or recording observed validation evidence.
---

# Validation Ledger Maintenance

## Purpose

Keep the machine-readable validation registry, durable target ledger, and
observed run history aligned. Selector output is planning data; committed CSV
rows are reviewed project history.

## Workflow

1. Read `skills/validation-selection/SKILL.md` and the testing ledger section
   in `docs/development/DEVELOPMENT_AND_TESTING.md`.
2. For a registry target, decide whether it already has durable run history:
   if yes, `ledger_id` must match the target id; if no, leave `ledger_id` null.
3. Add target rows to `docs/development/testing/test-execution-targets.csv`
   only when the target should become durable metadata. Add run rows only for
   commands that actually executed.
4. Never point one target's `ledger_id` at an unrelated target as an informal
   alias. Add an explicit alias mechanism first if aliases ever become needed.
5. Update selector/manual tests for new registry invariants.
6. Run lint and selector checks before committing.

## Commands

```powershell
.venv\Scripts\python.exe -m json.tool tests\TEST_SELECTION_TARGETS.json
.venv\Scripts\python.exe ops\scripts\dev\lint_validation_registry.py
.venv\Scripts\python.exe -m unittest tests.backend.manual.test_validation_selector -v
.venv\Scripts\python.exe ops\scripts\dev\select_validation_targets.py --worktree --json
git diff --check
```

## Guardrails

- Record only observed command outcomes in CSV run history.
- Keep private paths out of CSV rows; use `<repo>`, `<local-port>`, and similar
  placeholders.
- Treat `needs_review` and `not_sufficient` selector states as decision points,
  not failures to hide.
- Do not commit `.agent-run/` artifacts. Use them only as local evidence while
  preparing reviewed ledger rows.

## Related Files

- `tests/TEST_SELECTION_TARGETS.json`
- `docs/development/testing/test-execution-targets.csv`
- `docs/development/testing/test-execution-runs.csv`
- `ops/scripts/dev/lint_validation_registry.py`
- `ops/scripts/dev/select_validation_targets.py`
- `tests/backend/manual/test_validation_selector.py`
