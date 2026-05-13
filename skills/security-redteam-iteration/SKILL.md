---
name: security-redteam-iteration
description: Use this when continuing CourseEval iterative red-team hardening rounds: selecting dense security tests, adding backend and Playwright coverage, fixing discovered bugs, updating docs and CSV ledgers, recording pitfalls, running scoped validation, and committing without push.
---

# Security Red-Team Iteration

## Purpose

Run one complete CourseEval hardening iteration: choose high-value risk points,
add dense tests, let tests expose bugs, fix narrowly, update docs and ledgers, run
change-scoped validation, and commit locally.

## When to Use

Use when the user asks to continue a hardening round, add about 10 high-difficulty
security/robustness tests, include E2E, red-team a surface, or follow the
previous "test, fix, docs, ledger, commit without push" workflow.

## Workflow

1. Preflight: read `AGENTS.md`, `docs/README.md`,
   `docs/testing/README.md`, `docs/testing/TEST_SUITE_MAP.md`,
   `docs/testing/TEST_EXECUTION_PITFALLS.md`, and feature-specific docs.
   Capture the starting commit hash for `agent-update-log.csv` and new pitfalls.
2. Select risks from recent failures, current pitfalls/known issues, and
   current code. Prefer boundaries around role vs ownership, parent-code,
   course enrollment, class links, bulk APIs, status re-entry, dashboard
   aggregation, notification state, seed/dev APIs, and UI cache bypass.
3. Design a compact batch, usually 8-12 tests. Use pytest for dense API/data
   invariants and 1-2 Playwright/browser-backed cases when seed/login/localStorage
   or UI state adds value. One test may assert multiple related invariants.
4. Implement tests first. Accept red runs. Classify failures as product bug,
   test-contract bug, or harness/environment issue before editing product code.
5. Fix only confirmed product bugs. Keep the patch bounded to the surfaced
   behavior.
6. Update docs whenever behavior, permissions, API contracts, validation flow,
   or agent workflow changes. Update pitfalls when a repeatable failure mode,
   timeout, tool trap, or harness issue occurs.
7. Append observed runs to `test-execution-runs.csv`, including failed,
   timed-out, blocked, and final passed runs. Add concise summary rows when
   useful. Append `agent-update-log.csv` once per repository-changing round.
8. Run selector-recommended static checks, targeted tests, targeted Playwright,
   and a broad suite when the selector or risk warrants it. Record high-cost
   full targets such as `full.pytest.postgres` honestly when deferred.
9. Before commit, scan changed files for private paths/artifacts, run CSV
   parse smoke, `git diff --check`, and enough validation to support the final
   claim.
10. Commit locally. Do not push unless the user explicitly asks.

## Script Helpers

Scripts live in `skills/security-redteam-iteration/scripts/`. They are helpers,
not replacements for judgment.

Use these from the repository root:

```powershell
python skills/security-redteam-iteration/scripts/suggest_next_ids.py
python skills/security-redteam-iteration/scripts/changed_text_files.py
python skills/security-redteam-iteration/scripts/csv_smoke.py
python skills/security-redteam-iteration/scripts/private_path_scan.py --staged
```

Append CSV rows with:

```powershell
python skills/security-redteam-iteration/scripts/append_run_ledger.py --test-id security.api_regression --result passed --command "<observed command>" --summary "<observed summary>" --notes "<short notes>"
python skills/security-redteam-iteration/scripts/append_agent_update.py --source-commit <hash> --scope "<round scope>" --changed-files "<files>" --code true --tests true --docs true --pitfalls false --validation "<summary>" --notes "<notes>"
python skills/security-redteam-iteration/scripts/append_pitfall.py --heading "<Pitfall: ...>" --category playwright-startup --notes "<short notes>"
```

Run a bundled static validation profile with:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File skills/security-redteam-iteration/scripts/validation_smoke.ps1
```

## Guardrails

- Record only observed command outcomes in run ledgers.
- Do not put real local paths, tokens, browser cache paths, or `.agent-run/`
  artifact paths into committed rows; use placeholders like `<repo>` and
  `<local-port>`.
- New pitfalls use the most recent committed hash at the time they are recorded.
- If a script appends rows, inspect the diff before commit.
- Scripts may classify and format mechanical data, but the agent decides risk
  selection, bug classification, repair scope, validation breadth, and next
  concerns.

## Related Skills

- `skills/permission-audit/SKILL.md`
- `skills/school-playwright-e2e/SKILL.md`
- `skills/validation-selection/SKILL.md`
- `skills/validation-ledger-maintenance/SKILL.md`
- `skills/repository-normalization/SKILL.md`
