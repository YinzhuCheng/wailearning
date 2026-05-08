# Validation Infrastructure Review - 2026-05-08

## Purpose

This review captures the second-round reflection after getting the admin
Playwright smoke path running and then converting the immediate pitfalls into
`playwright_preflight.py` checks.

The conclusion: the validation infrastructure is worth keeping and improving,
but its next risk is not missing a single command. Its next risk is ambiguity:
an agent can still confuse an advisory recommendation, a policy skip, an
environment block, and a product pass unless the tooling makes those states
harder to misread.

## Current Shape

The validation system now has four distinct layers:

1. `tests/TEST_SELECTION_TARGETS.json`
   - Machine-readable target registry.
   - Maps changed paths to validation targets, risk levels, coverage tags,
     review reasons, and broad/full escalation rules.
2. `ops/scripts/dev/select_validation_targets.py`
   - Advisory planner.
   - Answers: "Given this diff, what should be run or explicitly reviewed?"
   - Emits `non_full_validation.status` as `acceptable`, `needs_review`, or
     `not_sufficient`.
3. `ops/scripts/dev/run_validation_target.py`
   - Single-target executor.
   - Writes ignored local evidence under `.agent-run/logs/`, appends structured
     local JSONL history, adds pytest JUnit XML when possible, and generates a
     ledger snippet for manual review.
4. Preflight and profile helpers
   - `ops/scripts/dev/playwright_preflight.py` catches Playwright environment
     blockers before browser runs.
   - `ops/scripts/dev/run_validation_profile.py` executes named groups such as
     `static` or `selector-recommended` while honoring risk and review gates.

The committed `docs/development/TEST_EXECUTION_LEDGER.md` remains the durable
human-reviewed record. `.agent-run/validation-history.jsonl` is useful local
evidence, but it is not project history.

## What Is Working

The first-version system already solves real failure modes:

- It prevents the "run nothing because the diff looked small" failure mode by
  giving a concrete first-pass target list.
- It prevents the opposite "run a full suite by reflex" failure mode for small
  docs, frontend utility, or narrow backend changes.
- It separates product failures from environment blockers for several common
  cases: missing executable, missing pytest, unresolved command placeholder,
  Playwright preflight failure, and sandbox `spawn EPERM`.
- It makes local evidence auditable by writing stdout/stderr paths, summaries,
  result classes, changed-path signatures, and generated ledger snippets.
- It now catches the Playwright seed-time dependency class that a shallow
  uvicorn startup check missed: missing backend modules, Python 3.14 dependency
  pin friction, `passlib` + `bcrypt` hash failure, and persistent SQLite state.

These are not theoretical wins. They directly shortened the path from
Playwright `spawn EPERM` and seed `500` to a successful targeted smoke run.

## Main Weaknesses

### 1. "Needs review" can still look too much like success

`select_validation_targets.py` correctly emits `needs_review` when a target is
environment-sensitive or broad enough to require operator judgment. The profile
runner then skips review-required targets unless `--include-review-targets` is
passed.

That default is safe operationally, but it can be misread. A profile run can
exit successfully after only static or non-review targets execute while the
selector still says review is needed. The final handoff must not summarize that
as "validation passed" without naming the deferred review target.

Third-round code/process candidate:

- make profile output and exit policy distinguish `passed_with_deferred_review`
  from plain `passed`;
- print a short explicit list of policy-skipped review targets at the end;
- consider a non-zero exit code when `non_full_validation.status=needs_review`
  and no review-required target was executed, unless a `--defer-review-targets`
  flag is supplied with a reason.

Third-round implementation:

- `ops/scripts/dev/run_validation_profile.py` now returns
  `result=passed_with_deferred_review` when executed targets pass but one or
  more review-required targets were skipped by policy.
- Profile JSON now includes `deferred_targets`, each with `target_id`, `risk`,
  and `reason`.
- The exit code remains `0` for now so the default fast loop is still usable,
  but final handoffs must not summarize this state as an unconditional pass.

### 2. Static target placeholders are not executable enough

`static.encoding_text_tools` contains `<changed-text-files>` as an argv
placeholder. The runner correctly blocks unresolved placeholders rather than
guessing, but that means the target is not fully self-service.

Third-round code/process candidate:

- teach `run_validation_target.py` to expand a small set of safe placeholders,
  starting with `<changed-text-files>`;
- or split encoding checks into a runnable "all changed text files" wrapper
  script and keep the registry argv literal.

Third-round implementation:

- `ops/scripts/dev/run_validation_target.py` now expands
  `<changed-text-files>` from the current worktree changed-path snapshot.
- Deleted files and non-text files are excluded from the expansion.
- `ops/scripts/dev/check_text_encoding.py` now supports `--skip-if-empty`, so
  an empty expansion scans zero files instead of accidentally falling back to
  the full tracked-file set.
- `tests/TEST_SELECTION_TARGETS.json` now uses `--skip-if-empty` for
  `static.encoding_text_tools`.

### 3. Environment profiles are uneven

Playwright now has a meaningful preflight. PostgreSQL-backed pytest, RAR
attachment coverage, browser installation, and package-manager readiness still
rely more on docs and local notes.

Third-round code/process candidate:

- add separate preflight scripts or target-level preflight hooks for:
  `postgres-pytest`, attachment extraction tools, admin frontend Node/npm
  readiness, and Playwright browser cache availability;
- record preflight JSON into target artifacts consistently, not only for
  `category: admin-playwright`.

### 4. Result parsing is strongest for pytest, weaker for Playwright

The runner can add and parse JUnit XML for pytest commands. Playwright target
records still mostly depend on stdout/stderr summaries, even though Playwright
can emit machine-readable reporters.

Third-round code/process candidate:

- add a Playwright reporter profile that writes JSON or JUnit into the artifact
  directory;
- parse test count, failed test titles, project, and retry information into
  `run.json`;
- keep stdout/stderr as raw evidence, but stop making them the only structured
  browser result source.

### 5. The registry is intentionally conservative, but still manual

The registry has good coverage for high-value targets, but it is not a semantic
dependency graph. File moves, new routers, new Vue views, and new tests require
manual updates. If that update is forgotten, the selector may fall back to
broader targets or leave non-product unmatched paths for review.

Third-round code/process candidate:

- add a registry lint that checks target IDs are unique, commands are runnable,
  referenced files exist where expected, ledger IDs match ledger headings when
  present, and Playwright spec filenames exist;
- add a "new test file without registry coverage" check;
- add a "new product source path only covered by broad fallback" warning.

### 6. Committed ledger and local JSONL can drift

The split is correct: local JSONL is raw local evidence; committed Markdown is
reviewed project memory. The cost is drift. A runner pass can exist only in
`.agent-run/`, while the ledger remains stale until a human or agent updates it.

Third-round code/process candidate:

- add a local command that reads the latest run JSON and prints a ready-to-paste
  ledger row with placeholders;
- add a ledger lint that detects malformed target headers, invalid result
  labels, inconsistent pass/run counts, and target IDs missing from the
  registry when they are intended to be selectable.

## Policy Reflection

The repository should keep change-scoped validation as the default. It is the
right tradeoff for day-to-day work: most changes do not justify a full
PostgreSQL run plus full browser suite before every commit.

But change-scoped validation needs hard honesty rules:

- `acceptable` means the selected scope is a reasonable first pass after the
  recommended commands actually run. It does not mean "no tests needed."
- `needs_review` means an explicit decision remains. Running only the cheap
  subset is allowed, but the deferred target must be named.
- `not_sufficient` means targeted evidence is not enough unless the blocker is
  handled or explicitly handed off as unresolved validation.
- `blocked` is not product failure and not product success. It is unresolved
  validation with an environment or orchestration cause.
- `skipped` is not proof. For release-quality claims, required skipped paths
  must be provisioned and exercised at least once.

## Recommended Third-Round Priorities

1. Make `selector-recommended` profile output harder to misread when review
   targets are skipped.
2. Remove the `<changed-text-files>` runner placeholder trap by code, not docs.
3. Add registry lint coverage for command placeholders, missing files, missing
   Playwright specs, and ledger/registry target drift.
4. Add Playwright machine-readable result artifacts.
5. Add non-Playwright environment preflights for PostgreSQL and attachment-tool
   targets.

The first three are small and high-leverage. They directly reduce agent
misreporting. The last two are larger and can follow after the profile and
registry layers are less ambiguous.

## Bottom Line

Yes, it is necessary to write the pitfalls into docs and convert avoidable
pitfalls into scripts. The Playwright repair showed why: documentation alone
would have required the next agent to remember Python 3.14 pins, bcrypt/passlib,
SQLite residue, and sandbox spawning. Preflight made those risks visible before
the browser run.

It is also necessary to reflect on the validation infrastructure itself. The
current tools are useful, but they are first-generation. The next quality bar is
to make the tooling's states impossible to overclaim: advisory, skipped,
blocked, failed, and passed must stay distinct all the way into final handoffs
and ledger rows.
