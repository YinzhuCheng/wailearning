# AGENTS — LLM coding agent handbook (BIMSA-CLASS)

This file is the **fast entry** for automated coding agents (Cursor, Codex, Claude Code, cloud agents). Humans may skim it; agents should read it **before** editing code.

The authoritative documentation hub remains [`docs/README.md`](docs/README.md). This handbook tells you **what to open next** and **what not to break**.

---

## 1. Non-negotiable rules

1. **Code is the source of truth.** If docs disagree with code, update docs (unless explicitly tasked to fix product bugs).
2. **Read task-scoped docs before editing.** Gate lists live in [`docs/README.md`](docs/README.md) §5 (“Mandatory reading by task”).
3. **Package boundary:** canonical backend import root is `apps.backend.wailearning_backend`. Do not add alternate top-level packages or rename this casually — see [`docs/architecture/REPOSITORY_STRUCTURE.md`](docs/architecture/REPOSITORY_STRUCTURE.md).
4. **Never weaken `/api/e2e/dev/*` gates** without reading [`docs/development/DEVELOPMENT_AND_TESTING.md`](docs/development/DEVELOPMENT_AND_TESTING.md) E2E sections — production still mounts the router but handlers return **404** unless `expose_e2e_dev_api()` is true (`main.py`).
5. **Frontend hiding ≠ authorization.** Every sensitive mutation must be enforced in FastAPI routers / domain helpers (`domains/courses/access.py`, homework routers, etc.).
6. **UTF-8 safety:** editing multilingual strings from Windows PowerShell requires [`docs/development/ENCODING_AND_MOJIBAKE_SAFETY.md`](docs/development/ENCODING_AND_MOJIBAKE_SAFETY.md).
7. **Local agent workspace:** `.agent-run/` is the ignored, local-only workspace for handoffs, private absolute paths, temporary orchestrators, logs, screenshots, and validation planning notes. Read it when continuing work on this machine, especially `.agent-run/local-private-paths.md` and `.agent-run/validation-automation-upgrade-outline.md` if present. Never commit `.agent-run/` contents. Older local notes may still say `.e2e-run/`; in this worktree that role has been superseded by `.agent-run/` while `.e2e-run/` remains ignored for compatibility.

---

## 2. Operational defaults for autonomous agents

These defaults are part of the repository working contract for LLM coding agents.
Follow them unless the user explicitly gives a conflicting instruction for the
current task.

1. **Read before acting.** At the start of every work round, read this file,
   [`docs/README.md`](docs/README.md), and the task-scoped documents identified
   in [`docs/README.md`](docs/README.md) §5 before editing code, tests, docs,
   scripts, or repository structure. If local continuation files exist under
   `.agent-run/`, read the task-relevant local notes as well.
2. **Execute basic repository operations directly.** For ordinary file reads,
   file writes, code edits, test-target discovery, and Git operations, proceed
   directly with the necessary commands. Do not ask the user to run routine
   commands or confirm routine local inspection. Ask only when an operation is
   destructive, privacy-sensitive, network-/installation-heavy, or otherwise
   outside the task's reasonable execution boundary.
3. **Minimize avoidable command prompts.** Prefer self-contained local commands
   for development, validation, and Git workflow. When a non-basic command is
   required, make the narrowest reasonable choice and explain the purpose only
   when it materially affects the user's risk or time.
4. **Keep documentation agent-grade.** Documentation updates should be detailed
   enough for future LLM agents to act without guessing. Do not shorten docs
   merely because a human might prefer a brief note. The primary consumer of
   repository process docs is an agentic coding system that benefits from
   explicit commands, preconditions, interpretation rules, and failure modes.
5. **Preserve text encoding.** Treat Windows PowerShell rendering as
   display-only until verified. When editing multilingual or encoding-sensitive
   files, follow
   [`docs/development/ENCODING_AND_MOJIBAKE_SAFETY.md`](docs/development/ENCODING_AND_MOJIBAKE_SAFETY.md):
   use UTF-8-safe display/write helpers, patch around ASCII anchors when
   practical, and verify suspicious glyphs by bytes or escaped output rather
   than by terminal appearance. If a CLI-side encoding adjustment is needed to
   prevent corruption, perform it directly instead of asking the user to repair
   the shell.
6. **Record pitfalls in the repository.** When a command fails, times out, is
   blocked by environment setup, exposes a flaky harness assumption, or reveals
   a repeatable trap, document the cause and mitigation in the relevant
   committed documentation using repository-relative paths and placeholders such
   as `<repo>`, `<artifact-dir>`, `<local-port>`, `<local-postgres-bin>`, or
   `<local-browser-cache>`.
7. **Keep private machine details local.** Real user names, absolute home
   paths, browser cache paths, downloaded binary locations, local database
   directories, local credentials/tokens, and machine-specific logs belong only
   in ignored local files under `.agent-run/`. Do not copy those details into
   committed docs, tests, scripts, commit messages, PR text, or ledger rows.
8. **Verify the commit boundary.** Before committing, confirm that ignored local
   notes are not tracked, scan committed changes for private path leaks, and run
   the narrowest useful static checks for the files touched. For validation
   selection, prefer
   [`ops/scripts/dev/select_validation_targets.py`](ops/scripts/dev/select_validation_targets.py)
   as the first pass, then run or explicitly defer the recommended targets based
   on task scope.

---

## 3. Deep maps (read these for structural edits)

| Topic | Document |
|-------|----------|
| Directory truth vs local artifacts | [`docs/architecture/REPOSITORY_STRUCTURE.md`](docs/architecture/REPOSITORY_STRUCTURE.md) |
| Bounded repo-tree moves (devtools consolidation) | [`docs/architecture/REPOSITORY_RESTRUCTURE_REPORT_2026-05.md`](docs/architecture/REPOSITORY_RESTRUCTURE_REPORT_2026-05.md) |
| Layering inside backend package | [`docs/architecture/BACKEND_PACKAGE_STRUCTURE.md`](docs/architecture/BACKEND_PACKAGE_STRUCTURE.md) |
| Endpoints & surface areas | [`docs/architecture/SYSTEM_OVERVIEW.md`](docs/architecture/SYSTEM_OVERVIEW.md) |
| Vertical slices (homework, LLM, notifications) | [`docs/architecture/CORE_BUSINESS_FLOWS.md`](docs/architecture/CORE_BUSINESS_FLOWS.md) |
| Env vars / defaults | [`docs/architecture/CONFIGURATION_REFERENCE.md`](docs/architecture/CONFIGURATION_REFERENCE.md) |
| LLM entities & worker | [`docs/product/LLM_HOMEWORK_GUIDE.md`](docs/product/LLM_HOMEWORK_GUIDE.md) |
| Parent JWT vs parent-code | [`docs/product/PARENT_PORTAL.md`](docs/product/PARENT_PORTAL.md) |
| Tests & Playwright | [`docs/development/DEVELOPMENT_AND_TESTING.md`](docs/development/DEVELOPMENT_AND_TESTING.md), [`docs/development/TEST_EXECUTION_PITFALLS.md`](docs/development/TEST_EXECUTION_PITFALLS.md) |
| File-level entrypoints & routers | [`docs/reference/CODE_MAP_AND_ENTRYPOINTS.md`](docs/reference/CODE_MAP_AND_ENTRYPOINTS.md) |
| Roles & permission helpers | [`docs/reference/PERMISSIONS_AND_SECURITY_BOUNDARIES.md`](docs/reference/PERMISSIONS_AND_SECURITY_BOUNDARIES.md) |
| ORM tables / naming notes | [`docs/reference/DATA_MODEL_ESSENTIALS.md`](docs/reference/DATA_MODEL_ESSENTIALS.md) |
| In-process LLM worker | [`docs/architecture/ASYNC_TASKS_AND_WORKERS.md`](docs/architecture/ASYNC_TASKS_AND_WORKERS.md) |
| Known gaps / risks | [`docs/known-issues-and-risks.md`](docs/known-issues-and-risks.md) |
| Operational playbook | [`docs/agent-playbook.md`](docs/agent-playbook.md) |

---

## 4. grep keywords (fast navigation)

| Intent | Keywords / symbols |
|--------|---------------------|
| Course visibility | `get_accessible_courses_query`, `ensure_course_access_http`, `prepare_student_course_context` |
| Instructor checks | `is_course_instructor`, `subject_teacher_user_ids` |
| Homework serialization | `_serialize_homework`, `_serialize_submission`, `effective_score_note_zh` |
| Grading queue | `HomeworkGradingTask`, `queue_grading_task`, `claim_grading_tasks_batch`, `process_grading_task`, `process_next_grading_task` |
| Worker lifecycle | `start_grading_worker`, `worker_manager`, `_WorkerManager` |
| Quota | `precheck_quota`, `reserve_quota_tokens`, `LLMGlobalQuotaPolicy` |
| Demo seed | `seed_demo_course_bundle`, `INIT_DEFAULT_DATA`, `domains/seed/demo.py` |
| Schema repair | `ensure_schema_updates`, `bootstrap.py` |
| E2E seed | `expose_e2e_dev_api`, `E2E_DEV_SEED_ENABLED`, `/api/e2e/dev/` |

---

## 5. High-risk modules (touch with a trace plan)

1. **`apps/backend/wailearning_backend/llm_grading.py`** — quotas, retries, attachment extraction, effective-score aggregation, worker orchestration.
2. **`apps/backend/wailearning_backend/domains/courses/access.py`** — enrollment visibility; impacts every role.
3. **`apps/backend/wailearning_backend/bootstrap.py` + `main.py` lifespan** — ordering: `create_all` → `ensure_schema_updates` → roster normalization → optional demo seed → worker start.
4. **`apps/backend/wailearning_backend/api/routers/e2e_dev.py`** — destructive endpoints; dual-gate auth when configured.
5. **`apps/backend/wailearning_backend/api/routers/homework.py`** — permission matrix + serialization redaction for students vs staff.

---

## 6. Verification checklist after edits

1. **Backend:** targeted `pytest` for touched package (from repo root). See [`docs/development/DEVELOPMENT_AND_TESTING.md`](docs/development/DEVELOPMENT_AND_TESTING.md).
2. **LLM paths:** run nearest tests under `tests/backend/llm/` or homework folders; watch for HTTP mocking patterns.
3. **Frontend:** `npm run build` inside affected SPA (`apps/web/admin` or `apps/web/parent`) when changing TS/Vue.
4. **Docs:** update CONFIGURATION_REFERENCE / CORE_BUSINESS_FLOWS / pitfalls when behavior or defaults shift.

---

## 7. Naming honesty (avoid agent confusion)

- **Product name:** README branding is **BIMSA-CLASS**; npm package may still show legacy names (`ddclass-frontend`) — treat as historical artifact unless migrating build metadata.
- **`Subject` vs “course”:** ORM model `Subject` maps to user-facing “course” in much of the UI and `/api/subjects` routes.

---

## 8. Where CI runs tests

Cloud pipeline definition (Alibaba DevOps style YAML): [`ops/ci/pr-pipeline.yml`](ops/ci/pr-pipeline.yml) — uses `python3 -m pytest -q`. There is **no** `.github/workflows/` directory in this repository snapshot; do not assume GitHub Actions unless added later.

---

When in doubt, open [`docs/agent-playbook.md`](docs/agent-playbook.md) for step-by-step workflows and [`docs/known-issues-and-risks.md`](docs/known-issues-and-risks.md) for unresolved hazards.
