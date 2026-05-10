---
name: repository-normalization
description: Use this when aligning CourseEval documentation, scripts, ops templates, and agent guidance with the current implementation without reviving retired package names or legacy fallbacks.
---

# Repository Normalization

## Purpose

Keep CourseEval documentation and governance aligned with the current codebase.
This skill covers code-as-docs checks, docs-as-governance updates, legacy-name
cleanup, and handoff preparation.

## When to Use

Use this before or during changes to README, AGENTS.md, docs, ops templates,
service names, package paths, environment-variable docs, validation ledgers, or
agent workflows.

## Inputs

- Task description and intended changed files.
- Current diff from `git status --short` and `git diff`.
- Related code anchors, tests, scripts, or deployment templates.

## Workflow

1. Read `AGENTS.md`, `docs/README.md`, and the task-scoped docs listed there.
2. Search code and tests before trusting documentation claims.
3. Identify whether old names are historical records or active drift.
4. Update docs in the same change set as any behavior, config, path, or service change.
5. Prefer CSV/JSON/YAML for append-only structured ledgers; keep Markdown as the interpretation layer.
6. For multilingual files on Windows, run the safe text workflow before editing.
7. Add or update executable checks when a rule can be automated.
8. End with a handoff note when the work spans multiple rounds or leaves known risks.

## Commands

```powershell
git status --short --branch
python ops/scripts/dev/select_validation_targets.py --worktree
python ops/scripts/dev/check_repository_normalization.py
python ops/scripts/dev/check_text_encoding.py --fail-on-suspicious <changed-file>
git diff --check
```

For multilingual files:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ops\scripts\windows\safe-text-workflow.ps1 -Path <repo-relative-path>
```

## Checks

- Current names remain `CourseEval`, `apps.backend.courseeval_backend`,
  `courseeval-backend.service`, and `ops/nginx/courseeval.example*.conf`.
- Retired names appear only in historical notes, append-only ledgers, or
  explicit "do not restore" warnings.
- Documentation claims cite current code paths, config, tests, or scripts.
- Validation failures are recorded with command, symptom, likely cause, and next step.

## Failure Handling

If a script reports stale names, classify each hit:

- historical record: preserve and document why it is allowed;
- active drift: update the doc/code/template;
- uncertain behavior: mark as `待验证` or "needs audit" and add a follow-up.

If tests cannot run, record the environment blocker rather than claiming the
change is verified.

## Related Files

- `AGENTS.md`
- `docs/README.md`
- `docs/development/ENCODING_AND_MOJIBAKE_SAFETY.md`
- `docs/development/testing/README.md`
- `docs/operations/DEPLOYMENT_AND_OPERATIONS.md`
- `ops/scripts/dev/check_repository_normalization.py`
- `ops/scripts/dev/check_text_encoding.py`
