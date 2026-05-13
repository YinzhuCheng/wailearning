# PostgreSQL And Pytest Pitfalls

## Purpose

Use this route when the failure shape suggests:

- PostgreSQL install, startup, or throwaway-cluster issues;
- SQLite vs PostgreSQL semantic drift;
- `TEST_DATABASE_URL` / `COURSEEVAL_AUTO_PG_TESTS` environment gating;
- full-suite skips that are actually missing-environment debt;
- pytest collection or DB reset behavior that fails before business assertions.

This file is a **router and summary**, not the canonical pitfall ledger. The
full historical narratives remain in
[TEST_EXECUTION_PITFALLS.md](TEST_EXECUTION_PITFALLS.md).

## Start Here

1. Run:

   ```powershell
   python ops\scripts\dev\search_pitfalls.py "<postgres or pytest symptom>"
   ```

2. Open:
   [DEVELOPMENT_AND_TESTING.md](DEVELOPMENT_AND_TESTING.md)
3. If the problem is local-environment shaped rather than product behavior,
   route through:
   [../../skills/local-test-triage/SKILL.md](../../skills/local-test-triage/SKILL.md)

## Primary Pitfall Clusters

| Cluster | Start with |
|---------|------------|
| SQLite temp-path / local pytest harness | Pitfall 7, local pytest SQLite sections, Pitfall 81 |
| Windows PostgreSQL bootstrap and local binaries | Pitfalls A-J, Windows Postgres dependency sections |
| PostgreSQL SQL or ORM semantics | Pitfalls 42-45, 57-62 |
| full-suite skip policy and dependency gates | Pitfalls 45-46 and full-suite dependency sections |
| schema/reset / metadata ordering | Pitfalls 79 and the PostgreSQL full-suite notes |

## Key Pitfalls

- **Pitfall 7**: pytest temp-path behavior on Windows can fail before test
  bodies execute.
- **Pitfalls A-J**: PostgreSQL on Windows often fails in provisioning, process
  lifetime, or startup-wrapper ways before any repo code is wrong.
- **Pitfall 42**: PostgreSQL rejects trailing commas in `IN (...)` lists.
- **Pitfall 43**: `Session.merge()` is not always a safe test-side upsert.
- **Pitfall 45**: many skips are environment gates, not optional quality.
- **Pitfall 46**: disposable Linux/cloud runners may simply lack `pytest`
  until `requirements.txt` is installed.
- **Pitfall 79**: some isolated pytest modules are sensitive to import order
  around `main.py` and DB reset helpers.

## Recommended Commands

```bash
python ops/scripts/dev/pytest_sqlite_guard.py --json
bash ops/scripts/dev/provision_postgres_pytest.sh
python3 -m pytest tests/ -q
```

Use:

- `TEST_DATABASE_URL` for explicit PostgreSQL runs
- `COURSEEVAL_AUTO_PG_TESTS=1` when following the repo's throwaway Postgres
  auto-pick path

## Related Files

- [TEST_EXECUTION_PITFALLS.md](TEST_EXECUTION_PITFALLS.md)
- [DEVELOPMENT_AND_TESTING.md](DEVELOPMENT_AND_TESTING.md)
- [../../skills/postgres-release-validation/SKILL.md](../../skills/postgres-release-validation/SKILL.md)
- [../../skills/local-test-triage/SKILL.md](../../skills/local-test-triage/SKILL.md)


## Detailed migrated entries

## Incremental Field Notes: PostgreSQL-Aligned UI/UX Audit on Windows

This subsection records a later UI/UX audit setup pass where the operator needed
real browser screenshots against a PostgreSQL-backed backend, not the default
SQLite-backed Playwright webServer path. These notes are intentionally additive:
they do not replace the earlier Playwright or PostgreSQL guidance above.

### Goal

The audit goal was to inspect the school SPA through Playwright screenshots while
using a production-aligned PostgreSQL database. SQLite was acceptable only for
quick local smoke and was explicitly rejected as the main evidence source for
UI/E2E behavior that depends on real persistence semantics.

### What worked

The reliable approach in a restricted Windows automation environment was:

1. Use an ignored artifact directory such as `<repo>/.e2e-run/postgres-runtime/`.
2. Download an official EDB PostgreSQL Windows x64 binary zip into that ignored
   directory. The pass used PostgreSQL `16.13`.
3. Extract the archive locally and use the bundled `initdb.exe`,
   `postgres.exe`, `psql.exe`, and `pg_isready.exe` from
   `<artifact-dir>/pgsql/bin/`.
4. Initialize a local throwaway cluster in an ignored data directory, for
   example `<artifact-dir>/data-clean`, with local trust auth.
5. Run PostgreSQL on a non-production loopback port, for example
   `127.0.0.1:15432`.
6. Create a clearly disposable database such as `courseeval_uiux_audit`.
7. Start the backend with:
   - `DATABASE_URL=postgresql://postgres@127.0.0.1:15432/courseeval_uiux_audit`
   - `E2E_DEV_SEED_ENABLED=true`
   - `E2E_DEV_SEED_TOKEN=<test token>`
   - `INIT_DEFAULT_DATA=false`
   - `ENABLE_LLM_GRADING_WORKER=false`
   - a local-only `SECRET_KEY`
8. Seed data through `POST /api/e2e/dev/reset-scenario` with the same
   `X-E2E-Seed-Token`.
9. Start Vite from `apps/web/school` with
   `VITE_PROXY_TARGET=http://127.0.0.1:<api-port>`.
10. Use Playwright screenshots and DOM snapshots against the Vite URL.

### Pitfall A: local machine may have no PostgreSQL service, Docker, psql, or winget

The pass first checked for:

- a running PostgreSQL service,
- `psql.exe` / `postgres.exe` / `pg_ctl.exe`,
- Docker,
- `winget`,
- `DATABASE_URL` / `TEST_DATABASE_URL`.

None were available in that environment. Do not assume a Windows machine already
has a database runtime just because the repository is PostgreSQL-first.

### Pitfall B: Chocolatey can exist but still be unusable for PostgreSQL install

Chocolatey was installed, but `choco install postgresql` failed because the shell
did not have administrator access to Chocolatey system directories and could not
write `lib-bad` or clear package lock state.

Avoid treating "Chocolatey exists" as equivalent to "the agent can install a
system PostgreSQL service." If Chocolatey needs admin rights, prefer a
user-directory binary archive when the task only needs a temporary local
database.

### Pitfall C: `pg_ctl` can fail on restricted Windows tokens

`initdb.exe` completed the cluster initialization but emitted Windows restricted
token errors at the end. `pg_ctl.exe start` also failed with restricted token
errors. The cluster files were still usable.

What worked was direct `postgres.exe -D <data-dir> -h 127.0.0.1 -p <port>` rather
than `pg_ctl.exe`, provided the process was launched in a context that could keep
it alive for the audit.

### Pitfall D: PostgreSQL writes normal LOG output to stderr

When wrapping `postgres.exe` with PowerShell, normal PostgreSQL startup lines can
arrive on stderr. If a wrapper script sets `$ErrorActionPreference = 'Stop'`,
PowerShell may treat a harmless startup LOG line as a native command error and
exit before PostgreSQL finishes starting.

For wrapper scripts around `postgres.exe`, either avoid `Stop` for native stderr
or redirect/handle stderr deliberately.

### Pitfall E: background process lifetime can differ by launcher

Several background launch attempts returned a process id but did not leave a
listening PostgreSQL server for the next command. Direct foreground startup
proved PostgreSQL itself was valid, but hidden `Start-Process`, `cmd /c`, and
PowerShell job patterns were unreliable in that sandboxed automation context.

When cross-command background processes are unreliable, use one orchestrator
process that starts PostgreSQL, backend, frontend, and Playwright inside the same
lifetime. In this pass, a local ignored Node script performed that orchestration.

### Pitfall F: Node child process spawn may be blocked in the default sandbox

The orchestrator initially failed with `spawn EPERM`, matching the broader
Playwright webServer `EPERM` pitfall. The fix was to run the orchestrator outside
the restricted sandbox/with the necessary execution approval. This is an
environment restriction, not evidence that PostgreSQL, Vite, or the app is
broken.

### Pitfall G: Vite must be started from the school app directory

Starting Vite with the Vite binary path while the current working directory was
the repository root produced a root URL that returned `404`. The fix was to set
the frontend process working directory to `<repo>/apps/web/school` before running
Vite.

This matters for custom audit scripts and external-server Playwright flows:
`node <repo>/apps/web/school/node_modules/vite/bin/vite.js` is not sufficient by
itself if the working directory is wrong.

### Pitfall H: repeated role login can hang if the previous session is still active

A screenshot script that logs in as admin and then navigates to `/login` to log
in as teacher/student can hang or redirect unexpectedly if the app immediately
redirects an already-authenticated user away from `/login`.

The robust helper should clear `localStorage` and `sessionStorage` before each
fresh role login, then navigate to `/login` and submit credentials.

### Pitfall I: PostgreSQL recovery after forced audit timeouts can add startup delay

Several interrupted experiments left the throwaway cluster needing crash
recovery. `pg_isready` reported `rejecting connections` before eventually
accepting connections. For clean audit runs, either shut PostgreSQL down
gracefully or reinitialize a new throwaway data directory such as
`data-clean`.

### Pitfall J: DOM snapshots and screenshots can disagree during page startup

A UI audit can produce a JSON snapshot showing that page text, buttons, and
routes exist while the paired screenshot is still blank or partially painted.
This usually means the screenshot was taken before the stable visual container
was visible, not that the JSON snapshot is wrong.

For login and other app-shell entry pages, do not rely on `page.goto(...)`
alone. Add stable page-level test IDs in product code and wait for the visible
panel before capture. Example pattern:

```javascript
await page.goto('/login', { waitUntil: 'domcontentloaded' })
await page.getByTestId('login-panel').waitFor({ state: 'visible', timeout: 30000 })
await page.waitForTimeout(300)
await capture(page, 'login')
```

The exact script path should be documented as `<repo>/...` or
`<artifact-dir>/...` in committed docs. If the machine-specific path matters for
a handoff, put it in an ignored local note instead.

### Artifact hygiene

Keep all of the following out of tracked source:

- downloaded PostgreSQL zips,
- extracted PostgreSQL binaries,
- local data directories,
- audit launch scripts,
- screenshots,
- runtime logs,
- seeded scenario JSON files.

Use ignored directories such as `.e2e-run/`. If a temporary spec is created under
`tests/e2e/...` for experimentation, delete it before committing unless it is a
deliberate maintained test.

### Privacy hygiene

Do not paste user-specific absolute paths into committed documentation. Use
placeholders such as:

- `<repo>`
- `<user-home>`
- `<artifact-dir>`
- `<api-port>`
- `<ui-port>`

Local handoff files can contain machine-specific paths when the next operator on
the same machine needs them, but committed docs should stay portable.
