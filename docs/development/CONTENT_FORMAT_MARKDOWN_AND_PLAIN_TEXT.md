# Content format: Markdown vs plain text (homework, submissions, materials, notifications, discussions)

## Purpose (for humans and LLM agents)

This repository stores long-form text in several places: homework instructions, student submission bodies, course materials, notifications, and discussion replies. Historically the admin UI assumed **Markdown** for most authoring surfaces, but some users need **plain text** where characters like `#`, `*`, or `_` must appear literally without being interpreted as Markdown.

This document describes the **optional format switch** implemented as `content_format` (or `body_format` for discussions) with allowed values:

- `markdown` (default): render with the same Markdown + KaTeX pipeline as other course content.
- `plain`: render as pre-wrapped text (no Markdown parsing in the browser for that field).

The database stores the flag on the row so API consumers and LLM pipelines can behave consistently.

## Where the flag lives (ORM)

| Table | Column | Applies to |
|-------|--------|------------|
| `homeworks` | `content_format` | Teacher-authored **作业内容** (not rubric/reference_answer in v1) |
| `homework_submissions` | `content_format` | Latest summary text mirrored from the latest attempt |
| `homework_attempts` | `content_format` | Each attempt body |
| `course_materials` | `content_format` | Material description body |
| `notifications` | `content_format` | Teacher/admin-authored notification body (`password_reset_request` remains HTML from the system) |
| `course_discussion_entries` | `body_format` | Each discussion message body (including LLM assistant rows, which remain `markdown`) |

Schema migrations are applied via `ensure_schema_updates()` in `apps/backend/wailearning_backend/bootstrap.py` using `ALTER TABLE ... ADD COLUMN IF NOT EXISTS ... DEFAULT 'markdown'`.

## API contracts (Pydantic)

- `HomeworkBase`, `HomeworkUpdate`, `HomeworkResponse`: `content_format: Literal["markdown","plain"]` (default `markdown`).
- `HomeworkSubmissionCreate`, `HomeworkSubmissionResponse`, `HomeworkAttemptResponse`: `content_format`.
- `HomeworkSubmissionStatusResponse`: includes `content_format` for teacher grid/detail views.
- `CourseDiscussionCreate`, `CourseDiscussionEntryResponse`: `body_format`.
- `NotificationBase` / `NotificationUpdate` / `NotificationResponse`: `content_format`.
- `CourseMaterialBase` / `CourseMaterialUpdate` / `CourseMaterialResponse`: `content_format`.

Normalization helper: `apps/backend/wailearning_backend/domains/text_content_format.py` (`normalize_content_format`).

## LLM grading behavior (critical)

Auto-grading expands Markdown images for homework instructions and student bodies. If the homework `content_format` is `plain`, the instruction text is wrapped for the model using `body_text_for_grading_llm` so Markdown-like punctuation is not mis-parsed as structure.

Similarly, if a **student attempt** uses `content_format="plain"`, the attempt body is fenced before tokenization/truncation so the model receives literal text.

Discussion LLM (`llm_discussion.py`) also wraps plain homework bodies, plain material bodies, plain prior student attempt excerpts, and plain historical discussion lines when building the thread context.

## Admin SPA (Vue)

### Shared components

- `MarkdownEditorPanel.vue`: optional `v-model:contentFormat` + `showFormatToggle`. When `plain` is selected, the Markdown toolbar and live preview are hidden; the textarea remains monospace for editing.
- `PlainOrMarkdownBlock.vue`: read-only display; delegates Markdown mode to `RichMarkdownDisplay` and uses `white-space: pre-wrap` for plain mode.
- `apps/web/admin/src/utils/contentFormat.js`: mirrors backend normalization for client defaults.

### Screens touched

- **Homework submission** (`HomeworkSubmission.vue`): label renamed to **正文**; editor supports Markdown/plain; history timeline uses `PlainOrMarkdownBlock`.
- **Homework authoring** (`Homework.vue`): assignment body editor toggles format; homework detail uses `PlainOrMarkdownBlock` for instructions.
- **Materials** (`Materials.vue`): same pattern for资料说明.
- **Notifications** (`Notifications.vue`): compose + detail (non-password-reset) respect `content_format`.
- **Teacher submissions** (`HomeworkSubmissions.vue`): detail + history expanded bodies use `PlainOrMarkdownBlock`; collapsed preview flattens Markdown to one line for readability.
- **Discussions** (`CourseDiscussionPanel.vue`): radio group **回复格式** before posting; `POST /api/discussions` sends `body_format`.

## Testing

Integration tests live in:

- `tests/backend/content_format/test_content_format_api.py`

They assert round-trip persistence for homework update + student submission, discussion `body_format`, and notification `content_format`.

## Pitfalls encountered while implementing (agent-oriented)

1. **Pydantic model accidentally deleted mid-edit**  
   During a large `schemas.py` edit, `class HomeworkCreate(HomeworkBase): pass` was dropped, leaving only `HomeworkUpdate`. Symptom: `ImportError: cannot import name 'HomeworkCreate'` when importing `apps.backend.wailearning_backend.main` or any router that imports schemas.  
   **Fix:** restore `HomeworkCreate` immediately after `HomeworkBase`. Run `python3 -c "from apps.backend.wailearning_backend.api.schemas import HomeworkCreate"` as a quick gate.

2. **SQLite bootstrap ordering**  
   `ALTER TABLE course_materials ADD COLUMN ...` must exist for databases that already have `course_materials` from earlier releases. The migration list in `bootstrap.py` is append-only; if a new `ALTER` is missing, production SQLite can start but ORM loads may fail when selecting unknown columns depending on SQLAlchemy version and reflection—prefer adding the `ALTER TABLE ... IF NOT EXISTS` alongside the model field.

3. **Frontend duplicate `data-testid` attributes**  
   Vue does not allow two identical attributes on one element. If you add `data-testid` to a wrapper component prop, remove the duplicate from the parent template.

4. **`refresh_submission_summary` must mirror `content_format`**  
   If only attempts store `content_format` but the summary row is refreshed from the latest attempt, the summary column must be updated too or teacher APIs will return stale `markdown` for plain attempts.

5. **Playwright / E2E**  
   This change set does not automatically update every Playwright selector. If a spec asserted raw textarea DOM for homework submission content, it may need to target the inner `.md-panel__input` textarea or use `data-testid="homework-submit-content"` on the panel root.

## Related documentation

- [LLM and Homework Guide](../product/LLM_HOMEWORK_GUIDE.md) — grading pipeline overview
- [Test Suite Map](TEST_SUITE_MAP.md) — where API tests live
- [Encoding And Mojibake Safety](ENCODING_AND_MOJIBAKE_SAFETY.md) — UTF-8 expectations for text fields
