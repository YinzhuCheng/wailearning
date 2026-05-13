---
name: docs-governance
description: Use when refining CourseEval README, AGENTS.md, docs, testing/contributing/frontend/deployment guidance, documentation links, or repeatable agent workflows so documentation reflects current implementation and repeated pitfalls become governance rules or scripts.
---

# Docs Governance

## Goal

Keep CourseEval documentation executable for future agents. Treat code as the
truth source, but preserve detailed governance where it prevents repeated
mistakes.

## Layer Role

This is a horizontal governance skill. Use it for documentation truth,
entrypoints, links, reports, and pitfall-to-rule work. Do not duplicate detailed
rules from specialized skills; route to them when the document change touches
their domain.

## Workflow

1. Read `AGENTS.md`, `docs/README.md`, and task-scoped docs listed there.
2. Check current implementation before changing a claim:
   - route and API claims: inspect `apps/backend/courseeval_backend/main.py`,
     `api/routers/`, and `api/schemas.py`;
   - config claims: inspect `core/config.py`, Vite config, ops templates;
   - test claims: inspect `tests/`, `pytest.ini`, Playwright config, and
     `tests/TEST_SELECTION_TARGETS.json`.
3. Run the docs guard before and after edits:
   `python ops/scripts/dev/check_docs_governance.py`.
4. Convert repeated manual pitfalls into one of:
   - a committed script under `ops/scripts/dev/`;
   - a repo-local skill under `skills/`;
   - a precise rule in `AGENTS.md`, `docs/README.md`, or the task-specific doc.
5. Keep dated run reports under `docs/reports/`; keep active guidance in
   the topic directory such as `docs/architecture/`, `docs/contributing/`,
   `docs/frontend/`, `docs/governance/`, `docs/operations/`,
   `docs/product/`, or `docs/testing/`.
6. If documentation is moved, update inbound links and hub indexes in the same
   change.
7. Route specialized work instead of copying its rules:
   - multilingual or PowerShell-sensitive edits:
     `skills/utf8-safe-editing/SKILL.md`;
   - deployment scripts, env templates, nginx/systemd:
     `skills/deployment-governance/SKILL.md`;
   - validation evidence and CSV ledgers:
     `skills/validation-ledger-maintenance/SKILL.md`;
   - API route/client docs: `skills/api-surface-audit/SKILL.md`.

## Checks

Use these from the repository root:

```powershell
python ops/scripts/dev/check_docs_governance.py
python ops/scripts/dev/check_repository_normalization.py
python ops/scripts/dev/check_text_encoding.py --fail-on-suspicious <changed-file>
git diff --check
```

## Decision Rules

- Do not shorten governance docs merely because they are detailed; remove only
  obsolete, contradictory, or duplicated instructions.
- Prefer the richer specialized skill or script when this skill and another
  skill cover the same task. Keep this skill as the documentation router.
- Prefer linking to the authoritative active doc over copying large sections.
- Keep private paths, local logs, screenshots, and machine-specific setup under
  ignored `.agent-run/`.
- Root-level raw logs and one-off CI captures should be ignored or archived
  under a dated report location, not left as naked root files.
