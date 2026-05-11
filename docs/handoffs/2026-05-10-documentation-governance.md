# Documentation Governance Handoff

## Status

- No active repository-normalization handoff is open.
- The documentation-governance and safety-hardening phase is closed for the
  current branch.
- Use this file only when a future documentation-governance or
  repository-normalization thread needs an explicit committed handoff.

## Current Branch

- `cursor/repository-normalization`

## Active Problem

- None.

## Completed Baseline

- Repository documentation and governance were normalized around CourseEval
  naming and current package boundaries.
- Agent-facing documentation policy now says repository docs primarily serve
  agent systems and should remain detailed, structured, and non-destructive by
  default.
- Student identity read paths now distinguish read-only profile resolution from
  repair-capable roster/course preparation.
- Validation registry and CSV ledger wiring now reject implicit ledger aliases.
- Admin Playwright validation target metadata now consistently routes through
  `node scripts/playwright-external-runner.cjs`.
- Mature recurring governance workflows are encoded as repo-local skills.

## Durable References

- `AGENTS.md`
- `docs/README.md`
- `docs/development/TEST_EXECUTION_PITFALLS.md`
- `docs/known-issues-and-risks.md`
- `skills/repository-normalization/SKILL.md`
- `skills/validation-selection/SKILL.md`
- `skills/validation-ledger-maintenance/SKILL.md`
- `skills/roster-identity-repair-playbook/SKILL.md`
- `skills/postgres-release-validation/SKILL.md`
- `skills/frontend-backend-contract-audit/SKILL.md`
- `skills/seed-surface-hardening/SKILL.md`

## If Reopened

Record the following before handing off again:

1. Branch and latest commit.
2. Current problem statement.
3. Files already changed.
4. Validation already run, with exact commands and outcomes.
5. Remaining risks or explicitly deferred targets.
6. Pitfalls moved into durable docs.
7. Items the next agent must not revert.
