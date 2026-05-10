---
name: validation-selection
description: Use this when choosing, running, or documenting CourseEval validation for a code, test, documentation, ops, or governance change. Triggers include test planning, selector output, validation target registry edits, final handoff validation summaries, and avoiding over-broad or under-scoped test claims.
---

# Validation Selection

## Purpose

Choose validation that is proportional to the change while staying honest about
coverage, skipped targets, blockers, and broad/full recommendations.

## Workflow

1. Read `AGENTS.md`, `docs/README.md`, and the task-scoped docs.
2. Inspect the diff or intended paths:
   `python ops/scripts/dev/select_validation_targets.py --worktree`
3. Use `--json` when you need exact target IDs, `non_full_validation.status`,
   unmatched paths, or `requires_review_reason` values.
4. Run recommended static and targeted targets directly, or use:
   `python ops/scripts/dev/run_validation_profile.py selector-recommended --worktree --max-risk targeted`
5. If the selector reports `needs_review`, decide and document whether to run
   the review target now.
6. If the selector reports `not_sufficient`, do not call validation complete
   until the full/broad target is run or explicitly deferred with a reason.
7. Record only real executed results in durable docs; selector planning output
   alone is not a test ledger entry.

## Commands

```powershell
python ops/scripts/dev/select_validation_targets.py --worktree
python ops/scripts/dev/select_validation_targets.py --worktree --json
python ops/scripts/dev/run_validation_target.py <target-id> --timeout-seconds 120
python ops/scripts/dev/run_validation_profile.py selector-recommended --worktree --max-risk targeted
python ops/scripts/dev/lint_validation_registry.py
```

## Guardrails

- Treat the selector as advisory, not as a substitute for engineering judgment.
- Add registry mappings when a repeated change path falls through to an
  imprecise fallback.
- Keep broad/full recommendations visible in the final answer or handoff even
  when they are deferred.
- Do not claim product coverage from static checks alone.
- Keep `.agent-run/` run artifacts local and uncommitted.

## Related Files

- `tests/TEST_SELECTION_TARGETS.json`
- `tests/backend/manual/test_validation_selector.py`
- `ops/scripts/dev/select_validation_targets.py`
- `ops/scripts/dev/run_validation_target.py`
- `ops/scripts/dev/run_validation_profile.py`
- `docs/development/DEVELOPMENT_AND_TESTING.md`
- `docs/development/testing/README.md`
