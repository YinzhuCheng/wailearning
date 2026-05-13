# Pitfall Index

## Purpose

This document is the stable explainer for
[`pitfall-index.csv`](pitfall-index.csv).

Use it when:

- adding a newly recorded pitfall to the structured index;
- checking whether a pitfall already has a durable indexed entry;
- understanding pitfall numbering and source-reference rules.

## What The CSV Stores

`pitfall-index.csv` is the structured companion to
[TEST_EXECUTION_PITFALLS.md](TEST_EXECUTION_PITFALLS.md).

Each row records:

- `pitfall_sequence`
- `source_commit_sha`
- `document_path`
- `heading`
- `category`
- `status`
- `notes`

The Markdown encyclopedia holds the explanatory body; this CSV provides a
searchable structured index for agents and tooling.

## When To Update It

Update the CSV in the same change set whenever a genuinely new pitfall is added
to the Markdown encyclopedia.

Do not add rows for duplicate root causes that are already indexed.

## Sequence Rules

1. New pitfalls use increasing positive `pitfall_sequence` values.
2. Historical Markdown-only pitfalls may stay at `0` with
   `source_commit_sha=Null`.
3. `source_commit_sha` for a new pitfall is the most recent committed hash at
   the time the pitfall is recorded.
4. `document_path` should point at the canonical pitfall body document.

## Related Scripts

- `ops/scripts/dev/search_pitfalls.py`
- `skills/security-redteam-iteration/scripts/append_pitfall.py`
- `skills/security-redteam-iteration/scripts/suggest_next_ids.py`

## Common Failure Modes

- duplicate numbering from helpers that misread BOM-prefixed headers
- indexing a pitfall in the wrong canonical document
- creating a second index row for the same root cause
- stale notes that no longer reflect the current mitigation

## Related Files

- [pitfall-index.csv](pitfall-index.csv)
- [TEST_EXECUTION_PITFALLS.md](TEST_EXECUTION_PITFALLS.md)
- [pitfalls-ledger-and-selector-tooling.md](pitfalls-ledger-and-selector-tooling.md)
