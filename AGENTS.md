# AGENTS — LLM coding agent handbook (CourseEval)

This file is the **fast entry** for automated coding agents (Cursor, Codex, Claude Code, cloud agents). Humans may skim it; agents should read it **before** editing code.

The authoritative documentation hub remains [`docs/README.md`](docs/README.md). This handbook tells you **what to open next** and **what not to break**.

---

## 0. Repository governance philosophy

CourseEval treats **code as documentation** and **documentation as governance**.

- **Code as documentation:** implementation is normally the source of truth.
  When documentation conflicts with code, update the documentation to match the
  current implementation unless the task explicitly asks for a product fix.
  If the documentation describes a more coherent intended rule, or records
  planned behavior that has not been implemented yet, update or add code and
  tests instead, and keep the docs explicit about current vs intended behavior.
- **Documentation as governance:** durable repository rules, operational
  workflows, and repeated agent procedures belong in committed documentation.
  When a workflow is common, fragile, or repeatedly rediscovered, prefer an
  executable script or repo-local skill over prose alone.
  Create or update repo-local skills whenever recurring workflows would help
  future agents act consistently; do this as needed during normal development,
  not only during dedicated documentation passes.

---

## 1. Non-negotiable rules

1. **Code is the source of truth.** If docs disagree with code, update docs (unless explicitly tasked to fix product bugs).
2. **Read task-scoped docs before editing.** Gate lists live in [`docs/README.md`](docs/README.md) §5 (“Mandatory reading by task”).
3. **Package boundary:** canonical backend import root is `apps.backend.courseeval_backend`. Do not add alternate top-level packages or rename this casually — see [`docs/architecture/REPOSITORY_STRUCTURE.md`](docs/architecture/REPOSITORY_STRUCTURE.md).
4. **Never weaken `/api/e2e/dev/*` gates** without reading [`docs/development/DEVELOPMENT_AND_TESTING.md`](docs/development/DEVELOPMENT_AND_TESTING.md) E2E sections — production still mounts the router but handlers return **404** unless `expose_e2e_dev_api()` is true (`main.py`).
5. **Frontend hiding ≠ authorization.** Every sensitive mutation must be enforced in FastAPI routers / domain helpers (`domains/courses/access.py`, homework routers, etc.).
6. **Do not revive removed legacy fallbacks.** Student identity resolves through `users.student_id`; course/class access resolves through `CourseEnrollment` and `subject_class_links`. Do not reintroduce `wailearning_backend`, `Subject.class_id` access fallbacks, or username/student-number guessing as normal feature behavior.
7. **UTF-8 safety:** editing multilingual strings from Windows PowerShell requires [`docs/development/ENCODING_AND_MOJIBAKE_SAFETY.md`](docs/development/ENCODING_AND_MOJIBAKE_SAFETY.md).
8. **Local agent workspace:** `.agent-run/` is the ignored, local-only workspace for private absolute paths, temporary orchestrators, logs, screenshots, and validation planning notes. Read task-relevant local files when continuing work on this machine, especially `.agent-run/local-private-paths.md` if present. Keep handoff-worthy repository context in committed docs when the task needs it, and keep machine-local notes private under `.agent-run/`. Never commit `.agent-run/` contents. Older local notes may still say `.e2e-run/`; in this worktree that role has been superseded by `.agent-run/` while `.e2e-run/` remains ignored for compatibility.
9. **Failure triage starts with pitfall search.** Before classifying any command,
   test, Playwright, PostgreSQL, encoding, port, process, selector, or local
   environment failure, search the pitfall memory first: run
   `python ops/scripts/dev/search_pitfalls.py "<error text or symptom>"`, then
   inspect [`docs/development/TEST_EXECUTION_PITFALLS.md`](docs/development/TEST_EXECUTION_PITFALLS.md),
   [`docs/development/testing/pitfall-index.csv`](docs/development/testing/pitfall-index.csv),
   [`docs/architecture/TROUBLESHOOTING.md`](docs/architecture/TROUBLESHOOTING.md),
   and the task-relevant skill. Do not guess, rewrite product code, or label a
   failure as product/test/environment until the existing pitfall memory has
   been checked.

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
   Repository documentation primarily serves agent systems, whose tolerance for
   sustained, detail-heavy reading is generally higher than that of human
   readers. Preserve documentation detail by default, and do not remove existing
   information unless it is genuinely incorrect, obsolete, duplicative in a way
   that causes confusion, or outside the document's intended scope. When keeping
   documentation detailed, keep it highly structured so future agents can scan,
   route, and execute the guidance reliably.
   Any code change that alters behavior, permissions, configuration, API
   contracts, validation flow, or operational workflow must update the
   corresponding committed documentation in the same change set. Do not leave
   changed code with stale docs and plan to "document later" unless the user
   explicitly asks for an isolated throwaway patch.
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
   Prefer converting repeatable pitfalls into executable guardrails in the same
   or a follow-up change: preflight checks, selector/runner rules, lint scripts,
   tests, registry entries, or CI/profile steps. If a pitfall cannot reasonably
   be automated yet, document the manual procedure and name the missing
   automation point so a later agent can code it instead of rediscovering the
   same failure.
   Every newly recorded pitfall must also be indexed in
   `docs/development/testing/pitfall-index.csv` with:
   `pitfall_sequence`, `source_commit_sha`, `document_path`, `heading`,
   `category`, `status`, and `notes`. New pitfall sequences are positive
   integers that increase by one. Historical Markdown-only pitfalls that predate
   the structured index may be represented with `pitfall_sequence=0` and
   `source_commit_sha=Null`; do not rewrite old prose just to assign historical
   numbers. For a new pitfall, use the most recent committed hash at the time
   the pitfall is recorded as `source_commit_sha`.
   Use `python ops/scripts/dev/search_pitfalls.py "<symptom>"` as the default
   fuzzy lookup before deciding whether the event is a new pitfall. Search the
   exact error text, the command/tool name, the affected framework, and likely
   aliases such as `pg`/`postgres`, `e2e`/`playwright`, or `utf8`/`mojibake`.
   If the search finds an existing entry with the same root cause and
   mitigation, add only the observed run/validation evidence. Add a new pitfall
   entry only when the root cause, trigger condition, or mitigation is genuinely
   new.
6a. **Record each conversation round in the update log.** At the end of every
   user-visible work round that changes repository files, append one row to
   `docs/development/testing/agent-update-log.csv`. Use a positive increasing
   `update_sequence` starting at 1, include the most recent committed hash at
   the start of that round as `source_commit_sha`, summarize the request and
   changed files, and mark whether code, tests, docs, pitfalls, and validation
   were touched. This log is a concise CSV index; keep detailed evidence in the
   normal docs, ledgers, and commit message.
7. **Keep private machine details local.** Real user names, absolute home
   paths, browser cache paths, downloaded binary locations, local database
   directories, local credentials/tokens, and machine-specific logs belong only
   in ignored local files under `.agent-run/`. Do not copy those details into
   committed docs, tests, scripts, commit messages, PR text, or ledger rows.
8. **Keep environment dependencies local unless explicitly promoted.** Tools
   copied into the working tree for agent convenience, including local
   PostgreSQL binaries, RAR extractors, Playwright browser caches, virtualenvs,
   npm dependencies, local databases, generated logs, screenshots, and upload
   fixtures, must live under ignored paths such as `.agent-run/`, `.e2e-run/`,
   `.venv/`, `node_modules/`, `uploads/`, or package-local artifact folders.
   Do not commit them unless the task explicitly asks for a tracked,
   cross-machine script/template and the file contains no private paths,
   secrets, machine-generated logs, or binary runtime payloads.
9. **Use the local VPN proxy before declaring network failure.** On this
   workstation, dependency and GitHub traffic may require the local VPN HTTP
   proxy at `http://127.0.0.1:7897`. When `pip`, `npm`, `npx`, Playwright
   browser install, `git fetch`, or similar outbound commands fail with network
   / socket / DNS errors, retry with `HTTP_PROXY`, `HTTPS_PROXY`, and
   `ALL_PROXY` set to that proxy before treating the environment as offline.
   Keep `NO_PROXY=localhost,127.0.0.1,::1` so local backend, Vite, PostgreSQL,
   and Playwright traffic stays on loopback.
10. **Refresh the active committed handoff on request.** When the user says they
   are preparing to hand off, update the task-relevant committed handoff
   document under `docs/handoffs/` with the current problem statement,
   confirmed findings, touched files, remaining plan, validation state,
   branch/worktree context, and explicit warnings for the next agent. Do not
   maintain a second `.agent-run/HANDOFF.md` or another competing private
   handoff note; local `.agent-run/` files may only hold private paths, logs,
   or machine-local artifacts that must not be uploaded. Assume the user may
   close the conversation immediately after that request and another agent
   system may continue from only the committed handoff.
11. **Verify the commit boundary.** Before committing, confirm that ignored local
   notes are not tracked, scan committed changes for private path leaks, and run
   the narrowest useful static checks for the files touched. For validation
   selection, prefer
   [`ops/scripts/dev/select_validation_targets.py`](ops/scripts/dev/select_validation_targets.py)
   as the first pass, then run or explicitly defer the recommended targets based
   on task scope.
12. **Default to change-scoped validation.** Unless the user explicitly requests
   full-suite, release-quality, zero-skip, or another broader validation level,
   verify only the samples, targets, and checks that are directly relevant to
   the changed files and affected behavior. Use the diff selector first, run the
   recommended static and targeted targets, inspect any `needs_review` or
   `not_sufficient` status, and document any deliberately deferred broad/full
   target in the final handoff. Do not use this default to ignore unmatched
   product paths, high-risk behavior, or selector gaps; add a registry rule, run
   a broader target, or explain the unresolved validation state.
13. **Run repository-normalization guardrails for docs/governance work.** When
   touching docs, ops templates, package paths, or historical cleanup, run
   `python ops/scripts/dev/check_repository_normalization.py` before handoff.
   Treat findings outside historical notes and CSV ledgers as active drift that
   needs either a code/doc fix or an explicit risk note.

---

## 3. Deep maps (read these for structural edits)

| Topic | Document |
|-------|----------|
| Directory truth vs local artifacts | [`docs/architecture/REPOSITORY_STRUCTURE.md`](docs/architecture/REPOSITORY_STRUCTURE.md) |
| Bounded repo-tree moves (devtools consolidation) | [`docs/reports/REPOSITORY_RESTRUCTURE_REPORT_2026-05.md`](docs/reports/REPOSITORY_RESTRUCTURE_REPORT_2026-05.md) |
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
| Repo-local skills | [`skills/docs-governance/SKILL.md`](skills/docs-governance/SKILL.md), [`skills/boundary-governance/SKILL.md`](skills/boundary-governance/SKILL.md), [`skills/structure-governance/SKILL.md`](skills/structure-governance/SKILL.md), [`skills/repository-normalization/SKILL.md`](skills/repository-normalization/SKILL.md), [`skills/security-redteam-iteration/SKILL.md`](skills/security-redteam-iteration/SKILL.md), [`skills/validation-selection/SKILL.md`](skills/validation-selection/SKILL.md), [`skills/validation-ledger-maintenance/SKILL.md`](skills/validation-ledger-maintenance/SKILL.md), [`skills/utf8-safe-editing/SKILL.md`](skills/utf8-safe-editing/SKILL.md), [`skills/permission-audit/SKILL.md`](skills/permission-audit/SKILL.md), [`skills/deployment-governance/SKILL.md`](skills/deployment-governance/SKILL.md), [`skills/local-test-triage/SKILL.md`](skills/local-test-triage/SKILL.md), [`skills/admin-playwright-e2e/SKILL.md`](skills/admin-playwright-e2e/SKILL.md), [`skills/data-migration-audit/SKILL.md`](skills/data-migration-audit/SKILL.md), [`skills/api-surface-audit/SKILL.md`](skills/api-surface-audit/SKILL.md), [`skills/roster-identity-repair-playbook/SKILL.md`](skills/roster-identity-repair-playbook/SKILL.md), [`skills/postgres-release-validation/SKILL.md`](skills/postgres-release-validation/SKILL.md), [`skills/frontend-backend-contract-audit/SKILL.md`](skills/frontend-backend-contract-audit/SKILL.md), [`skills/seed-surface-hardening/SKILL.md`](skills/seed-surface-hardening/SKILL.md) |

---

## 4. Repo-local skills

Use these skills as executable process memory for common agent tasks. Update
them when a repeated workflow becomes stable enough to encode.
When a workflow becomes common, fragile, or repeatedly useful, add or revise a
repo-local skill as part of the same governance cycle, preferably backed by a
script when the workflow can be automated.

**Prefer skill-backed workflows by default.** Before planning non-trivial work,
scan this section and use every task-relevant skill instead of relying on
memory or ad hoc reconstruction. Keep the more precise, executable skill or
script as the source of truth; if two skills overlap, use the richer specialized
skill and keep the broader one as an orchestrator or router.

**Keep skills layered, bounded, and de-duplicated.** Repo-local skills are a
hierarchy, not a flat checklist dump:

1. `repository-normalization` is the top-level router for repo-wide governance,
   skill taxonomy, package/path/name drift, and three-line governance.
2. `docs-governance`, `boundary-governance`, and `structure-governance` are
   horizontal governance skills. They should route into specialized skills
   instead of copying detailed domain rules.
3. Specialized skills own their narrow risk domains, such as permissions,
   API surface, frontend/backend contracts, data migration, deployment,
   seed/E2E surfaces, PostgreSQL validation, Playwright, UTF-8 editing, and
   local test triage.
4. Validation skills own target choice, evidence, and ledger updates.

When a task spans layers, call skills from broad to narrow: start with the
top-level or horizontal skill to define scope, then use the specialized skill
for high-risk domain rules, then use validation skills to choose and record
checks. If a simple skill or script duplicates a richer, more executable one,
delete or shrink the simple version; prefer preserving complex, precise,
tested workflows over keeping short but vague checklists. Do not delete a
mature specialized skill merely because a broader governance skill mentions
the same topic.

When a repository-normalization sequence ends, close the loop in committed
docs: record which boundaries are now accepted, which remain active follow-up,
which are explicitly deferred, and what validation evidence supports that
classification. Private notes, `.agent-run/` records, pytest caches, and local
SQLite scratch files are not source layout and must not be committed.

**Top-level and horizontal governance**

| Skill | Use when |
|-------|----------|
| [`skills/repository-normalization/SKILL.md`](skills/repository-normalization/SKILL.md) | Orchestrating repo-wide governance, skill taxonomy, package/path/name drift, and three-line governance routing |
| [`skills/docs-governance/SKILL.md`](skills/docs-governance/SKILL.md) | Refining README, AGENTS.md, docs, testing/development/deployment guidance, links, and repeatable documentation rules |
| [`skills/boundary-governance/SKILL.md`](skills/boundary-governance/SKILL.md) | Clarifying feature, module, permission, data-flow, import, and ownership boundaries without risky broad refactors |
| [`skills/structure-governance/SKILL.md`](skills/structure-governance/SKILL.md) | Organizing directory hierarchy, root files, duplicate semantic folders, structural references, and safe file moves |

**Specialized audit and execution skills**

| Skill | Use when |
|-------|----------|
| [`skills/security-redteam-iteration/SKILL.md`](skills/security-redteam-iteration/SKILL.md) | Continuing iterative security hardening rounds that add dense tests, include E2E, fix discovered bugs, update docs/ledgers/pitfalls, validate, and commit locally |
| [`skills/permission-audit/SKILL.md`](skills/permission-audit/SKILL.md) | Reviewing or changing authorization, role boundaries, course access, parent-code flows, or sensitive API behavior |
| [`skills/api-surface-audit/SKILL.md`](skills/api-surface-audit/SKILL.md) | Changing FastAPI routers, route prefixes, frontend API clients, API docs, or API regression tests |
| [`skills/frontend-backend-contract-audit/SKILL.md`](skills/frontend-backend-contract-audit/SKILL.md) | Reviewing pagination caps, request bounds, route/query contracts, bulk limits, or Vue/FastAPI API-shape drift |
| [`skills/data-migration-audit/SKILL.md`](skills/data-migration-audit/SKILL.md) | Changing SQLAlchemy models, schema repair DDL, student identity audit/repair helpers, or no-Alembic schema documentation |
| [`skills/roster-identity-repair-playbook/SKILL.md`](skills/roster-identity-repair-playbook/SKILL.md) | Auditing or repairing `users.student_id`, roster/user drift, ambiguous legacy matches, class moves, or student-course enrollment repair |
| [`skills/deployment-governance/SKILL.md`](skills/deployment-governance/SKILL.md) | Changing deployment scripts, ops docs, `.env.production`, nginx/systemd templates, or server Git deploy wrappers |
| [`skills/seed-surface-hardening/SKILL.md`](skills/seed-surface-hardening/SKILL.md) | Changing `/api/e2e/dev/*`, `INIT_DEFAULT_DATA`, first-admin bootstrap, seed tokens, public registration, or powerful demo/local surfaces |
| [`skills/admin-playwright-e2e/SKILL.md`](skills/admin-playwright-e2e/SKILL.md) | Running or debugging admin Playwright with the repository's external runner, seeded E2E helpers, and browser-harness guardrails |
| [`skills/postgres-release-validation/SKILL.md`](skills/postgres-release-validation/SKILL.md) | Planning or running PostgreSQL-backed validation for schema-sensitive or release-quality backend confidence |
| [`skills/local-test-triage/SKILL.md`](skills/local-test-triage/SKILL.md) | Diagnosing local pytest, SQLite, Playwright, port, process, dependency, or Windows test-environment hazards |
| [`skills/utf8-safe-editing/SKILL.md`](skills/utf8-safe-editing/SKILL.md) | Editing multilingual or encoding-sensitive files from Windows PowerShell |

**Validation and evidence skills**

| Skill | Use when |
|-------|----------|
| [`skills/validation-selection/SKILL.md`](skills/validation-selection/SKILL.md) | Choosing, running, or documenting change-scoped validation targets and selector output |
| [`skills/validation-ledger-maintenance/SKILL.md`](skills/validation-ledger-maintenance/SKILL.md) | Adding or revising validation targets, wiring `ledger_id`, updating CSV ledger rows, or correcting selector/history drift |

---

## 5. grep keywords (fast navigation)

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

## 6. High-risk modules (touch with a trace plan)

1. **`apps/backend/courseeval_backend/llm_grading.py`** — quotas, retries, attachment extraction, effective-score aggregation, worker orchestration.
2. **`apps/backend/courseeval_backend/domains/courses/access.py`** — enrollment visibility; impacts every role.
3. **`apps/backend/courseeval_backend/bootstrap.py` + `main.py` lifespan** — ordering: `create_all` → `ensure_schema_updates` → roster normalization → optional demo seed → worker start.
4. **`apps/backend/courseeval_backend/api/routers/e2e_dev.py`** — destructive endpoints; dual-gate auth when configured.
5. **`apps/backend/courseeval_backend/api/routers/homework.py`** — permission matrix + serialization redaction for students vs staff.

---

## 7. Diff-based validation workflow

Use the diff selector as the default validation planning entrypoint after every
non-trivial edit. It is advisory, not a replacement for engineering judgment,
but it prevents agents from either running a full suite unnecessarily or
claiming a narrow run when the diff asks for broader evidence.

Basic loop from the repository root:

1. Inspect the current recommendation:
   `python ops/scripts/dev/select_validation_targets.py --worktree`
2. If the output is easier to consume programmatically, rerun with `--json`.
3. Run the recommended `static` and `targeted` targets directly, or use:
   `python ops/scripts/dev/run_validation_profile.py selector-recommended --worktree --max-risk targeted`
4. If the selector reports `needs_review`, decide whether to include the named
   broad / review-required target now. Playwright targets usually require an
   explicit browser-ready environment and may need `--include-review-targets`.
5. If the selector reports `not_sufficient`, do not present targeted validation
   as complete until the full/broad blocker is handled or explicitly deferred
   in the final handoff.

Runner artifacts and structured history live under ignored `.agent-run/`. They
are useful local evidence, but they are not durable project history. Only update
[`docs/development/TEST_EXECUTION_LEDGER.md`](docs/development/TEST_EXECUTION_LEDGER.md)
after reviewing an actual run result; selector planning output alone is not a
ledger entry. Detailed semantics, commands, and limitations are in
[`docs/development/DEVELOPMENT_AND_TESTING.md`](docs/development/DEVELOPMENT_AND_TESTING.md)
under "Diff-based validation workflow".

---

## 8. Verification checklist after edits

1. **Backend:** targeted `pytest` for touched package (from repo root). See [`docs/development/DEVELOPMENT_AND_TESTING.md`](docs/development/DEVELOPMENT_AND_TESTING.md).
2. **LLM paths:** run nearest tests under `tests/backend/llm/` or homework folders; watch for HTTP mocking patterns.
3. **Frontend:** `npm run build` inside affected SPA (`apps/web/admin` or `apps/web/parent`) when changing TS/Vue.
4. **Docs:** update CONFIGURATION_REFERENCE / CORE_BUSINESS_FLOWS / pitfalls when behavior or defaults shift.
5. **Repository normalization:** for docs, ops, package, or naming changes, run
   `python ops/scripts/dev/check_repository_normalization.py` and explain any
   allowed historical hits.

---

## 9. Naming honesty (avoid agent confusion)

- **Product name:** README branding is **CourseEval**; npm package may still show legacy names (`courseeval-admin`) — treat as historical artifact unless migrating build metadata.
- **`Subject` vs “course”:** ORM model `Subject` maps to user-facing “course” in much of the UI and `/api/subjects` routes.
- **Historical names:** `wailearning_backend`, `ddclass`, old deployment service names, and old domain examples are not current implementation names. If you find them outside intentionally historical notes or test ledgers, update the docs/code path rather than expanding compatibility.

---

## 10. Where CI runs tests

Cloud pipeline definitions (Alibaba DevOps style YAML) live under [`ops/ci/`](ops/ci/); `pr-pipeline.yml` uses `python3 -m pytest -q`.

GitHub Actions now has a lightweight entrypoint at [`.github/workflows/lightweight-validation.yml`](.github/workflows/lightweight-validation.yml). It runs selector/tooling checks, emits a diff-based validation recommendation for pull requests, runs quick backend `pytest`, and builds the admin and parent frontends. Treat it as the first cloud gate, not as full production-aligned validation. PostgreSQL-backed pytest, RAR-dependent attachment coverage, and Playwright E2E remain local/manual or future cloud-profile work unless a later workflow explicitly adds those environments.

---

When in doubt, open [`docs/agent-playbook.md`](docs/agent-playbook.md) for step-by-step workflows and [`docs/known-issues-and-risks.md`](docs/known-issues-and-risks.md) for unresolved hazards.
