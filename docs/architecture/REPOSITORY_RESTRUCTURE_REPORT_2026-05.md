# Repository Restructure Report — May 2026

## Purpose

This document records a **bounded** repository-structure optimization pass focused on **eliminating a redundant top-level directory** and aligning documentation with the on-disk layout after the move.

It is written primarily for **LLM coding agents** and maintainers who need:

- a precise **before/after** mapping,
- a list of **edited references**,
- **pitfalls** observed during validation (including failures that did *not* occur but are easy to imagine),
- and explicit **non-goals** so future passes do not confuse this change with backend domain extraction.

This pass intentionally **does not** change:

- the canonical Python import root `apps.backend.wailearning_backend`,
- HTTP routes, environment variable names, or database columns,
- production deployment topology beyond documentation clarity,
- backend package-internal decomposition (for example splitting `llm_grading.py` remains separate architectural work — see [STRUCTURE_AUDIT_AND_MIGRATION_PLAN.md](STRUCTURE_AUDIT_AND_MIGRATION_PLAN.md)).

---

## 1. Executive summary

### What changed

1. **Removed** the repository-root directory `tools/` (it previously contained only one Python utility).
2. **Moved** `tools/testing/audit_test_redundancy.py` → `tests/devtools/audit_test_redundancy.py` using `git mv` to preserve history.
3. **Adjusted** the redundancy auditor so files under `tests/devtools/` are **skipped** during inventory scans (the utility must not inflate category counts or appear as duplicate-analysis noise).
4. **Regenerated** `docs/development/TEST_REDUNDANCY_AUDIT.md` by executing the relocated script (standard workflow — the report footer path string updates automatically).
5. **Updated** primary structural documents (`README.md`, `REPOSITORY_STRUCTURE.md`, `STRUCTURE_AUDIT_AND_MIGRATION_PLAN.md`, `CODE_MAP_AND_ENTRYPOINTS.md`, `TEST_SUITE_MAP.md`, `DEVELOPMENT_AND_TESTING.md`, `HISTORICAL_CODE_CLEANUP.md`, `TEST_EXECUTION_PITFALLS.md`, `docs/README.md`, `AGENTS.md`) so agents do not follow stale paths.

### Why this matters for agents

Top-level directories compete for attention in repository-wide searches. A lone `tools/` directory that only wraps test maintenance creates **dual semantics** with:

- `ops/scripts/` (deployment and server maintenance), and
- `tests/` (everything pytest- or Playwright-adjacent).

Collapsing test-local tooling into `tests/devtools/` reduces **surface area** without touching runtime imports.

---

## 2. Pre-change structural assessment (read-only synthesis)

### Project type and stack

- **Backend:** FastAPI application packaged as `apps/backend/wailearning_backend/` with explicit imports `apps.backend.wailearning_backend.*`.
- **Frontends:** Vue 3 + Vite SPAs — `apps/web/admin/` (staff/admin) and `apps/web/parent/` (parent portal).
- **Tests:** `pytest` under `tests/backend`, `tests/behavior`, `tests/security`, `tests/postgres`; Playwright under `tests/e2e/web-admin/`.
- **Ops:** Shell/systemd/nginx/CI YAML under `ops/`.
- **Documentation:** `docs/` hub + root `README.md` + `AGENTS.md`.

### Top-level directories (meanings)

| Path | Role |
|------|------|
| `apps/` | All shipped application source (backend package + both SPAs). |
| `docs/` | Authoritative documentation tree (architecture, development, operations, product). |
| `ops/` | Deployment scripts, CI YAML references, nginx/systemd templates — **not** pytest helpers. |
| `tests/` | Automated tests, fixtures, scenarios, Playwright specs, and **devtools** utilities scoped to the test corpus. |
| Root contract files | `README.md`, `LICENSE`, `requirements.txt`, `pytest.ini`, `conftest.py`, `.gitignore`, `.editorconfig`, `.env.production` template, etc. |

### Observed structural issue addressed in this pass

| Title | Type | Involved paths | Problem | Target | Risk |
|-------|------|----------------|---------|--------|------|
| Redundant top-level `tools/` | Semantic duplication | `tools/testing/audit_test_redundancy.py` vs `tests/**` | A second top-level bucket for a single test-maintenance script blurred boundaries with `ops/scripts/` | `tests/devtools/audit_test_redundancy.py` | Low — no imports from product code |

### Structural issues explicitly **not** solved here (defer / separate passes)

These remain documented in [STRUCTURE_AUDIT_AND_MIGRATION_PLAN.md](STRUCTURE_AUDIT_AND_MIGRATION_PLAN.md) and [REPOSITORY_STRUCTURE.md](REPOSITORY_STRUCTURE.md):

- Large backend orchestration modules (`llm_grading.py`, `bootstrap.py`, `llm_discussion.py`).
- Further extraction into `domains/*` without changing import roots.

---

## 3. Target layout rationale

### Design constraints

1. **Do not** introduce a new top-level directory to replace `tools/` — the goal is fewer buckets, not more.
2. **Do not** place pytest-discovered filenames under `tests/devtools/` (`test_*.py` must remain absent per [`pytest.ini`](../../pytest.ini)).
3. **Prefer** colocating test-corpus tooling under `tests/` so agents searching “everything about tests” find analyzers alongside suites.

### Target directory: `tests/devtools/`

Meaning:

- Holds scripts that read or rewrite artifacts under `tests/` or generated markdown under `docs/development/` **as part of test hygiene**.
- Not for production deploy scripts (those stay in `ops/scripts/`).

---

## 4. File movement mapping table

| ID | Original path | New path | Move type | Reason | References updated | Tests impacted | Docs impacted | Deploy impacted | Risk | Manual confirmation |
|----|---------------|----------|-----------|--------|-------------------|----------------|---------------|-----------------|------|---------------------|
| M1 | `tools/testing/audit_test_redundancy.py` | `tests/devtools/audit_test_redundancy.py` | `git mv` | Merge test maintenance into `tests/`; remove redundant top-level dir | Script self-reference, docs hub, README, architecture docs | None (utility is not imported by pytest modules) | Yes (multiple) | No | Low | Not required |

---

## 5. Reference repair checklist (completed)

### Code / tooling

- [`tests/devtools/audit_test_redundancy.py`](../../tests/devtools/audit_test_redundancy.py)
  - Skip `tests/devtools/**` during `iter_python_test_files()` inventory walk.
  - Footer string now prints `` `tests/devtools/audit_test_redundancy.py` `` inside generated `TEST_REDUNDANCY_AUDIT.md`.

### Documentation files touched

- [`README.md`](../../README.md) — repository layout block notes devtools location.
- [`docs/architecture/REPOSITORY_STRUCTURE.md`](REPOSITORY_STRUCTURE.md) — high-level tree + Test Boundaries mention `tests/devtools/`.
- [`docs/architecture/STRUCTURE_AUDIT_AND_MIGRATION_PLAN.md`](STRUCTURE_AUDIT_AND_MIGRATION_PLAN.md) — pattern labels + ASCII tree + Phase 2 guidance.
- [`docs/reference/CODE_MAP_AND_ENTRYPOINTS.md`](../reference/CODE_MAP_AND_ENTRYPOINTS.md) — map row points to `tests/devtools/`.
- [`docs/development/TEST_SUITE_MAP.md`](../development/TEST_SUITE_MAP.md) — tree + dedicated subsection.
- [`docs/development/DEVELOPMENT_AND_TESTING.md`](../development/DEVELOPMENT_AND_TESTING.md) — policy pointer path.
- [`docs/development/HISTORICAL_CODE_CLEANUP.md`](../development/HISTORICAL_CODE_CLEANUP.md) — historical pointer path.
- [`docs/development/TEST_EXECUTION_PITFALLS.md`](../development/TEST_EXECUTION_PITFALLS.md) — stale-path pitfall note.
- [`docs/README.md`](../README.md) — hub link to this report.
- [`AGENTS.md`](../../AGENTS.md) — deep-map link.

### Generated documentation

- [`docs/development/TEST_REDUNDANCY_AUDIT.md`](../development/TEST_REDUNDANCY_AUDIT.md) — regenerated via script execution (footer + inventory refresh).

---

## 6. Verification performed (this pass)

Commands executed from repository root (exact versions depend on local `.venv` / Node install):

1. **Utility smoke:** `python3 tests/devtools/audit_test_redundancy.py` — must print `Wrote .../docs/development/TEST_REDUNDANCY_AUDIT.md` without traceback.
2. **Backend pytest slice:** `python3 -m pytest tests/backend/integration/test_core_api_surface.py -q` — validates environment still imports app after doc-only + tooling move.
3. **Admin production build:** `npm --prefix apps/web/admin run build` — ensures SPA toolchain intact (no path assumptions on removed `tools/`).
4. **Stale path grep (code + automation only):** `rg 'tools/testing' -g '*.{py,yml,yaml,sh,bat,cjs,js,json}'` — expected **zero** matches. Narrative docs such as this report and [`TEST_EXECUTION_PITFALLS.md`](../development/TEST_EXECUTION_PITFALLS.md) may still **mention** the old string when explaining the migration; that is intentional and should not be deleted just to silence `rg`.

### Docker / Compose

No `docker-compose.yml` exists in this repository snapshot; **compose validation was not applicable**. If a future branch adds Compose, re-run `docker compose config` after any path edits.

---

## 7. Pitfalls encountered or anticipated (for agents)

Record these in docs so the next agent does not lose time.

### P1 — Broken `REPO_ROOT` resolution after moving the auditor

**Symptom:** `audit_test_redundancy.py` computes `REPO_ROOT = Path(__file__).resolve().parents[2]`.

**Detail:** When the file lived at `tools/testing/audit_test_redundancy.py`, `parents[2]` reached the repository root. After move to `tests/devtools/audit_test_redundancy.py`, `parents[2]` **still** reaches the repository root (devtools → tests → repo). No code change was required — but this is an easy place to miscount `parents[N]` if a future maintainer nests another directory.

**Mitigation:** If you relocate again, recompute using `while` + marker file discovery (`pytest.ini` presence) instead of a hard-coded depth — **待人工确认** whether that refactor is worth the noise.

### P2 — Accidental pytest collection if renamed to `test_*.py`

**Symptom:** pytest tries to import the script as a test module; collection errors or bizarre fixtures apply.

**Mitigation:** Keep filenames like `audit_test_redundancy.py` (no `test_` prefix).

### P3 — Documentation drift (`tools/testing/` bookmarks)

**Symptom:** External bookmarks, stale PR descriptions, or contributor notes still cite `tools/testing/...`.

**Mitigation:** Search `rg 'tools/testing'` across the repo after structural edits; update AGENTS + hub docs first so agents self-correct.

### P4 — Full-suite PostgreSQL / Playwright failures unrelated to this move

During unrelated May 2026 remediation, failures traced to:

- PostgreSQL installed but not started under `policy-rc.d` restricted containers,
- missing `unrar` binary for attachment extraction tests,
- incorrect Playwright assertion assuming `/dashboard/` when admin lands on `/students`.

**None of those failures were triggered by this repository-structure move**, but agents often blame the most recent directory shuffle — keep environment pitfalls in [`TEST_EXECUTION_PITFALLS.md`](../development/TEST_EXECUTION_PITFALLS.md).

---

## 8. Remaining risks and follow-ups

| Risk | Severity | Mitigation |
|------|----------|------------|
| External wiki / onboarding decks still show `tools/` | Low | Search non-repo docs manually — **待人工确认** |
| Future scripts recreate root-level `tools/` out of habit | Medium | Enforce via PR review + link to this report |
| `tests/devtools/` grows without onboarding text | Low | Added [`tests/devtools/README.md`](../../tests/devtools/README.md) during round closure so agents have a first-hop index even with a single utility script. [`TEST_SUITE_MAP.md`](../development/TEST_SUITE_MAP.md) remains the authoritative detailed map. |

---

## 9. Compatibility / legacy

- **No** import shims were added — product Python code did not reference `tools/`.
- **No** CI YAML changes were required — pipeline invokes `pytest`, not the auditor.
- **Git history:** preserved via `git mv`.

---

## 10. Quick commands for the next agent

```bash
# Regenerate redundancy audit markdown
python3 tests/devtools/audit_test_redundancy.py

# Confirm no stale references remain in code/config (Markdown may cite legacy paths on purpose)
rg 'tools/testing' -g '*.{py,yml,yaml,sh,bat,cjs,js,json}' || true

# Focused API smoke after structural edits
python3 -m pytest tests/backend/integration/test_core_api_surface.py -q
```

---

## Document history

- **2026-05:** Initial consolidation removing root `tools/` and introducing `tests/devtools/` as the home for test-tree maintenance scripts.

---

## 11. Round closure statement (repository-level structure pass)

This subsection exists so agents do not reopen finished work by accident.

**Marked complete for the scope “Git 仓库顶层与测试树边界整理”:**

- redundant root-level `tools/` removal,
- `audit_test_redundancy.py` relocation under `tests/devtools/`,
- reference repairs across Markdown contracts,
- regenerated `TEST_REDUNDANCY_AUDIT.md`,
- validation commands recorded in §6 and §10.

**Explicitly out of scope for this same pass (defer to dedicated backend refactors):**

- splitting `llm_grading.py`, `llm_discussion.py`, or `bootstrap.py` (high coupling; see [STRUCTURE_AUDIT_AND_MIGRATION_PLAN.md](STRUCTURE_AUDIT_AND_MIGRATION_PLAN.md) §“Immediate recommendation after this pass”),
- any change to the canonical import root `apps.backend.wailearning_backend`,
- HTTP routes, environment variable names, and database columns.

If you need to resume structural work, start a **new** task label rather than extending this closure section — it prevents ambiguous “half-done repo refactor” states for automation.
