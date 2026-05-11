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

## New Handoff Topic

- The user wants to add comment-thread link support for multiple content types
  across roles: homework, materials, and notes.
- The link UI should not ask users to paste raw URLs. Instead, it should let
  them choose a target from a visually polished, multi-step selector.
- The linked item should render in the comment area as a compact, attractive
  card/button rather than a bare URL.
- The comment/reply area should expose an explicit entry point for creating or
  attaching such links.
- No code changes were requested yet; the user asked to pause after
  requirements alignment and then leave.

## Open Questions To Resolve Next

1. Which comment surfaces are in scope?
   - homework detail comments
   - materials detail comments
   - notes detail comments
   - one shared comment component across all three

2. Which roles may create links?
   - admins
   - teachers
   - students
   - parents / parent-code viewers

3. What is the link semantics?
   - a reference card that jumps to the target
   - a route-style internal link with richer presentation
   - a pure metadata attachment that is not a navigation target

4. What is the allowed target scope?
   - current course only
   - cross-course
   - only items already visible to the current user

5. What hierarchy should the selector use?
   - type -> course -> specific item
   - type -> term -> course -> item
   - type -> chapter/category -> item
   - another product-specific flow

6. What does the reply-area entry point look like?
   - an inline icon button inside the reply box
   - a dedicated "add link" button beside reply actions
   - a context action on existing comments

7. How many links may a single comment contain?
   - exactly one
   - multiple
   - mixed with ordinary text

8. What editing behavior is required after insertion?
   - delete only
   - replace
   - reselect target
   - repost as another reply

9. What metadata should the compact card show?
   - title only
   - title plus type badge
   - title plus course / chapter / status metadata

10. Is mobile support required in the first pass?
    - yes, with the same selector flow
    - yes, but simplified
    - desktop first, mobile later

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
