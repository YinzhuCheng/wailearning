# Full admin Playwright E2E runbook (`npm run test:e2e`)

## Purpose and audience

This document exists primarily for **LLM coding agents** and automation operators who must run **`apps/web/admin`** → **`npm run test:e2e`** (full Playwright suite: all specs under `tests/e2e/web-admin/`, typically **single-worker serial** per `playwright.config.cjs`). Humans may skim headings and commands; agents should read the failure triage sections before rewriting product code.

**Goal:** reduce wasted steps on environment gaps, seed/token mismatches, selector ambiguity in complex DOM, layout geometry traps, and **SQLite persistence effects** across hundreds of `resetE2eScenario()` calls.

**Implicit premise:** full-suite runs often mean **one backend process** plus a **file-backed SQLite database** reused for the entire CLI session. Many “single spec green, full suite red” outcomes are **state accumulation + harness ambiguity**, not necessarily broken business logic.

Cross-reference: [TEST_EXECUTION_PITFALLS.md](TEST_EXECUTION_PITFALLS.md) (numbered pitfalls), [DEVELOPMENT_AND_TESTING.md](DEVELOPMENT_AND_TESTING.md), [ENCODING_AND_MOJIBAKE_SAFETY.md](ENCODING_AND_MOJIBAKE_SAFETY.md).

---

## Hard prerequisites (treat as blocking)

### Repository paths (placeholders)

- `<REPO_ROOT>` — git checkout root.
- `<ADMIN_PKG>` — `<REPO_ROOT>/apps/web/admin` (the **only** directory that owns admin `package.json` for Playwright).
- `<E2E_SQLITE>` — file path derived from Playwright config (commonly `/tmp/playwright_e2e_<E2E_API_PORT>.sqlite` on Unix; see `apps/web/admin/playwright.config.cjs`).

### Node / npm

Do **not** assume a minimal CI image ships Node. On Debian/Ubuntu-style agents:

```bash
sudo apt-get update
sudo apt-get install -y nodejs npm
```

Versions vary by distribution; they must satisfy `apps/web/admin/package-lock.json` expectations for `npm ci`.

### Frontend install location

Run dependency install **inside** `<ADMIN_PKG>`, not only at `<REPO_ROOT>`:

```bash
cd <REPO_ROOT>/apps/web/admin
npm ci
```

Anti-pattern: installing nothing under `<ADMIN_PKG>` then `npm run test:e2e` → `npm: command not found` or missing `@playwright/test` (see **Pitfall 48** in [TEST_EXECUTION_PITFALLS.md](TEST_EXECUTION_PITFALLS.md)).

### Playwright browsers

```bash
cd <REPO_ROOT>/apps/web/admin
npx playwright install chromium
```

If the project config only targets Chromium, installing Chromium alone is usually sufficient.

### Python backend invoked by `webServer`

Playwright `webServer` starts uvicorn. The interpreter must have **`requirements.txt`** installed:

```bash
cd <REPO_ROOT>
python3 -m pip install -r requirements.txt
```

Or set **`E2E_PYTHON=<path-to-venv-python>`** to a venv that already contains `uvicorn`, SQLAlchemy, etc. Symptom when wrong: webServer stderr shows **`No module named uvicorn`** (**Pitfall 11**).

### Seed token and CI semantics

Typical environment for a serious full run:

```bash
export CI=1
export E2E_PYTHON=/usr/bin/python3
export E2E_DEV_SEED_TOKEN=<same-value-as-backend>
```

The backend must have **`E2E_DEV_SEED_ENABLED=true`** and matching **`E2E_DEV_SEED_TOKEN`** (Playwright `globalSetup` and `tests/e2e/web-admin/fixtures.cjs` call `POST /api/e2e/dev/reset-scenario` with header **`X-E2E-Seed-Token`**).

If the token is missing or mismatched, many tests **skip** or **`resetE2eScenario` throws** — do not assume the SPA regressed.

---

## System shape: why failures chain

### Single-process backend + file SQLite

`playwright.config.cjs` sets `DATABASE_URL` to a **SQLite file** keyed by `E2E_API_PORT` (see config). Within **one** `npm run test:e2e` process:

- The database file **accumulates rows** across specs unless something deletes it.
- `POST /api/e2e/dev/reset-scenario` inserts **new** users/classes/courses every `beforeEach` in many specs.

If any uniqueness constraint collides (historically **`students.parent_code`** — see **Pitfall 52**), **`reset-scenario` returns 500**. Downstream tests then see bad `scenario.json`, wrong logins, empty tables — failures look unrelated.

### High-frequency `resetE2eScenario()`

When **`reset-scenario` fails once**, subsequent tests may operate on **stale `scenario.json`** or half-written DB state. Debugging strategy:

1. Stop asserting UI until **`POST /api/e2e/dev/reset-scenario` returns 200** consistently.
2. Read backend logs for **`IntegrityError`**, **`UNIQUE constraint`**.

---

## Pitfall catalog A–E (full-suite amplifiers)

### A — `students.parent_code` uniqueness vs seed entropy

**Symptom (backend):**

```text
sqlite3.IntegrityError: UNIQUE constraint failed: students.parent_code
```

**Symptom (Playwright):** `E2E seed failed (500)`, timeouts, “cannot find row”, blank shell.

**Concept:** `Student.parent_code` is **nullable unique**. If seed derives `parent_code` from too small a space (e.g. only 6 hex chars), repeated resets against a **persistent** SQLite file behave like a birthday paradox.

**Why single-file runs may pass:** fresh `<E2E_SQLITE>` or fewer resets.

**Fix (source-level):** ensure seed uses **high-entropy** codes (full suffix / UUID-derived), never aggressive truncation. **Pitfall 52** documents the repository fix path.

**Mitigation (environment-only):** delete `<E2E_SQLITE>` or point `DATABASE_URL` at a new path — useful to **confirm** collision hypothesis, not a substitute for code fixes.

### B — Element Plus selector ambiguity (“所属班级”, duplicate labels)

**Symptom:** wrong dropdown, no click effect, wrong API payload.

**Principle:** anchor **`getByRole('dialog', { name: /.../ })`** first, then scope `.el-form-item` / `.el-select`. Avoid page-wide `filter({ hasText: '所属班级' })` when the same literal appears in **table headers** and **dialogs**.

### C — Mobile sidebar geometry vs real CSS

`boundingBox()` width assertions can fail if `el-aside` keeps **min-width** or translation hides visually without collapsing layout width. Prefer **explicit CSS classes** for collapsed state over fragile inline-style substring selectors.

### D — `boundingBox()` over too many nodes

`locator('article.course-card')` may match **many** nodes (cached routes, hidden lists). Iterating all `nth(i)` → **timeout**.

**Pattern:** `locator(...).filter({ visible: true })`, cap **N** iterations (sampling), assert structural intent not exhaustive enumeration.

### E — Strict mode / overly broad `getByText(/LLM/)`

Multiple “LLM” strings on one page → strict violations. Anchor `.quota-card` or add **`data-testid`** in product when extending tests.

---

## Flaky in full-suite context

Do not immediately blame “browser randomness” when:

- Seed failed upstream (**reset 500**).
- Overlays/MessageBox from prior step still mounted.
- Data missing because **earlier spec** aborted DB seed.

**Triage order:**

1. Last successful **`reset-scenario`** / **`scenario.json`** freshness.
2. API status codes / backend traceback.
3. Locator scope / waits.
4. Only then suspect nondeterministic UI.

---

## Artifacts to collect on failure

- `<ADMIN_PKG>/test-results/**/error-context.md`
- `trace.zip` paths printed by Playwright
- Backend stdout: **`IntegrityError`**, SQLAlchemy tracebacks
- Manual `curl` / `fetch` to **`POST /api/e2e/dev/reset-scenario`** with **`X-E2E-Seed-Token`**

---

## Short execution checklist (no calendar estimates)

1. Node/npm present; **`npm ci`** in `<ADMIN_PKG>`.
2. **`npx playwright install chromium`**.
3. **`pip install -r requirements.txt`** on **`E2E_PYTHON`** interpreter.
4. Export **`CI`**, **`E2E_PYTHON`**, **`E2E_DEV_SEED_TOKEN`** aligned with backend env.
5. If investigating cumulative DB issues: try a **fresh** `<E2E_SQLITE>` path once as a control experiment.
6. On **`IntegrityError`**: fix seed/uniqueness — avoid mass product changes first.
7. Selectors: dialog name → form scope.
8. Geometry: visible + capped scans.
9. Text: narrow matchers / `data-testid`.

---

## Command reference

Full Playwright (admin package):

```bash
cd <REPO_ROOT>/apps/web/admin
CI=1 E2E_PYTHON=/usr/bin/python3 E2E_DEV_SEED_TOKEN=<seed> npm run test:e2e
```

Single spec (debug):

```bash
cd <REPO_ROOT>/apps/web/admin
npx playwright test <spec-filename>.spec.js --project=chromium
```

Full pytest (separate from Playwright; complementary):

```bash
cd <REPO_ROOT>
WAILEARNING_AUTO_PG_TESTS=1 python3 -m pytest tests/
```

See [DEVELOPMENT_AND_TESTING.md](DEVELOPMENT_AND_TESTING.md) for PostgreSQL provision script and zero-skip expectations.
