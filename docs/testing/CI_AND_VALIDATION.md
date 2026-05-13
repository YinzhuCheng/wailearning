# CI And Validation

## Purpose

This document centralizes the current CI entrypoints and validation routing for
CourseEval.

Use it when:

- deciding which cloud checks currently exist;
- routing local validation work before or after CI;
- explaining the gap between lightweight cloud gates and fuller local/manual
  validation.

## CI Entrypoints

### GitHub Actions

Current lightweight workflow:

- [`.github/workflows/lightweight-validation.yml`](../../.github/workflows/lightweight-validation.yml)

Current scope:

- selector/tooling checks;
- diff-based validation recommendation artifacts for pull requests;
- quick backend `pytest`;
- school frontend build;
- parent frontend build.

Current non-goals:

- no PostgreSQL service container;
- no zero-skip backend guarantee;
- no RAR-dependent attachment environment provisioning;
- no full Playwright E2E run;
- no automatic broad/full selector target execution.

### External CI Definitions

Cloud pipeline examples remain under:

- [`ops/ci/`](../../ops/ci/)

The reference PR pipeline uses:

```bash
python3 -m pytest -q
```

## Local Validation Entry

For detailed local validation workflow, use:

- [`DEVELOPMENT_AND_TESTING.md`](DEVELOPMENT_AND_TESTING.md)
- [`FULL_PLAYWRIGHT_E2E_RUNBOOK.md`](FULL_PLAYWRIGHT_E2E_RUNBOOK.md)
- [`../architecture/TROUBLESHOOTING.md`](../architecture/TROUBLESHOOTING.md)
- [`../../skills/validation-selection/SKILL.md`](../../skills/validation-selection/SKILL.md)

Start with the diff selector:

```bash
python ops/scripts/dev/select_validation_targets.py --worktree
```

## How To Interpret The Current Gate

Treat GitHub Actions as the first cloud gate, not as full production-aligned
validation. A green lightweight workflow does **not** by itself prove:

- PostgreSQL-backed schema parity;
- zero-skip backend validation;
- browser-harness correctness for Playwright;
- attachment extraction paths that depend on extra runtime tools.

Use local/manual validation to close those gaps when the task scope requires
it.

## Agent Reporting Rule

When reporting validation:

- separate selector planning from observed execution;
- separate local execution from remote CI status;
- state when broad/full targets were deferred;
- state when CI scope is intentionally narrower than the requested confidence
  level.

## Related Files

- `docs/testing/DEVELOPMENT_AND_TESTING.md`
- `docs/testing/FULL_PLAYWRIGHT_E2E_RUNBOOK.md`
- `docs/testing/TEST_COVERAGE_MATRIX_AND_RUN_REPORT_2026-05.md`
- `ops/ci/pr-pipeline.yml`
- `.github/workflows/lightweight-validation.yml`
- `skills/validation-selection/SKILL.md`
