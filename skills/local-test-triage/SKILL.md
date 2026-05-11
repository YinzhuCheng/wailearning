---
name: local-test-triage
description: Use this when CourseEval local pytest, SQLite, Playwright, port, process, dependency, or Windows PowerShell test failures look environment-related or inconsistent with ordered full-suite behavior.
---

# Local Test Triage

## Purpose

Separate real product regressions from known local harness hazards before
changing code. Convert repeatable pitfalls into docs, scripts, or selector
guardrails when practical.

## Workflow

1. Read `docs/development/DEVELOPMENT_AND_TESTING.md`,
   `docs/development/TEST_EXECUTION_PITFALLS.md`, and
   `docs/known-issues-and-risks.md`.
2. Check whether a failure is environment-shaped: missing module, port
   collision, missing browser, stale Playwright process, corrupted SQLite file,
   or concurrent pytest processes.
3. For SQLite weirdness, confirm no residual pytest/Python process is using
   `.pytest_tmp/test*.sqlite` before deleting or reusing it. Prefer the
   read-only guardrail script before manual process inspection.
4. Reproduce with one process and the narrowest relevant target.
5. If the failure is a real product regression, fix code/tests and run the
   selector-recommended targets.
6. If it is a repeatable harness pitfall, document it or add a guardrail.

## Commands

```powershell
python ops/scripts/dev/pytest_sqlite_guard.py
python ops/scripts/dev/pytest_sqlite_guard.py --json
python ops/scripts/dev/pytest_sqlite_guard.py --fail-on-active-pytest
Get-CimInstance Win32_Process | Where-Object { $_.Name -match 'python|pytest|py\.exe' } | Select-Object ProcessId,Name,CommandLine
python ops/scripts/dev/select_validation_targets.py --worktree
python ops/scripts/dev/run_validation_target.py <target-id> --timeout-seconds 120
```

## Guardrails

- Do not run concurrent pytest processes against the same SQLite artifact.
- Do not delete `.pytest_tmp/test*.sqlite` until no process is using it.
- `pytest_sqlite_guard.py` is read-only: it reports active pytest processes and
  SQLite file state, but does not stop processes or delete files.
- Treat isolated discussion-file SQLite reset noise as a harness concern unless
  it appears in ordered full-suite progression.
- Classify missing tools, port collisions, and Playwright browser absence as
  environment blockers, not product failures.
- Keep `.agent-run/` logs and machine paths out of committed docs.

## Related Files

- `tests/conftest.py`
- `tests/db_reset.py`
- `ops/scripts/dev/pytest_sqlite_guard.py`
- `docs/development/TEST_EXECUTION_PITFALLS.md`
- `docs/known-issues-and-risks.md`
- `ops/scripts/dev/run_validation_target.py`
