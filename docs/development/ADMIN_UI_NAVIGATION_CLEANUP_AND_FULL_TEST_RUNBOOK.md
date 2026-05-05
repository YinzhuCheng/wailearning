# Admin SPA Navigation Cleanup and Full Regression Test Runbook

This document is written primarily for automated coding agents (LLM-based or CI workers) that must reproduce a known-good verification path after UI navigation changes. Human readers may find it long; that is intentional: agents benefit from exhaustive, low-ambiguity steps and failure-mode notes.

## Mandatory upstream reading (do not skip)

Before changing admin navigation, global layout chrome, or repository-wide test assumptions, read at least:

1. [REPOSITORY_STRUCTURE.md](../architecture/REPOSITORY_STRUCTURE.md) — canonical paths for `apps/web/admin/` and test locations.
2. [DEVELOPMENT_AND_TESTING.md](DEVELOPMENT_AND_TESTING.md) — pytest environment variables, Playwright caveats, and PostgreSQL conventions.
3. [TEST_EXECUTION_PITFALLS.md](TEST_EXECUTION_PITFALLS.md) — false failures from ports, shims, and timing.
4. [ENCODING_AND_MOJIBAKE_SAFETY.md](ENCODING_AND_MOJIBAKE_SAFETY.md) — when editing multilingual UI strings or documentation, avoid introducing mojibake; prefer UTF-8 end-to-end.

## What changed in the admin UI (this change set)

### Sidebar (`apps/web/admin/src/views/Layout.vue`)

**Goal:** reduce a flat list of top-level admin entries that were conceptually one family (users, classes, courses, students) and duplicate “personal settings” placement.

1. **Administrator role:** the former flat items `学生管理`, `班级管理`, `用户管理`, `课程管理` are grouped under a single second-level submenu labelled **「用户与教学」** (`admin-core`). Indices used by `default-openeds` were extended so that visiting any of `/students`, `/classes`, `/users`, `/subjects` expands this submenu automatically.
2. **Existing second-level groups** (`学期与配置`, `消息与审计`) are unchanged in purpose; only the admin default-opened index logic gained the `admin-core` branch.
3. **Personal settings:** remain a **top-level** sidebar item for every role (administrator, class teacher, teacher, student) because it is a cross-cutting concern and must stay one click away after removing the redundant user-menu entry (see below).

### Header user dropdown

**Removed:** the actionable menu item **「个人设置」** from the avatar dropdown.

**Rationale:** the same destination is available from the sidebar on all roles; keeping it in the dropdown duplicated navigation and increased cognitive load (“two ways to do the same thing”) without adding capability.

**Kept:** the disabled “profile card” block at the top of the dropdown (avatar + display name + role + username) for at-a-glance identity confirmation.

**Conditional block — LLM quota summary:** the progress block labelled for LLM daily quota is now rendered **only for students** (`v-if="userStore.isStudent"` on the quota container). For teachers and administrators the English placeholder strings such as `Managed in system LLM quota settings.` were misleading noise because those roles are not backed by the same student quota API semantics in the header dropdown context. Agents must not reintroduce non-student quota text without wiring a real teacher/admin aggregate API.

### Homework list page (`apps/web/admin/src/views/Homework.vue`)

1. **Removed** the header button **「学生作业一览」** for non-student users when a course is selected.

   **Rationale:** the same route `/homework/students` remains in the **sidebar** under **「作业与资料」** for teachers. The header duplicate was rarely needed once the sidebar structure exists and violated the “one obvious path” principle.

2. **Replaced** the student-row `el-dropdown` split button (primary action + single dropdown item “仅查看说明”) with two explicit buttons: **「作业与提交」** (primary) and **「仅看说明」** (plain small).

   **Rationale:** a dropdown with exactly one secondary entry is poor affordance; two buttons communicate both actions without an extra click target. Automated UI tests that previously assumed a dropdown structure for student homework rows must be updated if any exist (grep for `el-dropdown` in homework specs).

## Pitfalls encountered while validating this work (agent-oriented)

These are real failure modes observed or narrowly avoided during implementation and test preparation. Use them when triaging “tests pass locally but fail in cloud agent” tickets.

### Pitfall A — `python` vs `python3` on minimal Linux images

Some containers ship **only** `python3`. Invoking `python -m pytest` fails with `command not found`. Prefer:

```bash
python3 -m pytest ...
```

### Pitfall B — PostgreSQL `tests/postgres/*` modules skip unless the engine is PostgreSQL

The repository `tests/conftest.py` defaults `DATABASE_URL` to a **file-backed SQLite** URL when neither `TEST_DATABASE_URL` nor `WAILEARNING_AUTO_PG_TESTS` yields a working Postgres URL. Many modules under `tests/postgres/` carry:

```python
pytestmark = pytest.mark.skipif(engine.dialect.name != "postgresql", ...)
```

**Symptom:** full `pytest` run reports dozens of skips for `tests/postgres/*` even though you intended a “full” run.

**Remediation (explicit URL — recommended for agents claiming full regression):**

```bash
export TEST_DATABASE_URL='postgresql+psycopg2://<USER>:<PASSWORD>@127.0.0.1:5432/<DBNAME>'
```

Use a **dedicated throwaway database** (never production). The suite issues `DROP SCHEMA public CASCADE` during resets (`tests/db_reset.py`).

**Remediation (auto-pick documented default — optional):**

```bash
export WAILEARNING_AUTO_PG_TESTS=1
```

This path probes `127.0.0.1:5432` and credentials matching `tests/conftest.py::_default_postgres_pytest_url()` (see that file for the exact URL string). It only activates when TCP and `psycopg2.connect` succeed.

### Pitfall C — PostgreSQL installed but not started (policy-rc.d / container images)

On Debian-derived CI images, `apt-get install postgresql` may complete without the daemon running if `policy-rc.d` denies service start during package configuration.

**Symptom:** `pg_isready` fails; psycopg2 connection errors.

**Remediation:** start the cluster explicitly, e.g. `pg_ctlcluster <version> main start` or `service postgresql start`, then re-run `pg_isready -h 127.0.0.1 -p 5432`.

### Pitfall D — RAR attachment tests and `unrar` binary name

`tests/backend/llm/test_llm_attachment_formats.py` calls `_require_unrar()` which accepts either `unrar` **or** `unrar-free` on `PATH`. Installing only `unrar-free` is sufficient on Ubuntu. If both are missing, those tests **skip** with a message about installing `unrar`.

**Agent requirement:** for a “no skip” claim on RAR cases, install `unrar-free` (or `unrar`) before pytest.

### Pitfall E — Playwright / E2E scope

This change set primarily touches Vue layout and homework list chrome. The repository’s Playwright suite is large and environment-sensitive (see `DEVELOPMENT_AND_TESTING.md`). A **full** Playwright run is not automatically required for every navigation-only change unless the project gate explicitly demands it; however, any spec that asserted the presence of removed UI (duplicate “个人设置” in the user dropdown, homework header “学生作业一览”, or student homework split-button dropdown) must be updated.

**Search hints for maintainers:**

```bash
rg "学生作业一览|personal-settings|split-button|header-user-menu" apps/web/admin tests/e2e
```

### Pitfall F — Encoding when editing Chinese labels

Edits touched Chinese navigation labels. Always save files as **UTF-8** without BOM. If a terminal or editor mis-decodes UTF-8 as Latin-1, mojibake can be committed; follow `ENCODING_AND_MOJIBAKE_SAFETY.md` and verify with `git diff` byte inspection when in doubt.

### Pitfall G — Vite `npm run build` catches syntax errors that IDE diagnostics may miss

If a shared module such as `apps/web/admin/src/utils/theme.js` is missing a closing brace or otherwise invalid, **Vite/Rollup fails at build time** with a parse error (for example `Failed to parse source for import analysis`). The same file may still appear acceptable to lightweight lint passes.

**Remediation:** after edits to files on the admin bundle’s import graph, run:

```bash
cd <REPO_ROOT>/apps/web/admin
npm ci
npm run build
```

## Suggested verification commands (placeholder paths)

Replace `<REPO_ROOT>` with your clone path (example: `/workspace` in cloud agents, or `/opt/dd-class/source` on a deployment server when validating built assets).

### Backend full pytest (PostgreSQL URL explicit)

```bash
cd <REPO_ROOT>
export PYTHONPATH=<REPO_ROOT>
export TEST_DATABASE_URL='postgresql+psycopg2://wailearning_test:wailearning_test@127.0.0.1:5432/wailearning_pytest_all'
python3 -m pip install -r requirements.txt
python3 -m pytest tests -q --tb=short
```

### Admin production build smoke (optional but recommended after Vue edits)

```bash
cd <REPO_ROOT>/apps/web/admin
npm ci
npm run build
```

## Verification outcomes recorded for this branch (agent log)

The following commands were executed successfully on a Linux agent image after installing OS packages `postgresql`, `postgresql-contrib`, `unrar-free`, `nodejs`, and `npm` (exact package names may differ on non-Debian bases):

- **PostgreSQL throwaway role/database:** created `wailearning_test` / `wailearning_pytest_all` on `127.0.0.1:5432` (credentials must match `TEST_DATABASE_URL` below).
- **Full pytest:** `export PYTHONPATH=<REPO_ROOT>` and `export TEST_DATABASE_URL='postgresql+psycopg2://wailearning_test:wailearning_test@127.0.0.1:5432/wailearning_pytest_all'` then `python3 -m pytest tests -q` → **433 passed**, **0 skipped** (collection count 433).
- **Admin bundle:** `cd <REPO_ROOT>/apps/web/admin && npm ci && npm run build` → **success** (Vite emitted existing chunk-size warnings only).

Playwright E2E was **not** re-run as part of this agent turn because the repository gate for this change was backend + production build smoke; if CI requires Playwright, follow `DEVELOPMENT_AND_TESTING.md` and ensure `E2E_DEV_SEED_TOKEN` plus backend availability.

## Traceability

- Vue layout: `apps/web/admin/src/views/Layout.vue`
- Homework list: `apps/web/admin/src/views/Homework.vue`
- Theme tokens (unchanged in this doc’s scope but related to prior appearance work): `apps/web/admin/src/utils/theme.js`, `apps/web/admin/src/style.css`
