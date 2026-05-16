---
name: parallel-validation-orchestration
description: Use this when CourseEval validation should run in parallel with automatic slot refill, explicit process supervision, persistent progress files, per-block concurrency, and shard-specific PostgreSQL isolation instead of manual batch launching.
---

# Parallel Validation Orchestration

## Purpose

Run large CourseEval validation workloads with:

- automatic slot refill instead of manual batch replacement
- explicit long-lived supervisor processes
- stable progress files that future rounds can read
- per-block and per-shard concurrency settings
- isolated PostgreSQL workers for dialect-sensitive shards

This skill exists to replace manual “launch a batch, wait, manually top up”
testing loops with durable process orchestration.

## Canonical Process Names / Prefixes

Use the prefix **`WAI-VALID-`** for every durable process, state file, and log
surface so the operator can rediscover them without relying on memory.

These names must remain explicit in every future revision of the workflow:

- `WAI-VALID-supervisor`
- `WAI-VALID-worker`
- `WAI-VALID-pg-worker`
- `WAI-VALID-watchdog`

On Windows the actual executable name may still be `python.exe` or
`powershell.exe`, but the **script filenames, pid files, state files, command
lines, log directories, and progress files** must include the `WAI-VALID-`
prefix.

## Durable Local State

Recommended local-only state root:

- `.agent-run/validation-daemon/`

Recommended files:

- `.agent-run/validation-daemon/WAI-VALID-state.json`
- `.agent-run/validation-daemon/WAI-VALID-queue.json`
- `.agent-run/validation-daemon/WAI-VALID-progress.json`
- `.agent-run/validation-daemon/WAI-VALID-current-run.json`
- `.agent-run/validation-daemon/WAI-VALID-supervisor.pid`
- `.agent-run/validation-daemon/WAI-VALID-watchdog.pid`

Recommended log roots:

- `.agent-run/logs/WAI-VALID-backend-*/`
- `.agent-run/logs/WAI-VALID-behavior-*/`
- `.agent-run/logs/WAI-VALID-e2e-*/`

## Workflow

1. Read:
   - `AGENTS.md`
   - `docs/testing/VALIDATION_WORKFLOW_AND_TOOLS.md`
   - `docs/testing/FULL_VALIDATION_ENVIRONMENT_POLICY.md`
   - `docs/testing/FULL_PLAYWRIGHT_E2E_RUNBOOK.md` when browser shards are in scope
2. Classify incoming test examples / paths into blocks:
   - backend SQLite-compatible
   - backend PostgreSQL-sensitive
   - behavior
   - Playwright E2E
3. Choose concurrency **per block**, not globally.
4. Before starting a run, ask the operator to confirm:
   - blocks
   - per-block concurrency
   - whether visible monitoring is desired
5. Start one **`WAI-VALID-supervisor`** process for the current run.
6. The supervisor:
   - loads the task queue
   - fills up to the configured slot count
   - watches for completed workers
   - immediately refills freed slots from the queue
   - writes progress after every state change
7. If the operator asked for live visibility, open a **foreground progress
   monitor window** that tails the progress file and prints updates.
8. Normal backend/behavior shards use `WAI-VALID-worker`.
9. PostgreSQL-sensitive shards use `WAI-VALID-pg-worker`, one isolated fresh
   cluster / port / data dir per shard.
10. If needed, a lightweight **`WAI-VALID-watchdog`** watches the supervisor and
   restarts it only when the current state files show resumable work.
11. When the queue drains, the supervisor writes a final summary and exits
   cleanly.

## Input / Output Contract

### Input

Accept either:

- explicit test paths/files
- a directory list
- a mixed list of test samples
- a natural-language regression intent such as `light`, `medium`, or `heavy`

The skill must then perform **automatic block splitting** by:

1. identifying the shard family
2. grouping into backend / behavior / Playwright
3. further separating PostgreSQL-sensitive shards from SQLite-compatible shards
4. assigning the requested concurrency per block

### Output

Produce these durable artifacts:

- a block plan file
- a queue file
- a progress file
- a results file
- per-shard logs
- a final summary
- a block report file
- a plain-text block summary file

## Automatic Block Splitting

When the input is a set of test samples or file paths, split them
automatically using these rules:

1. **backend** first
2. within backend:
   - `tests/backend/postgres`-like or explicit PostgreSQL-only paths go to the
     PostgreSQL-sensitive lane
   - everything else goes to the SQLite-compatible lane
3. **behavior** second
4. **Playwright E2E** third

If a sample belongs to multiple lanes, prefer the narrowest lane that can be
executed safely and deterministically.

## Per-Block Concurrency Controls

Each block may have a different concurrency value.

Examples:

- backend SQLite-compatible: `4`
- backend PostgreSQL-sensitive: `1` per isolated cluster unless you explicitly
  provision one cluster per worker
- behavior: `5` or `10` depending on machine headroom
- Playwright: `1` unless you have isolated ports and DBs

The supervisor must keep the block-specific concurrency in the progress file so
the operator can see which block is using which budget.

The first tracked runtime now supports block-aware launch specs such as:

```text
--block-spec behavior:5:tests/behavior/test_admin_llm_policy_behavior.py,tests/behavior/test_discussion_api_behavior.py
--block-spec backend-postgres-sensitive:2:tests/postgres/test_postgres_dialect_guards.py,tests/postgres/test_postgres_llm_schema_and_policy.py
```

## Regression Intensity

The orchestration layer should accept a regression intensity label in addition
to the raw shard list.

Recommended vocabulary:

- `light`
  - direct targets only
  - minimum static/governance validation
- `medium`
  - direct targets
  - nearby related blocks
  - historically fragile regressions when relevant
- `heavy`
  - any logic change expands to the related logic surface
  - still not equivalent to full-suite by default

The run config, progress file, and monitor should all expose the chosen
regression intensity explicitly.

The first tracked implementation now expands some domains this way:

- `light`
  - direct targets only
- `medium`
  - direct targets plus a small adjacent regression surface
- `heavy`
  - direct targets plus a wider related logic surface

Current first-pass domain coverage includes:

- `homework`
- `llm`
- `notifications`
- `discussions`
- `roster`

These expansion rules are intentionally conservative and committed in the
runtime so they can be revised through repository history instead of terminal
lore.

Observed first-pass proof:

- `light` on `tests/backend/homework/test_homework_llm_grading.py` stayed at
  1 direct task
- `heavy` on the same input expanded to a 6-task run that also scheduled
  related behavior suites

## Progress Listener

The process pair should include a progress listener that:

1. reads the progress file on an interval
2. prints a concise progress line
3. reports:
   - active block
   - concurrency
   - completed / total
   - running shard count
   - failed shard count
4. never replaces the source of truth in the progress file

This listener is for observability only.

Recommended console format:

```text
[WAI-VALID] behavior 10-way | 10/20 done | running=8 | failed=1 | queue=1
```

### Visible Monitor Window

If the operator wants to watch progress live, the workflow should expose a
foreground monitor window rather than a hidden-only background process.

The visible monitor window should:

- remain open for the duration of the run
- refresh on an interval
- show block name, concurrency, running, completed, failed, and queue counts
- list the currently running shards
- show regression intensity and regression-origin breakdown
- show per-block pass / fail / total and current slot occupancy
- be easy to inspect without switching away from chat

The first tracked monitor layout now aims to read like a live report with:

- a run header
- an overall summary
- a per-block section
- a running-slot section
- a recent-events section

The monitor window is for visibility; the progress file remains the source of
truth.

Recommended implementation files:

- `ops/scripts/dev/wai_valid_supervisor.py`
- `ops/scripts/dev/wai_valid_monitor.py`
- `ops/scripts/windows/start-validation-monitor.bat`
- `ops/scripts/windows/start-validation-supervisor.bat`

Default operator behavior:

- launching `start-validation-supervisor.bat` should start a visible Win10
  console titled `WAI-VALID-supervisor`
- launching `start-validation-monitor.bat` should open a visible Win10 console
  window titled `WAI-VALID-monitor`
- the monitor should discover the current run automatically from
  `WAI-VALID-current-run.json`

## Block Switching Rules

Do not mix blocks without explicit policy.

Recommended sequence:

1. backend SQLite-compatible
2. backend PostgreSQL-sensitive
3. behavior
4. Playwright E2E

Only switch blocks when:

- the current block is clean
- or it is honestly blocked
- or the operator explicitly requests a transition

## Resume Rules

The supervisor should resume from state if:

- the queue file exists
- the progress file exists
- the task list can be reconstructed deterministically

If a run is resumed, the supervisor should preserve:

- already completed shards
- failed shards
- current block
- current concurrency

## Exact Process Naming Convention

Keep these names in the docs and scripts:

- supervisor: `WAI-VALID-supervisor`
- watcher: `WAI-VALID-watchdog`
- generic worker: `WAI-VALID-worker`
- PostgreSQL worker: `WAI-VALID-pg-worker`

Do not rename these casually. They are intentionally the stable discovery
surface for the operator.

The first tracked implementation now lives in:

- `ops/scripts/dev/wai_valid_supervisor.py`
- `ops/scripts/windows/start-validation-supervisor.bat`
- `ops/scripts/dev/wai_valid_monitor.py`
- `ops/scripts/windows/start-validation-monitor.bat`

## Input Contract

The orchestrator should accept:

- a list of test examples, directories, or files
- a block type or auto-classification mode
- a concurrency value per block
- CPU and memory ceilings
- a PostgreSQL isolation toggle
- a resume-from-state toggle

Example conceptual input:

```json
{
  "block": "behavior",
  "targets": [
    "tests/behavior/test_discussion_api_behavior.py",
    "tests/behavior/test_multi_actor_timeline_behavior.py"
  ],
  "concurrency": 8,
  "cpu_target": 75,
  "memory_target": 85,
  "postgres_isolation": true,
  "resume": true
}
```

## Automatic Slot Refill Rule

This is the core rule of the skill:

- **never wait for a whole batch to finish before starting the next shard**
- the supervisor must refill any freed slot as soon as a worker ends and the
  queue still has work

The only exceptions are:

- browser/E2E shards where explicit port / DB isolation is not available
- operator-chosen serial or low-concurrency safety mode

## Block-Specific Rules

### Backend SQLite-compatible

- parallel workers are allowed because `tests/conftest.py` uses per-process
  SQLite files by default
- use high concurrency if machine resource ceilings permit it

### Backend PostgreSQL-sensitive

- never share one `TEST_DATABASE_URL` across concurrent workers
- every `WAI-VALID-pg-worker` gets:
  - a fresh data dir
  - a unique port
  - a fresh test database

### Behavior

- file-level shards are preferred
- automatic refill is allowed
- keep a close eye on CPU because behavior files can be heavy

### Playwright E2E

- parallelism is allowed only with explicit isolation:
  - distinct API ports
  - distinct UI ports
  - distinct DB / SQLite state
  - separate webServer lifecycles
- otherwise run serial or low-concurrency

## Monitoring Rules

The supervisor must write progress often enough that an interrupted human can
ask “what is still running?” and get a real answer from files, not memory.

Minimum fields in the progress file:

- updated timestamp
- total shard count
- queue remaining
- running shards
- completed shard count
- failed shard count
- completed shard list
- failed shard list
- active block name
- configured concurrency
- regression intensity
- running slot metadata
- per-block summary metadata
- regression-origin totals
- block concurrency mapping

## Failure Handling

When a worker fails:

1. record the shard as failed
2. keep the supervisor alive
3. continue refilling remaining slots unless operator policy says “stop on
   first failure”
4. write the failed shard log path into state
5. leave enough information for a later focused rerun

## Resume / Reconnect Aid

Every finished run should leave behind a quick human-readable summary file in
the run directory. Use it on reconnect to answer:

- which blocks completed
- which shards failed
- whether the failures look like product/test regressions or environment /
  bootstrap problems

Preferred artifact pair:

- `block-report.json`
- `block-summary.txt`

## Task Metadata

Every supervised task should be able to carry:

- `block`
- `kind`
- `origin`
  - `primary`
  - `regression`
  - `retry`
- `origin_detail`
  - short label such as `direct-target`, `adjacent-surface`, or
    `failure-rerun`

The monitor should expose these labels so the operator can distinguish direct
tests from expanded regression coverage.

## Guardrails

- Do not use one PostgreSQL database for multiple concurrent pytest workers.
- Do not let Playwright default-port jobs run in parallel without explicit
  isolation.
- Do not rely on transient in-memory state as the only source of truth.
- Do not present batch-level status from stale cache files; rewrite progress on
  every state change.
- Keep process names / prefixes stable so the operator can rediscover them.
- Do not let the listener become the only source of truth; the progress file is
  the source of truth.
- Do not write a single monolithic “all tests” queue when a block-specific queue
  can be reconstructed from inputs.

## When To Request Escalation

Escalation may be required when:

- starting durable detached supervisor or watchdog processes outside the default
  sandbox lifecycle
- creating or running isolated PostgreSQL clusters that need a less restricted
  execution context
- binding ports or running browser/webServer processes in a context where the
  default sandbox kills background children
- opening multiple isolated PostgreSQL worker instances for parallel shards

If escalation is required, request it explicitly and explain that it is for the
`WAI-VALID-*` supervisor / worker system.

## Current Runtime Boundary

The first tracked runtime now supports:

- multi-block runs through repeated `--block-spec`
- per-block concurrency enforcement
- block-aware progress reporting

It does **not** yet fully implement:

- automatic natural-language expansion from `light` / `medium` / `heavy`
  regression modes into additional tasks
- a finished watchdog/resume stack

## Related Files

- `AGENTS.md`
- `docs/testing/VALIDATION_WORKFLOW_AND_TOOLS.md`
- `docs/testing/FULL_VALIDATION_ENVIRONMENT_POLICY.md`
- `docs/testing/FULL_PLAYWRIGHT_E2E_RUNBOOK.md`
- `skills/validation-selection/SKILL.md`
- `skills/postgres-release-validation/SKILL.md`
- `skills/school-playwright-e2e/SKILL.md`
