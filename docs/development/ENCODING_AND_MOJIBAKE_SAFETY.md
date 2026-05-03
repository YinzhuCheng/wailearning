# Encoding And Mojibake Safety

## Purpose

This document defines the repository policy for editing multilingual files from Windows + PowerShell without introducing mojibake into tracked source.

The audience is primarily LLM coding agents and automation-oriented maintainers. The goal is operational correctness, not brevity.

Read this before:

- editing any file that contains Chinese UI text or comments,
- rewriting long Markdown files from terminal output,
- "cleaning up" text that only looks broken in the console,
- or auditing whether a previous refactor accidentally introduced encoding corruption.

## Core Rule

PowerShell console output is not the source of truth for Unicode text in this repository.

If terminal rendering and repository history disagree, trust the file bytes on disk and the version-controlled diff, not the glyphs shown in the shell window.

## What Can Go Wrong

The repository is frequently edited from Windows environments where:

- UTF-8 file contents may render incorrectly in the terminal,
- copied terminal text may contain mojibake that was never in the source file,
- mixed-language Markdown can be damaged by full-file rewrites,
- and test fixtures may intentionally contain historical strings that should not be "fixed" during unrelated work.

This creates two different classes of problem:

1. display-only mojibake
2. real file-content corruption

Those classes must not be conflated.

## Safe Editing Strategy

Use this workflow for any multilingual or encoding-sensitive file.

1. Prefer structural edits over text rewrites.
2. Anchor edits on ASCII context such as file paths, route names, identifiers, Markdown headings, JSON keys, or `data-testid` values.
3. Use patch-based edits instead of copying text out of terminal output.
4. If a non-ASCII literal truly must change, verify it through a UTF-8-safe editor or another byte-safe path before editing.
5. After the edit, review the git diff for the specific file and confirm that only the intended lines changed.

## Unsafe Practices

Do not do the following:

- copy Chinese text from PowerShell output and paste it back into tracked files,
- rewrite a whole multilingual file just to change one structural line,
- normalize a suspicious string by eye when the terminal may be lying,
- or treat any unreadable glyph sequence as proof that the repository file itself is corrupted.

## Preferred Tactics By File Type

### Python source

- Prefer structural refactors, imports, helpers, and call-site changes without touching human-language literals.
- If only a small non-ASCII literal must change, prefer a minimal patch around that literal.
- If a Unicode escape is clearer and already consistent with the file style, it is acceptable for a narrowly scoped change.

### JavaScript or Vue files

- Anchor changes on identifiers, props, API calls, selectors, and test IDs.
- Avoid terminal-driven rewrites of user-facing copy unless the task is explicitly text-focused.

### Markdown documentation

- Prefer adding new ASCII sections instead of rewriting older mixed-language sections unless the older section is clearly obsolete.
- Preserve historical notes, but translate outdated implementation references into current-branch meaning.

## Current Repository Audit Findings

Date of audit: `2026-05-03`

The current branch contains visible mojibake-like sequences in a small number of tracked files. At the time of this audit, those hotspots were treated as existing repository state that requires dedicated text-repair work, not opportunistic edits during unrelated refactors.

This audit did **not** find new suspicious mojibake sequences in the documentation files that were intentionally edited in this round.

Known hotspots identified during this audit include:

- `tests/e2e/web-admin/e2e-llm-hard-scenarios.spec.js`
- `tests/e2e/web-admin/e2e-scenario-resilience.spec.js`

Interpretation:

- some hotspots may be true file-content corruption from older edits,
- some may be historically checked-in text that still passes runtime use,
- some may only appear suspicious when viewed through PowerShell output.

In the two E2E files above, the suspicious strings currently appear inside selectors and text-matching helpers, which makes casual "cleanup" especially risky.

The important operational rule is the same in all three cases: do not "repair" them casually while doing structural or behavioral work.

## How To Audit For Real Corruption

When you need to decide whether a mojibake-looking string is real file corruption:

1. inspect the file through a UTF-8-safe editor,
2. compare against git history when available,
3. review whether the string is user-facing copy, test data, or a literal that affects selectors or assertions,
4. isolate the repair into a dedicated change set if possible.

Do not combine encoding cleanup with a large refactor unless the encoding issue blocks the refactor itself.

## Rules For Documentation Upgrades

Documentation work in this repository should follow these rules:

- keep the docs detailed enough for an LLM agent to act on them,
- prefer additive clarification over deletion unless the old text is truly obsolete,
- preserve historical lessons and traps,
- but rewrite outdated implementation details so they remain meaningful under the current code layout.

When an older paragraph contains useful operational history but refers to paths or modules that no longer exist, keep the lesson and update the implementation reference.

## Recommended Verification After Editing

For documentation-only changes in encoding-sensitive files:

- review the file diff directly,
- confirm that headings, links, and code fences remain intact,
- confirm that no unrelated multilingual blocks were rewritten,
- and confirm that any new policy text points to the current repository paths.

For code changes in encoding-sensitive files:

- review the diff,
- confirm imports and syntax by inspection,
- and isolate any separate text-repair work from the structural change when possible.
