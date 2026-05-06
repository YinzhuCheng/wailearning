# Troubleshooting

## Purpose

Symptom-first pointers for **local development**, **tests**, and **deployments**. Each item links deeper detail elsewhere; prefer those documents for full procedures.

---

## Backend will not start

| Symptom | Likely cause | Where to read |
|---------|----------------|---------------|
| `ValidationError` for `SECRET_KEY` or `DATABASE_URL` | Production or `REQUIRE_STRONG_SECRETS=true` with placeholder secrets | [CONFIGURATION_REFERENCE.md](CONFIGURATION_REFERENCE.md) |
| `E2E_DEV_SEED_ENABLED must be false when APP_ENV is production` | Mis-set env in prod template | `core/config.py` validator |
| Import errors for `apps.backend.wailearning_backend` | Running Python from wrong cwd or broken venv | [REPOSITORY_STRUCTURE.md](REPOSITORY_STRUCTURE.md) |

---

## JWT / login failures after change

- Password resets invalidate tokens via `token_version` on user rows — if login succeeds but APIs 401, confirm client storage cleared and user row not stuck mid-migration.
- CORS: if browser shows CORS errors, verify `BACKEND_CORS_ORIGINS` includes the SPA origin and that you did not enable wildcard origins while relying on credentials.

---

## LLM grading stuck or noisy failures

| Symptom | Check |
|---------|-------|
| Tasks stay `queued` | `ENABLE_LLM_GRADING_WORKER`, `LLM_GRADING_WORKER_LEADER` vs process count; worker logs |
| Tasks stuck `processing` | Stale reclaim interval `LLM_GRADING_TASK_STALE_SECONDS`; DB connectivity |
| Quota unexpected | Global policy timezone and per-student overrides — [../product/LLM_HOMEWORK_GUIDE.md](../product/LLM_HOMEWORK_GUIDE.md) |

---

## Playwright E2E unreliable or slow

Most failures are **environment or harness**, not application logic.

| Symptom | Likely cause | Detail |
|---------|----------------|--------|
| Port already in use (`3012`, `8012`, etc.) | Stale `node` / `uvicorn` | [../development/TEST_EXECUTION_PITFALLS.md](../development/TEST_EXECUTION_PITFALLS.md) — port hygiene |
| Seed returns 404 | `E2E_DEV_SEED_ENABLED` false or wrong token | [../development/DEVELOPMENT_AND_TESTING.md](../development/DEVELOPMENT_AND_TESTING.md) |
| Powerful `/api/e2e/dev/*` 401/403 | Dual gate — need admin JWT + seed header | same |
| Element Plus dropdown flaky | Hover-trigger menus, teleported poppers | pitfalls doc — course switcher / dialog patterns |
| Full suite timeout on layout tests | Too many `boundingBox()` calls | pitfalls doc — sampling strategy |

Full runbook: [../development/FULL_PLAYWRIGHT_E2E_RUNBOOK.md](../development/FULL_PLAYWRIGHT_E2E_RUNBOOK.md).

---

## pytest failures only on SQLite or only on PostgreSQL

- Some tests require PostgreSQL (`TEST_DATABASE_URL`) — see [../development/DEVELOPMENT_AND_TESTING.md](../development/DEVELOPMENT_AND_TESTING.md).
- SQLite has different concurrency and timestamp semantics; do not assume parity.

---

## Uploads / attachments 403 or wrong file

- Attachment authorization is centralized in `api/routers/files.py` with `_has_attachment_access` — duplicate filenames may require `attachment_url` query disambiguation (see pitfalls).

---

## nginx / production static assets

- Admin vs parent base paths — [../operations/DEPLOYMENT_AND_OPERATIONS.md](../operations/DEPLOYMENT_AND_OPERATIONS.md).
- After upgrade, run post-deploy checks from `ops/scripts/post_deploy_check.sh` if available in your environment.

---

## Still stuck?

1. Reduce scope: one pytest module or one Playwright file.
2. Confirm env printed by `playwright.config.cjs` / backend settings (non-secret fields only).
3. Search [../development/TEST_EXECUTION_PITFALLS.md](../development/TEST_EXECUTION_PITFALLS.md) for the HTTP status or error string.
