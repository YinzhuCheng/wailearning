# Repository Normalization + PostgreSQL Validation Handoff

Date: 2026-05-12

Branch: `cursor/repository-normalization`

Latest committed cleanup baseline before this handoff:

- `38149b7 chore: normalize course schedules and markdown demos`

## User Direction

The user asked for broad repository cleanup under `AGENTS.md`, specifically:

- remove old implementations, redundant code, and "double-track" behavior;
- go beyond only the newly touched feature and inspect the wider repository;
- validate through the repository route;
- commit and push;
- then fix the local environment until PostgreSQL validation could run;
- record encountered pitfalls, promote reusable knowledge into skills, and
  write this handoff.

## Completed Product Cleanup

The previous commit normalized course schedule handling:

- `course_times` is now the backend source of truth for course schedules;
- top-level subject fields `weekly_schedule`, `course_start_at`, and
  `course_end_at` were removed from models, schemas, bootstrap DDL, route
  serialization/create/update logic, seed assignment, and tests;
- the student `MyCourses.vue` course creation UI now edits `course_times`
  directly instead of keeping a separate legacy schedule form;
- remaining `weekly_schedule`, `course_start_at`, and `course_end_at` names are
  legitimate inner fields of each `course_times[]` item or frontend helpers
  that edit/render that shape.

The same cleanup also handled the user-facing UI findings:

- `MarkdownLatexLiveDemo.vue` card and image examples stay collapsed by default
  and expose explicit show/hide toggles;
- the homework dialog E2E now verifies cards and image examples are hidden until
  clicked;
- the sidebar brand is `CourseEval`;
- student sidebar icons are distinct, including `学习主页` and `我的成绩`;
- active tracked code/docs were checked for `CourEval` and no live hits remain;
- demo learning-note text was repaired from placeholder/mojibake-like content
  to valid Chinese Markdown.

## PostgreSQL Environment Fix

The earlier PostgreSQL blocker was not the product code. The local host had
Python 3.14, while the committed dependency set still pinned:

- `psycopg2-binary==2.9.9`, which source-builds on Python 3.14 and failed;
- `pydantic==2.5.3`, which pulls an old `pydantic-core` without cp314 wheels.

This round updated `requirements.txt` to the locally proven Python-3.14-capable
combination:

- `psycopg2-binary==2.9.12`
- `pydantic==2.13.4`
- `pydantic-settings==2.14.0`

`pip check` passed after this environment was populated.

## PostgreSQL Validation Evidence

An ignored local orchestrator under `.agent-run/` started a fresh throwaway
PostgreSQL cluster from local binaries, created the disposable role/database,
set `TEST_DATABASE_URL`, ran the Postgres package, and stopped the process.

Executed target:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\postgres -q
```

Result:

- `42 passed`
- warnings were existing Pydantic deprecation warnings plus a local pytest cache
  path warning;
- no PostgreSQL assertion failed.

The first `initdb.exe` attempt failed in the default sandbox with
`could not create restricted token: error code 87`. The same command succeeded
when rerun in an approved non-restricted PowerShell context. This is now
documented in `docs/development/TEST_EXECUTION_PITFALLS.md` and
`skills/postgres-release-validation/SKILL.md`.

## Documentation And Skill Updates In This Round

Updated:

- `skills/postgres-release-validation/SKILL.md`
  - records Python 3.14 + `psycopg2-binary` wheel requirements;
  - records the Windows local-binary orchestrator pattern;
  - warns to keep paths/logs under ignored artifacts.
- `docs/development/TEST_EXECUTION_PITFALLS.md`
  - records the `psycopg2-binary==2.9.9` Python 3.14 failure mode;
  - records the `initdb.exe` restricted-token failure and approved-context fix;
  - records that Chocolatey/download failures do not necessarily block
    PostgreSQL validation if a compatible venv and local PG binaries exist.
- `ops/scripts/dev/playwright_preflight.py`
  - now describes Python 3.14 compatibility in terms of stale pins rather than
    implying all current pins are risky once upgraded.

## Validation Already Completed For The Cleanup Commit

Before commit `38149b7`, the following relevant checks passed:

- repository normalization guard: `stale=0`;
- `git diff --check`;
- targeted text encoding checks;
- API/schema governance checks;
- validation selector unittest suite;
- frontend Markdown/clipboard Node tests;
- backend demo seed tests;
- roster/course behavior pytest targets;
- admin SPA production build;
- targeted admin Playwright markdown reader spec, `13/13`.

After the environment fix in this handoff round:

- `pip check` passed;
- `ops/scripts/dev/playwright_preflight.py --json` passed all checks, and after
  dependency pin edits it should no longer report the old psycopg2/pydantic pin
  risk once rerun;
- `tests/postgres` passed under PostgreSQL: `42 passed`.

## Remaining Concerns

Full-tree PostgreSQL pytest (`full.pytest.postgres`) has not been run in this
round. The focused PostgreSQL package is now proven runnable, but the full tree
is still the release-quality target for schema-sensitive changes.

Full admin Playwright was not rerun after the dependency pin edits. The prior
targeted Playwright spec passed for the cleanup behavior, and preflight is
green, but broad frontend routing/seed coverage remains outside this round's
timebox.

The local orchestrator is intentionally ignored under `.agent-run/`; it should
not be committed as-is because it contains machine-specific binary locations.
If this workflow becomes common, promote it into a portable `ops/scripts/dev`
Windows helper that accepts `<local-postgres-bin>`, `<artifact-dir>`, and
`<local-port>` parameters.

The dependency pin upgrade follows the local working environment. If maintainers
want strict Python 3.11/3.12-only release pins instead, they should decide that
explicitly; otherwise the current branch is more reproducible for this Windows
Python 3.14 host.
