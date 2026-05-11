---
name: postgres-release-validation
description: Use this when CourseEval needs production-aligned backend validation, zero-skip pytest evidence, PostgreSQL dialect coverage, schema-sensitive confidence, or release-quality validation beyond SQLite fast loops.
---

# PostgreSQL Release Validation

## Purpose

Use PostgreSQL as the production-aligned backend validation reference for
schema, constraint, transaction, and dialect-sensitive behavior. SQLite is a
fast local loop, not final evidence for schema-sensitive changes.

## Workflow

1. Read `docs/development/DEVELOPMENT_AND_TESTING.md`,
   `docs/development/TEST_EXECUTION_PITFALLS.md`, and
   `docs/development/TEST_COVERAGE_MATRIX_AND_RUN_REPORT_2026-05.md`.
2. Provision a throwaway PostgreSQL database. Never point tests at production
   or shared operator data.
3. Ensure attachment tooling is present if claiming full zero-skip evidence:
   install `unrar`, `unrar-free`, or a compatible archive extractor.
4. Export `TEST_DATABASE_URL`, or use `COURSEEVAL_AUTO_PG_TESTS=1` after the
   standard local provisioner succeeds.
5. Run the smallest PostgreSQL target needed first, then full `tests/` only
   when the task asks for release-quality confidence.
6. Record blocked, skipped, or timed-out runs honestly. Do not convert
   environment skips into passing evidence.

## Commands

```bash
bash ops/scripts/dev/provision_postgres_pytest.sh
export TEST_DATABASE_URL='postgresql+psycopg2://courseeval_test:courseeval_test@127.0.0.1:5432/courseeval_pytest_all'
python3 -m pytest tests/postgres -q
python3 -m pytest tests -q
```

Windows agents may use the repository virtualenv interpreter once
`TEST_DATABASE_URL` points to a reachable PostgreSQL instance:

```powershell
$env:TEST_DATABASE_URL='postgresql+psycopg2://courseeval_test:courseeval_test@127.0.0.1:5432/courseeval_pytest_all'
.\.venv\Scripts\python.exe -m pytest tests\postgres -q
```

## Guardrails

- Do not run concurrent pytest processes against the same PostgreSQL database;
  `tests/db_reset.py` resets schemas destructively.
- Treat SQLite-only green as insufficient for schema, raw SQL, FK, enum,
  uniqueness, or transaction changes.
- Do not memorize a permanent passed-test integer. Track skip classes and
  target coverage instead.
- Keep local database paths, credentials beyond documented throwaway defaults,
  logs, and generated artifacts out of committed docs.

## Related Files

- `ops/scripts/dev/provision_postgres_pytest.sh`
- `tests/postgres/`
- `tests/db_reset.py`
- `docs/development/DEVELOPMENT_AND_TESTING.md`
- `docs/development/TEST_EXECUTION_PITFALLS.md`
- `docs/development/testing/test-execution-targets.csv`
