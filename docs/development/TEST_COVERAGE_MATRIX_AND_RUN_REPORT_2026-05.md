# Test coverage matrix and full-suite run report — 2026-05

This document satisfies the “coverage matrix + run record” deliverable for the **full testing remediation** round. It is written primarily for LLM agents and maintainers; verbosity is intentional.

---

## Part A — System & test harness summary

| Topic | Fact |
|-------|------|
| Backend framework | FastAPI + SQLAlchemy + Pydantic v2 (`apps/backend/wailearning_backend/`) |
| Primary pytest roots | `tests/backend/`, `tests/behavior/`, `tests/security/`, `tests/backend/e2e_dev/` |
| Default DB under pytest | File-backed SQLite at `<repo-root>/.pytest_tmp/test.sqlite` unless `TEST_DATABASE_URL` overrides (`tests/conftest.py`). |
| Schema bootstrap in tests | `tests/db_reset.reset_test_database_schema()` → imports **`db.models`** then `drop_all`/`create_all`; then `bootstrap.ensure_schema_updates()`. |
| Playwright | Specs in `tests/e2e/web-admin/`; config `apps/web/admin/playwright.config.cjs`; launches uvicorn on `E2E_API_PORT` (8012) + Vite admin UI on `E2E_UI_PORT` (3012) unless `PLAYWRIGHT_USE_EXTERNAL_SERVERS`. |
| CI reference command | `python3 -m pytest -q` (`ops/ci/pr-pipeline.yml` sibling files under `ops/ci/`). |

---

## Part B — Coverage matrix (selected scenarios)

| Scenario | Prior coverage | Added this round | Tests | Strength | Residual risk |
|----------|----------------|------------------|-------|-----------|---------------|
| Health + root JSON | Partial / indirect | Yes | `tests/backend/integration/test_core_api_surface.py` | Medium | Bing proxy routes not covered |
| JWT missing / invalid login | Partial | Yes | same file | Strong | Refresh-token flows not in scope |
| `/api/auth/me` envelope | Weak | Yes | same file | Strong | Avatar upload edge cases |
| Users list unauthenticated | Weak | Yes | same file | Medium | Pagination semantics elsewhere |
| Homework object-level 403 (no enrollment) | Mixed | Yes | same file | Strong | Cross-class teacher unions |
| Effective-score API keys on submission | Covered deep in homework suite | Reinforced surface contract | same file | Medium | Appeals / batch flows |
| Teacher vs student rubric redaction | Covered elsewhere | Duplicate high-value guard | same file | Strong | Admin impersonation not tested |
| Demo seed LLM preset validation status | Outdated expectation (`validated` only) | Updated | `tests/backend/e2e_dev/test_demo_llm_seed_and_student_quota_edges.py` | Strong | Live vendor bootstrap differs |
| SQLite metadata registration order | Missing → flaky | Fixed harness | `tests/db_reset.py` | Strong | Shared sqlite corruption still possible |
| E2E login / invalid password | Partial | Yes | `tests/e2e/web-admin/e2e-core-flows-smoke.spec.js` | Strong | MFA not applicable |
| E2E multi-role navigation | Partial | Yes | same file | Medium | Parent SPA separate tree |

---

## Part C — New / materially changed tests

| File | Type | Scenario highlights | Mock / real |
|------|------|----------------------|-------------|
| `tests/db_reset.py` | Harness fix | Forces ORM mapper registration before DDL | Real SQLite engine |
| `tests/backend/integration/test_core_api_surface.py` | API integration ×10 | Auth, homework ACL, rubric redaction, submission metadata keys | Real FastAPI `TestClient`, real DB |
| `tests/backend/e2e_dev/test_demo_llm_seed_and_student_quota_edges.py` | Expectation alignment | Accepts `validated` **or** fallback `pending` preset `gpt-5.4` | Real seed + ORM |
| `tests/e2e/web-admin/e2e-core-flows-smoke.spec.js` | Playwright ×10 | Login failure path, student homework grid w/ title match, materials/notifications routes | Real Chromium + dual servers + seeded HTTP |

---

## Part D — Commands executed (this environment)

| Command | Purpose | Result |
|---------|---------|--------|
| `python3 -m pytest tests/backend/integration/test_core_api_surface.py -q` | Validate new API suite | PASS |
| `python3 -m pytest tests/backend -q` | Backend regression | **263 passed**, **2 skipped** (missing OS `unrar` for archive extraction tests — pre-existing guard) |
| `python3 -m pytest tests/behavior tests/security -q` | Higher-level flows | **158 passed**, **1 skipped** |
| `npm install` + `npx playwright install chromium` (under `apps/web/admin`) | Browser deps | Success |
| `npx playwright test e2e-core-flows-smoke.spec.js` | New E2E suite | **10 passed** |
| `npm run build` (`apps/web/admin`) | SPA compile check | Success |

---

## Part E — Fixes applied

| Issue | Category | Fix |
|-------|----------|-----|
| `no such table: course_llm_configs` during pytest reset | Test harness / ordering | Import `db.models` inside `reset_test_database_schema()` |
| `test_demo_seed_binds_llm...` expected always `validated` | Outdated test vs bootstrap without API key | Allow `pending` + assert preset name `gpt-5.4` |
| Admin Playwright expected `/dashboard` but router sends `/students` | Test bug vs real UX | Assert authenticated layout instead of fixed path |

---

## Part F — Remaining gaps (not addressed this round)

| Gap | Reason deferred |
|-----|-----------------|
| Full Playwright repo-wide suite (`npm run test:e2e` all files) | Runtime budget >30min; targeted new tier + build gate executed |
| Postgres-only suites (`tests/postgres`) | No dockerized Postgres started in this session |
| Vitest/Jest unit tests | Admin package declares none beyond Playwright |
| Removal of `unrar` skips | Requires OS package approval in CI image |

---

## Part G — Skip / xfail / focus ethics audit

| Item | Status |
|------|--------|
| New `pytest.mark.skip` | **None added** |
| New `pytest.mark.xfail` | **None added** |
| `test.only` / `describe.only` | **None** |
| Pre-existing skips | `tests/backend/llm/test_llm_attachment_formats.py` — requires `unrar` binary (2 tests) |

---

## Part H — Agent maintenance notes

1. Always prefer `python3 -m pytest` on Linux CI images.
2. When debugging sqlite chaos, delete `.pytest_tmp/test.sqlite` **after** confirming no concurrent pytest.
3. Playwright specs that need seeded IDs **must** call `resetE2eScenario()` — cache lives at `tests/e2e/web-admin/.cache/scenario.json`.
