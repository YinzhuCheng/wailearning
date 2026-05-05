# Historical Code Cleanup

## Purpose

This document defines how to remove historical or redundant code in this repository without breaking still-supported compatibility paths.

The primary audience is an LLM agent or automation-oriented maintainer. The goal is not to keep the document short. The goal is to make cleanup decisions reproducible.

## Repository-Specific Constraint

Do not treat every `legacy`, `old`, `compat`, or duplicate-looking branch as dead code.

In this repository, some legacy-looking paths still serve one of these concrete purposes:

- persisted database rows created before a schema or serialization change
- deployment-time migration from an older on-disk layout
- backward-compatible reads while writes already use the new format
- E2E fixtures or regression tests that intentionally exercise older payload shapes

A path is only safe to remove when you can name the exact compatibility contract that has ended.

## Removal Standard

Before deleting code, satisfy all applicable checks below.

1. Confirm the code is not part of the current import or route graph.
2. Confirm the code is not required only by tests, seed scripts, or deployment scripts.
3. Confirm the code is not the read-side of a write-migrated data format.
4. Confirm the code is not the only bridge for old rows already stored in production-like databases.
5. Confirm the code is not the only bridge for old uploaded files or attachment paths.
6. Confirm the code is not still referenced by documentation that defines the supported operational path.

If any item above is still true, prefer one of these alternatives instead of deletion:

- extract duplicate logic into one shared helper
- narrow a compatibility branch so the supported contract is explicit
- document the removal precondition and leave the branch in place
- delete only obviously unused imports, locals, helpers, or wrappers around still-needed behavior

## What Was Cleaned In This Sweep

Date of sweep: `2026-05-03`

This pass intentionally focused on low-risk historical noise, not broad compatibility removal.

### 1. Repeated discussion `@LLM` prefix stripping was consolidated

A shared helper now owns the logic that removes the UI-only `@LLM` first line before content is sent or interpreted:

- historical location: `apps/backend/wailearning_backend/discussion_llm_ui.py`
- current location: `apps/backend/wailearning_backend/domains/llm/discussion_ui.py`

The following modules previously carried their own duplicate regex + helper:

- `apps/backend/wailearning_backend/llm_discussion.py`
- `apps/backend/wailearning_backend/api/routers/discussions.py`

This is the preferred cleanup pattern when two runtime paths still need the same behavior: deduplicate first, delete only the repeated implementation.

### 2. Unused backend imports were removed

The sweep removed imports that were no longer read by runtime code from these modules:

- `apps/backend/wailearning_backend/bootstrap.py`
- `apps/backend/wailearning_backend/llm_grading.py`
- historical location: `apps/backend/wailearning_backend/llm_group_routing.py`
- historical location: `apps/backend/wailearning_backend/services.py`
- `apps/backend/wailearning_backend/api/routers/homework.py`
- `apps/backend/wailearning_backend/api/routers/logs.py`
- `apps/backend/wailearning_backend/api/routers/semesters.py`
- `apps/backend/wailearning_backend/api/routers/users.py`

Current structure note:

- the old `llm_group_routing.py` logic now lives in `apps/backend/wailearning_backend/domains/llm/routing.py`
- the old `services.py` log helper now lives in `apps/backend/wailearning_backend/services/logging.py`

This class of cleanup is high-signal and low-risk because it reduces false search hits and makes real dependencies easier to inspect.

### 3. Dead scenario module and import indirection removed (`2026-05-05`)

This pass removed **unused** test-support code and narrowed the supported import surface:

- **`tests/scenarios/llm_pressures.py` deleted:** Static analysis (`rg`/import graph) showed **no** test module,
  production module, or script importing this file. Heavy LLM scenarios remain covered by
  `tests/backend/llm/test_llm_stress_scenarios.py`, `test_llm_concurrency_scenarios.py`, and several
  behavior suites. If a future maintainer needs a dedicated pressure helper package again, add it
  alongside at least one pytest-discovered test or an explicit import from an existing test so it
  cannot silently rot.
- **Root compatibility stubs deleted:** `tests/llm_scenario.py`, `tests/material_flow.py`, and
  `tests/llm_pressures.py` were thin star-import re-exports. All in-repo imports were rewritten to
  **`tests.scenarios.llm_scenario`** and **`tests.scenarios.material_flow`** (pattern replace across
  `tests/**/*.py`). External forks that still used the old paths must update on merge.
- **`tools/testing/audit_test_redundancy.py`:** Removed the special-case branch that classified the
  deleted stub filenames; scenario helpers under `tests/scenarios/` already fall under the
  `tests/scenarios/` category rule.

Verification performed in the same change set:

- Full **`python3 -m pytest tests/`** on **SQLite** (default `tests/conftest.py`): **389 passed,
  43 skipped** (PostgreSQL-only modules + `test_r3`).
- Full pytest with **`TEST_DATABASE_URL=postgresql+psycopg2://wailearning_test:wailearning_test@127.0.0.1:5432/wailearning_pytest_all`**
  after `pg_ctlcluster 16 main start` and `bash ops/scripts/dev/provision_postgres_pytest.sh`:
  **432 passed, 0 skipped**.
- **`tests/backend/llm/test_llm_attachment_formats.py`** RAR cases now read committed archives under
  **`tests/fixtures/llm_rar/`** so they exercise **`unrar`** / **`unrar-free`** (production path)
  without requiring the non-free **`rar`** compressor at **test runtime**. Archives were generated once
  using **`rar`** with commands equivalent to the former inline test setup; regeneration belongs in
  maintainer docs (`TEST_SUITE_MAP.md`), not in CI logs.

### 4. Broad compatibility branches were intentionally not removed

Several areas still look historical but were not deleted in this pass because they likely continue to serve existing data or operational compatibility:

- course schedule fallback logic in `api/routers/subjects.py`
- attachment directory fallback logic in `wailearning_backend/attachments.py`
- deployment-time upload migration logic in `ops/scripts/deploy_backend.sh`
- branding normalization and bootstrap migration helpers
- legacy document-format extraction in `domains/llm/attachments.py`

These are valid future cleanup targets only after their remaining data or deployment contracts are explicitly retired.

## PowerShell Encoding Safety Rules

This repository is frequently edited from Windows PowerShell sessions where console rendering can misrepresent UTF-8 text. That rendering issue must not be allowed to write mojibake back into the repo.

The detailed editing policy and current hotspot audit now live in:

- [ENCODING_AND_MOJIBAKE_SAFETY.md](ENCODING_AND_MOJIBAKE_SAFETY.md)

Follow these rules when touching any file that contains non-ASCII text, especially Chinese UI strings, shell comments, or mixed-language documentation.

### Safe editing rules

- Prefer minimal patch edits over full-file rewrites.
- Prefer Unicode escape sequences when only a few literals must change in Python source.
- Avoid copying terminal-rendered mojibake text back into patches.
- If a file already contains non-ASCII text and the terminal display is suspicious, verify with an editor or byte-safe read path before changing the text itself.
- When the task is structural, refactor imports, helpers, signatures, or control flow without rewriting human-language strings.

### Unsafe patterns

- replacing a full file from terminal output when the terminal is showing mojibake
- editing Chinese strings based only on what PowerShell displayed
- normalizing text by hand if you have not verified the original encoding
- converting a small targeted change into a wholesale reformat of a multilingual file

### Recommended strategy for multilingual files

1. Make structural changes first.
2. Leave existing human-language literals untouched unless the task explicitly requires text correction.
3. If text correction is required, verify the source in a UTF-8-safe editor or use escaped literals where appropriate.
4. Re-run a syntax-level validation after the edit so structural fixes are not mixed with encoding regressions.

## Current Mojibake Audit Status

Date of audit: `2026-05-03`

This cleanup sweep included an explicit encoding-safety review because the repository is often edited through Windows + PowerShell.

The practical findings were:

- the repository contains a small number of known mojibake-like hotspots,
- not every suspicious string should be treated as proof of new corruption,
- and structural refactors must not opportunistically rewrite multilingual text unless the text itself is the target of the change.

At the time of this audit, the tracked hotspot list was moved into [ENCODING_AND_MOJIBAKE_SAFETY.md](ENCODING_AND_MOJIBAKE_SAFETY.md) so future agents can update the inventory without mixing it into cleanup-removal decisions.

## Validation Standard After Cleanup

For cleanup-only changes, the minimum bar is:

- repository diff review
- syntax compilation for the touched Python package
- targeted static reasoning about import and call-site reachability

For behavior-affecting cleanup, add:

- targeted tests for the affected module or route
- fixture or migration verification if compatibility code was removed
- deployment-path validation if scripts or storage paths changed

## Recommended Next Targets

These are candidates for later cleanup, but only with stronger verification than this sweep required.

### Candidate: schedule legacy read path

Files:

- `apps/backend/wailearning_backend/api/routers/subjects.py`
- `apps/web/admin/src/components/CourseSchedulePicker.vue`

Why it still exists:

- the backend can still read old `weekly_schedule` + date columns
- the admin UI can still surface non-canonical schedule values

Removal precondition:

- confirm all stored course rows have canonical `course_times` or canonical serialized schedule values
- add or run a migration that rewrites old rows
- remove the warning path only after read-side fallback is unnecessary

### Candidate: attachment directory fallback roots

File:

- `apps/backend/wailearning_backend/attachments.py`

Why it still exists:

- runtime reads still try multiple historical upload roots

Removal precondition:

- define the only supported upload root
- verify production-like assets are fully migrated there
- update deployment docs and scripts in the same change

### Candidate: deploy-time legacy upload copy

File:

- `ops/scripts/deploy_backend.sh`

Why it still exists:

- it preserves uploads from older layouts during deployment

Removal precondition:

- deployment documentation states one canonical layout
- old upload trees are no longer expected on any supported host

## Working Rule For Future Sweeps

When cleanup pressure is high, prefer this order:

1. remove unused imports
2. remove duplicate helpers by extraction
3. remove wrappers with zero unique behavior
4. remove compatibility reads only after data migration is proven complete
5. remove deployment fallbacks only after operations documentation and host layout are proven current

This order keeps cleanup aggressive where it is safe and conservative where the repository still carries live historical contracts.
