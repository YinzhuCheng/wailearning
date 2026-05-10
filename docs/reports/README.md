# Reports

This directory holds dated audit reports, restructure reports, remediation
notes, and historical pass records.

Use this directory when a document records what happened during a specific
maintenance round rather than defining active architecture, development,
operations, or product rules.

## Rules

- Keep active guidance in the topic directory such as `docs/architecture/`,
  `docs/development/`, `docs/operations/`, or `docs/product/`.
- Move completed audit trails and dated pass reports here when they are useful
  history but no longer the primary operating guide.
- After moving a report, update `docs/README.md`, `AGENTS.md`, and any
  task-specific references in the same change.
- Prefer one report file per maintenance round. Large structured run data
  belongs in CSV, JSON, or YAML with a Markdown index.
