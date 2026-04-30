# Testing Pitfalls And Runbook

This note records testing-side problems only.

It is meant to help the next person run the test suite faster and more safely.
Repository bugs themselves are documented in `tests/REPO_ISSUES_EXPOSED_BY_THIS_ROUND.md`.

## 1. Transferable lessons for a coding agent

These are not specific to this repository. They are likely to repeat in other projects.

### 1.1 Do not trust UI copy too early

- Several Playwright failures were caused by selectors tied to dialog titles, labels, toast text, or full table-row text.
- Those selectors are fragile under:
  - i18n or encoding changes
  - UI animation timing
  - pagination or filtering
  - product wording changes
- Better default order:
  - `data-testid`
  - outcome-level checks such as API polling or login success
  - plain text matching only as a last resort

### 1.2 A targeted replay passing does not prove the full suite is stable

- Multiple cases passed when run alone and still failed in the full suite.
- Common reasons:
  - incomplete state isolation
  - different timing after many prior tests
  - helper reset paths that cover only part of the state
- Practical rule:
  - after a local fix, rerun the target test
  - then rerun the relevant spec
  - then rerun the full suite

### 1.3 Separate business failures from test-environment failures

- This round had both real repository bugs and pure test-run failures.
- A good example was `pytest -rs` launched from `C:\Windows\system32`:
  - relative `--basetemp` from `pytest.ini` resolved into the system directory
  - RAR-related tests failed in setup
  - that was a run-directory problem, not a product bug

### 1.4 Be more sensitive to Windows working directory and relative paths

- On many repos, people assume tests always run from repo root.
- In this environment, starting from `system32` can break:
  - relative temp paths
  - generated artifacts
  - test discovery side effects
- Default discipline:
  - set `workdir` explicitly to repo root
  - do not rely on caller cwd
  - inspect relative paths in `pytest.ini` before blaming the code

### 1.5 Avoid treating "UI animation fully finished" as the main assertion

- In Element Plus flows, `toBeHidden()` often waits for animation completion, not for the business action itself.
- The backend action may already have succeeded.
- Better pattern:
  - assert the business result first
  - wait for animation only if the next step truly depends on it

## 2. Project-specific testing lessons

### 2.1 This repo requires separating backend bugs from frontend-test instability

- This round fixed real backend startup bugs.
- The remaining Playwright failures were mostly about:
  - selectors
  - animation timing
  - list refresh and pagination
- In this repo, a red test does not automatically mean the same failure layer every time.

### 2.2 `tests/conftest.py` and worker-state isolation are critical

- If `worker_manager`, `ENABLE_LLM_GRADING_WORKER`, and `E2E_DEV_SEED_*` are not reset, backend tests can leak state into later tests.
- That leakage is not obvious in isolated runs and becomes visible in full-suite runs.

### 2.3 Playwright scenarios must reseed per test

- These E2E cases mutate real course, enrollment, homework, appeal, notification, and LLM-config state.
- Sharing one mutable seed across tests causes downstream contamination.
- The `beforeEach -> resetE2eScenario()` pattern should be kept.

### 2.4 "More realistic environment simulation" here means more than "browser runs"

- High-value realism in this repo came from:
  - real worker enabled by default
  - queue drain through the worker path
  - mock LLM support for empty body, bad JSON, sleep, and request indexing
- Those changes were much more valuable than simply opening a browser.

### 2.5 This round confirmed a command-line encoding risk

- The mojibake that appeared in `frontend/e2e/e2e-scenario-boundary-dynamic-complex.spec.js`
  was mainly introduced by the Windows + PowerShell + string-rewrite editing chain.
- That does not mean the repo has no text fragility.
- The actual risk was the combination of:
  - many Chinese text selectors in tests
  - command-line batch editing of Chinese source strings
- Safer follow-up rules:
  - do not bulk-rewrite Chinese source text from the shell
  - prefer git-history-based reconstruction for already-corrupted files
  - move high-frequency test selectors toward `data-testid`

### 2.6 Recommended execution pattern for this repo

- Backend full run:
  - start from repo root
  - run `.\.venv\Scripts\python.exe -m pytest`
- To inspect skips:
  - also run from repo root
  - add `-rs`
- Playwright:
  - use the repo's fixed environment variables
  - point `PLAYWRIGHT_BROWSERS_PATH` at the local browser cache
  - run targeted cases first, then the full suite

### 2.7 Current testing state

- Backend `pytest` full run passed earlier in repo-root execution:
  - `281 passed, 3 skipped`
- A later `pytest -rs` run from `system32` showed an environment-side temp-path failure on RAR tests.
- Playwright full run is not fully green yet:
  - the remaining failures are selector, animation, and list-refresh issues
  - they are no longer the original startup unique-constraint bugs
