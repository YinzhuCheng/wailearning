# Test Execution Pitfalls

## Purpose

This document records pitfalls encountered while executing the repository test suites on Windows + PowerShell during the repository-structure refactor completed on May 1, 2026. The focus here is the tester environment, test runner behavior, and execution workflow friction, not product-code bugs.

This file is meant to save future test operators from rediscovering the same issues.

## Read This Before Running Tests

If you are about to run tests, especially as an LLM coding agent on Windows + PowerShell, check these first:

1. Use the repository `.venv`, not a global Python.
2. Treat `npm.ps1` as suspect; prefer `npm.cmd` or `npx.cmd` when PowerShell policy is restrictive.
3. Assume stale backend or frontend processes may still own your intended ports.
4. Do not trust "a port responds" as proof that the correct app is serving.
5. For Playwright, prefer isolated ports and explicit external-server startup when a run matters.
6. If pytest fails before test bodies execute, inspect temp-path behavior before blaming product code.
7. Do not copy Chinese text from PowerShell output back into tracked files.

If you skip this checklist, you may spend time debugging the shell, temp directories, old background processes, or port collisions instead of the repository itself.

## Scope of the Recorded Session

- Host shell: Windows PowerShell
- Repository root: `C:\Users\bloom\wailearning-e2e-boundary-dynamic-complex-d8c7`
- Python runtime: repository `.venv`
- Frontend package runner: `npm.cmd` / `npx.cmd`
- Browser cache path: `C:\Users\bloom\AppData\Local\ms-playwright`
- Tested after repository structure migration into:
  - `apps/backend/app/`
  - `apps/web/admin/`
  - `apps/web/parent/`
  - `ops/`
  - `tests/e2e/web-admin/`

## Pitfall 1: PowerShell output can display mojibake

### Symptom

Chinese output shown in the terminal may render as mojibake even when the underlying file content is correct.

### Why it matters

- Terminal copy-paste is not trustworthy for Chinese strings.
- Batch files, YAML comments, and legacy script files are especially easy to corrupt if edited by copying text from PowerShell output.

### Safe handling strategy

- Do not copy Chinese text from terminal output back into repository files.
- Prefer patch-based file edits over terminal-mediated rewrite flows.
- When touching files that may already contain Chinese text, treat the file content on disk as authoritative, not the shell rendering.
- If a file appears garbled in the shell, inspect it through a safer path before editing.

## Pitfall 2: `npm` PowerShell shim may be blocked by execution policy

### Symptom

Running `npm run ...` directly from PowerShell can fail with script-execution-policy errors because `npm.ps1` is blocked.

### What worked

Use `npm.cmd` or `npx.cmd` explicitly.

Example:

```powershell
& 'C:\Program Files\nodejs\npm.cmd' run test:e2e
& 'C:\Program Files\nodejs\npx.cmd' playwright test --list
```

### Recommendation

Any automation intended for Windows PowerShell should prefer `.cmd` entrypoints when invoking Node package tools.

## Pitfall 3: sandboxed Node child-process spawning can fail with `EPERM`

### Symptom

Playwright and Vite failed inside the default sandbox with errors such as:

- `spawn EPERM`
- Vite/esbuild startup failure
- Playwright worker fork failure

### Where it happened

- Playwright internal worker processes
- Playwright `webServer` startup mode
- Vite config loading via esbuild

### Operational conclusion

This was an execution-environment limitation, not a repository-code regression.

### What worked

The browser suite had to be run outside the default sandbox on isolated ports, with the backend and frontend started explicitly first.

### Recommendation

If Playwright fails immediately with process-spawn `EPERM`, treat it as an environment problem first, not as an application problem.

## Pitfall 4: Playwright `webServer` auto-start was too fragile for this environment

### Symptom

Even after the repository structure was fixed, Playwright startup remained unreliable when it was allowed to manage backend/frontend servers itself.

### Root causes observed

- sandbox restrictions on subprocess creation
- stale ports responding from older processes
- frontend dev server returning misleading non-application responses

### What worked

Introduce a mode where Playwright does not start `webServer` itself and instead reuses pre-started external servers.

Operationally this required:

- isolated API/UI ports
- explicit health checks
- explicit `E2E_API_URL`
- explicit `PLAYWRIGHT_BASE_URL`
- explicit `PLAYWRIGHT_USE_EXTERNAL_SERVERS=1`

### Recommendation

For long or important Windows E2E runs, prefer:

1. start backend explicitly
2. start Vite explicitly
3. verify API `200`
4. verify UI root returns a real `200`, not just "a port is open"
5. run Playwright against those servers

## Pitfall 5: a `404` from the UI port is not a valid readiness signal

### Symptom

At one point the UI port returned `404`, which looked like "the server is reachable", but the actual SPA was not serving correctly for the intended test session.

### Why this is dangerous

- A stale process or wrong server can occupy the target port.
- The browser tests may then time out on missing controls rather than failing at startup.
- This can waste significant debugging time because the failure presents as missing DOM state instead of incorrect environment boot.

### Recommendation

Treat a UI dev server as healthy only if the root page returns `200` and renders the expected app shell.

Do not accept "some HTTP response exists" as sufficient readiness.

## Pitfall 6: old listening processes can silently poison later test runs

### Symptom

Ports previously used by older frontend or backend processes may remain occupied, causing later runs to hit stale services instead of the newly started test stack.

### Consequences

- false-positive readiness checks
- wrong database backing the test run
- UI selectors timing out because the browser is looking at an old page

### What worked

- use isolated ports for each serious rerun
- explicitly verify both API and UI against the intended process
- avoid reusing 3012/8012 blindly if earlier test attempts may have left residue

## Pitfall 7: pytest temporary-directory behavior on Windows can fail before business assertions run

### Symptom

Backend tests initially failed in pytest temp-directory setup/cleanup with `PermissionError` and directory-numbering failures unrelated to application logic.

Observed failure shapes included:

- cleanup of basetemp failing
- temp root under `%TEMP%` inaccessible
- numbered temp dir creation failing on Windows
- pytest helper symlink behavior not behaving well in this environment

### Important distinction

These were test-runner infrastructure failures, not backend logic failures.

### What was needed

Repository-level pytest bootstrapping had to force a safer Windows temp-root strategy and soften problematic Windows temp-dir behavior for this environment.

### Recommendation

When backend tests fail before test bodies run, inspect pytest temp-path behavior first before blaming the product code.

## Pitfall 8: background process survival differs between direct execution and detached PowerShell sessions

### Symptom

A backend command that stayed alive when run interactively did not necessarily stay alive when launched as a hidden detached process from a separate automation step.

### Consequence

Health checks could fail even though the exact same command was valid.

### What worked

Using a single controlling script that:

- starts the backend,
- starts the frontend,
- waits for health,
- runs the browser tests,
- then tears everything down

was much more reliable than trying to launch background services in one step and test them in later independent shell calls.

## Pitfall 9: migrated test files may lose implicit Node module resolution

### Symptom

After moving E2E specs from `frontend/e2e/` to `tests/e2e/web-admin/`, Node module resolution for `@playwright/test` no longer worked automatically for the moved files.

### Why it happened

The specs were no longer physically under the frontend package tree, so relative module lookup assumptions changed.

### What worked

The Playwright config had to set up module resolution explicitly from the admin frontend package context.

### Recommendation

Whenever tests are moved outside the owning package root, re-check module resolution immediately with `playwright test --list` before attempting the full suite.

## Pitfall 10: `git` index updates may need elevated execution in this environment

### Symptom

Some `git` operations failed with:

- inability to create `.git/index.lock`

### Practical effect

Normal local staging may fail even though file changes are correct on disk.

### Recommendation

If `git add` or related index-writing commands fail with index-lock permission errors in this environment, treat that as an execution-permission problem rather than a repository-integrity problem.

## Proven Command Patterns

### Backend full suite

```powershell
& '.\.venv\Scripts\python.exe' -m pytest tests -rs -q
```

### Playwright test discovery

```powershell
$env:PLAYWRIGHT_BROWSERS_PATH='C:\Users\<user>\AppData\Local\ms-playwright'
& 'C:\Program Files\nodejs\npx.cmd' playwright test --list
```

### Windows-safe Node package invocation

```powershell
& 'C:\Program Files\nodejs\npm.cmd' run test:e2e
& 'C:\Program Files\nodejs\npx.cmd' playwright test
```

## Recommended Execution Order for Future Full Validation

1. Confirm no stale backend/frontend processes are occupying the intended ports.
2. Use the repository `.venv` explicitly for backend commands.
3. Run backend `pytest` first, because it is cheaper and exposes import/path regressions quickly.
4. For Playwright on Windows, prefer isolated ports and explicit external-server startup.
5. Require UI root `200` before starting browser tests.
6. If Playwright fails with `EPERM`, retry outside the restricted sandbox before concluding the suite is broken.
7. If a single concurrency scenario fails after a long mostly-green run, rerun that one case in isolation before treating it as a deterministic regression.

## What This Document Does Not Claim

- It does not claim the product code is bug-free.
- It does not claim all Windows environments need the exact same workarounds.
- It does not claim the sandbox restrictions seen here will match CI or a developer's normal terminal.

It only records what actually happened during this May 1, 2026 validation session so the next operator can start from firmer ground.
