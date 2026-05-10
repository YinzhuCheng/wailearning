# Documentation Governance Handoff

## Completed

- Continued the repository normalization line on `cursor/repository-normalization`.
- Confirmed that several apparent mojibake hits in `README.md`, `AGENTS.md`,
  and `docs/README.md` are PowerShell display artifacts when viewed through
  `safe-text-workflow.ps1`; they were not rewritten.
- Extended `check_text_encoding.py` with common Windows/CP936 mojibake markers.
- Added `check_repository_normalization.py` to catch active reintroduction of
  retired project/package/service/domain names while allowing historical ledgers.
- Updated architecture/reference docs so old names are no longer described as
  acceptable current ops paths.
- Updated the PostgreSQL UI audit example database from a retired name to
  `courseeval_uiux_audit`.
- Added the repo-local `repository-normalization` skill and linked it from
  `AGENTS.md` and `docs/README.md`.
- Updated the validation selector registry so root-level `ops/scripts/*.ps1`
  changes map to the static encoding/text tooling target.

## Changed Files

- `AGENTS.md`
- `docs/README.md`
- `docs/architecture/MAINTAINER_AGENT_GUIDE.md`
- `docs/reference/CODE_MAP_AND_ENTRYPOINTS.md`
- `docs/development/ENCODING_AND_MOJIBAKE_SAFETY.md`
- `docs/development/TEST_EXECUTION_PITFALLS.md`
- `docs/handoffs/2026-05-10-documentation-governance.md`
- `ops/scripts/dev/check_repository_normalization.py`
- `ops/scripts/dev/check_text_encoding.py`
- `ops/scripts/setup_git_remotes.ps1`
- `tests/TEST_SELECTION_TARGETS.json`
- `skills/repository-normalization/SKILL.md`

## Verification

- `python -m py_compile ops/scripts/dev/check_text_encoding.py ops/scripts/dev/check_repository_normalization.py` - passed.
- `python ops/scripts/dev/check_repository_normalization.py` - passed; `scanned=376 stale=0 missing_required_paths=0`.
- `python ops/scripts/dev/check_text_encoding.py --fail-on-suspicious <changed files>` - passed; `scanned=11 decode_errors=0 suspicious=0`.
- `python ops/scripts/dev/repo_line_health.py` - passed; tracked health text lines reported successfully.
- `python -m json.tool tests/TEST_SELECTION_TARGETS.json` - passed.
- `python ops/scripts/dev/lint_validation_registry.py` - passed.
- `python ops/scripts/dev/select_validation_targets.py --worktree` - passed with `non_full_validation.status=acceptable`; every changed path matched at least one target.
- `python -m py_compile ops/scripts/dev/select_validation_targets.py ops/scripts/dev/run_validation_target.py ops/scripts/dev/run_validation_profile.py ops/scripts/dev/validation_history.py ops/scripts/dev/lint_validation_registry.py tests/backend/manual/test_validation_selector.py` - passed.
- `python ops/scripts/dev/run_validation_target.py static.validation_selector --dry-run` - passed as a dry-run smoke (`result=skipped`, no command executed).
- `python -m unittest tests.backend.manual.test_validation_selector -v` - passed; 36 tests OK.
- `git diff --check` - passed; Git emitted only the existing CRLF warning for `ops/scripts/setup_git_remotes.ps1`.

## Known Failures

- No verification command failed in this batch.
- A future whole-repository suspicious-marker scan with `--fail-on-suspicious`
  is expected to report existing E2E selector/assertion hotspots in:
  - `tests/e2e/web-admin/e2e-scenario-resilience.spec.js`
  - `tests/e2e/web-admin/e2e-llm-hard-scenarios.spec.js`
- These were not fixed in this batch because selector repairs need targeted
  Playwright validation and should not be bundled with documentation governance.

## Risks

- `check_repository_normalization.py` is intentionally conservative. If it
  reports a historical note outside its allowlist, classify the hit before
  deleting text.
- The new mojibake markers may find real old corruption in test files. Treat
  that as a dedicated test-maintenance task, not as proof this docs batch broke
  encoding.
- No backend business logic was changed in this batch.

## Recommended Next Batch

1. Do a dedicated E2E text-selector cleanup for the two known mojibake hotspots,
   with the affected Playwright specs run afterward:
   - `tests/e2e/web-admin/e2e-scenario-resilience.spec.js`
   - `tests/e2e/web-admin/e2e-llm-hard-scenarios.spec.js`
2. Add `check_repository_normalization.py` to the lightweight validation path
   after confirming the current allowlist is not noisy on fresh clones.
3. Continue docs/code alignment for data migration and permission governance in
   a separate, behavior-aware batch. Do not mix that with broad copyediting.
4. Audit whether deployment docs, ops templates, and `CONFIGURATION_REFERENCE`
   still agree on every service name, env var, upload path, and health check.
5. Update this handoff again if any validation command fails or if a planned
   item needs to move into the long-term plan.

## Long-Term Plan

This workstream is multi-round. Future agents should treat the items below as a
planning backlog, not as tasks that must all fit into the next batch.

### Documentation Consistency

- Build a repeatable docs-vs-code audit for README, AGENTS, docs, ops templates,
  tests, and app package metadata.
- Keep `docs/README.md` as the navigation hub and prevent deep governance docs
  from becoming hidden one-off notes.
- Keep old names confined to historical handoffs, append-only ledgers, and
  explicit "do not restore" warnings.
- Periodically run `check_repository_normalization.py` and expand it when new
  retired paths, env vars, or service names are discovered.

### Data Migration Governance

- Document the current no-Alembic upgrade model around `ensure_schema_updates()`
  and its operational limits.
- Add or document preflight checks for:
  - `users.student_id` completeness for active student login accounts;
  - `subject_class_links` coverage for required courses;
  - orphaned roster/user rows;
  - duplicate or conflicting student bindings;
  - upload files under the effective `UPLOADS_DIR`;
  - stored system settings that still carry retired branding.
- Keep migration guidance explicit about what is runtime repair, what is
  one-time operator action, and what remains unverified.

### Permission And Security Governance

- Turn the object-level permission rules into a checklist and, where practical,
  static/searchable checks.
- Keep backend authorization as the source of truth; never let frontend route or
  button hiding stand in for FastAPI/domain permission checks.
- Audit course access, homework submission/review, LLM settings, parent-code
  access, notification visibility, password reset, and file download/upload
  boundaries as separate review slices.
- Record test targets for each permission slice in the validation selector when
  the mapping becomes clear.

### Deployment And Operations Governance

- Keep `ops/systemd/courseeval-backend.service`,
  `ops/nginx/courseeval.example*.conf`, deployment docs, and config docs in
  lockstep.
- Add scripted checks for env examples vs `Settings` fields if a stable env
  example file is introduced.
- Expand upgrade guidance with backup, restore, rollback, log inspection,
  health checks, and post-upgrade smoke tests.
- Clarify production worker leadership and the DB-backed LLM queue limits for
  multi-instance deployments.

### Testing And Validation Governance

- Continue treating CSV files under `docs/development/testing/` as the source
  for structured validation history; Markdown files should remain entry points
  and interpretation layers.
- Add `check_repository_normalization.py` to CI once the local signal is stable.
- Keep improving `tests/TEST_SELECTION_TARGETS.json` so docs, ops scripts,
  skills, backend, frontend, and E2E harness changes all map to useful
  validation targets.
- Record failed or blocked validation with command, symptom, likely cause,
  merge risk, and next action instead of describing it as green.

### Skills And Agent Workflows

- Expand `skills/repository-normalization` only when repeated workflow details
  become too large for AGENTS.md.
- Consider dedicated skills for:
  - UTF-8/mojibake repair;
  - permission audit;
  - data migration audit;
  - deployment upgrade checks;
  - API regression audit;
  - docs/code consistency checks.
- Keep skills command-oriented: inputs, workflow, checks, failure handling, and
  related files should be concrete enough for an agent to execute.

### Documentation Format Governance

- Keep large append-only or structured records in CSV/JSON/YAML.
- Use Markdown for stable entry points, interpretation rules, procedures, and
  tradeoffs.
- Avoid converting complex procedures into oversized tables. Use headings,
  steps, verification, failure handling, and related files instead.
- Every long-lived governance document should state its scope, when to use it,
  commands, success criteria, failure handling, and related files.

## Do Not Revert

- Do not restore `wailearning_backend`, old service names, old domain examples,
  or `dd-class`/`ddclass` as current names.
- Do not reintroduce username/student-number guessing as normal student
  identity behavior.
- Do not reintroduce `Subject.class_id` as the normal course/class access
  fallback.
- Do not flatten the CSV validation ledgers back into giant Markdown tables.

## Useful Commands

```powershell
python ops/scripts/dev/check_repository_normalization.py
python ops/scripts/dev/check_text_encoding.py --fail-on-suspicious AGENTS.md docs/README.md
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ops\scripts\windows\safe-text-workflow.ps1 -Path AGENTS.md -FailOnSuspicious
python ops/scripts/dev/select_validation_targets.py --worktree
```
