# Score-Appeal Red-Team Next-Round Handoff (2026-05-18)

## Purpose

Hand off the next red-team preparation after one completed repository round on
branch:

- `cursor/repository-normalization-schema-notifications`

The completed round focused on `score appeals` and closed one local flaw class:
terminal-state drift and conflicting teacher processing on
`score_grade_appeals`.

This handoff is for the next agent to continue attacking the remaining fragile
surfaces, not to reopen the same score-appeal state-machine bug unless a new
adjacent hypothesis appears.

## Required Reading Order

1. `AGENTS.md`
2. `docs/README.md`
3. `docs/governance/repository-governance.md`
4. `skills/security-redteam-iteration/SKILL.md`
5. `skills/security-redteam-parallel-attacks/SKILL.md`
6. `docs/testing/REDTEAM_PARALLEL_ATTACKS.md`
7. `skills/school-playwright-e2e/SKILL.md` if the batch includes browser work
8. Re-read this handoff

## What The Completed Round Proved

The completed repository round added four attack probes plus one concentrated
repair around `score appeals`:

1. finalized score appeals could be rewritten by stale teacher requests;
2. conflicting concurrent terminal writes could both succeed;
3. teacher responses could be stored while leaving the appeal in `pending`;
4. exact terminal replay should remain idempotent.

Concentrated repair outcome:

- resolved/rejected score appeals are now immutable;
- teacher-response plus `pending` is rejected;
- concurrent terminal writes now use conditional update conflict handling;
- exact terminal replay remains idempotent.

Observed focused validation:

- `C:\Users\bloom\wailearning\.venv\Scripts\python.exe -m pytest tests\backend\scores\test_score_composition.py -q`
- result: `10 passed`

No broad behavior, security, or Playwright regression was run for this round.

## How To Prepare The Next Round

Use the new parallel batch contract:

- plan exactly four attack slots;
- require at least one Playwright/browser-backed E2E slot;
- keep the four slots clustered around one or two nearby flaw classes.

Recommended planning helper:

```powershell
python skills/security-redteam-iteration/scripts/plan_parallel_attack_batch.py --surface notifications --surface homework_submissions --surface bootstrap_first_write
```

Treat the script output as a template, not an authoritative final plan.

## Best Next Thin Surfaces

Prefer the next round to target one nearby cluster, not another unrelated tour.

### Recommended cluster A: notifications state convergence

Attack ideas:

1. concurrent create/update/delete on one notification row;
2. read-state races between `mark-all-read`, single-row read, and delete;
3. stale selected-course cache plus browser badge convergence;
4. one E2E attack from `tests/e2e/web-school/e2e-notification-sync-deep-tier.spec.js`

Suggested maintained anchors:

- `tests/behavior/test_notification_sync_api_edge_behavior.py`
- `tests/e2e/web-school/e2e-notification-sync-deep-tier.spec.js`
- `tests/e2e/web-school/e2e-notification-header-sync-tier.spec.js`

### Recommended cluster B: homework submissions first-write / stale-state recovery

Attack ideas:

1. concurrent first submission write storms;
2. teacher review vs student stale resubmit;
3. stale browser-selected course during submit/review navigation;
4. one E2E attack from `tests/e2e/web-school/e2e-scenario-resilience.spec.js`

Suggested maintained anchors:

- `tests/behavior/test_course_roster_homework_edge_behavior.py`
- `tests/e2e/web-school/e2e-scenario-resilience.spec.js`
- `tests/e2e/web-school/e2e-cross-cutting-tier2.spec.js`

## What Not To Do First

- do not reopen the already-fixed score-appeal terminal-state bug unless a new
  adjacent regression is observed;
- do not start with broad `school.e2e.full` or broad Playwright reruns;
- do not treat one attack as one repository round when the active skill still
  defines `4 attacks + 1 concentrated repair`.

## Push / Branch State

At handoff time, the branch contains the completed score-appeal red-team round
and the repository guidance updates for round semantics and parallel attack
planning.

The next agent should inspect the current branch head, read this handoff, build
one four-slot batch, and then continue the next repository round from `attack
1/4`.
