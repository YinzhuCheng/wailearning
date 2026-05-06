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
| `homeworks` | `content_format` | Teacher-authored **作业内容**（评分要点 / 教师私有要点 / 参考答案或思路另见独立列，格式同上均为 Markdown 管线渲染） |
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

- `MarkdownEditorPanel.vue`: optional `v-model:contentFormat` + `showFormatToggle`. When `plain` is selected, the Markdown toolbar, KaTeX usage hint, fixed **LaTeX live demo** (`MarkdownLatexLiveDemo.vue`), and live preview are hidden; the textarea remains monospace for editing. In Markdown mode the toolbar includes **行内公式** / **独立公式** snippets (`\(…\)`, `$$…$$`). Above the textarea, a **non-editable canonical example** (`apps/web/admin/src/utils/markdownLatexDemo.js`) is always rendered via `RichMarkdownDisplay` so authors see correct delimiter behavior before typing; below that, **您的内容预览** mirrors the editable textarea. Props `compact-demo` reduces padding / hides the collapsible raw-markdown panel when multiple Markdown fields stack in one dialog (homework rubric blocks still show the **same rendered** demo).
- `MarkdownLatexLiveDemo.vue`: reusable demo card + copy / insert actions; imported by `MarkdownEditorPanel` and by `CourseDiscussionPanel` whenever `draftFormat === 'markdown'`.
- `PlainOrMarkdownBlock.vue`: read-only display; delegates Markdown mode to `RichMarkdownDisplay` and uses `white-space: pre-wrap` for plain mode.
- `apps/web/admin/src/utils/contentFormat.js`: mirrors backend normalization for client defaults.

### Screens touched

- **Homework submission** (`HomeworkSubmission.vue`): label renamed to **正文**; editor supports Markdown/plain; history timeline uses `PlainOrMarkdownBlock`.
- **Homework authoring** (`Homework.vue`): assignment body editor toggles format; homework detail uses `PlainOrMarkdownBlock` for instructions.
- **Materials** (`Materials.vue` + `MaterialRead.vue`): authoring uses the same Markdown panel; table rows expose **阅读页** linking to `/materials/read/:id` with prev/next navigation while the modal detail dialog keeps quick preview + discussion threading. **Full-page reader (`MaterialRead.vue`) also mounts `CourseDiscussionPanel` below the article** so behavior matches the modal: thread bodies render via `PlainOrMarkdownBlock` (Markdown + KaTeX vs plain); composer shows the same Markdown/LaTeX live demo when reply format is Markdown. Orphan materials (`discussion_requires_context=true`) show the existing warning card instead of the thread composer.
- **Notifications** (`Notifications.vue`): compose + detail (non-password-reset) respect `content_format`.
- **Teacher submissions** (`HomeworkSubmissions.vue` + `HomeworkSubmissionReview.vue`): the **list** still uses `PlainOrMarkdownBlock` in the **历史** dialog for expanded attempt bodies. **「详情」** no longer opens a 720px dialog: it **navigates to** `HomeworkSubmissionReview.vue` at **`/homework/:homeworkId/submissions/:submissionId`** (query params such as `student_id` are preserved for return navigation). The review page uses the same render stack for the latest summary body, embeds a score/comment form, a collapsible per-attempt history timeline, and a **返回提交列表** control. The teacher-only API **`GET /api/homeworks/{homework_id}/submissions/{submission_id}/status`** returns a single `HomeworkSubmissionStatusResponse` row for that page (avoids paging the full class roster). **Pitfall:** older Playwright specs that waited for `getByRole('dialog')` after clicking **详情** must be updated to assert `toHaveURL(/\/homework\/\d+\/submissions\/\d+/)` and target `data-testid="homework-submission-detail-body"` on the **page** (not inside a dialog).
- **Discussions** (`CourseDiscussionPanel.vue`): radio group **回复格式** before posting; choosing **Markdown** reveals the same live KaTeX demo (`MarkdownLatexLiveDemo`) plus copy/insert helpers; `POST /api/discussions` sends `body_format`.

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
   **Material read + discussion:** after embedding `CourseDiscussionPanel` on `/materials/read/:id`, specs can scope assertions to `.material-read-page .discussion-card` (card header text 「讨论区」). Duplicate `data-testid="markdown-latex-demo-render"` remains limited to editor surfaces; the discussion list uses `PlainOrMarkdownBlock` per row without that test id.

6. **Dashboard `total_students` vs elective enrollment**  
   Earlier implementations counted every `Student` in the course class even when `subject_id` targeted an elective with partial `course_enrollments`. Symptoms: the **removed** teacher 「课程仪表盘」page showed “学生总数 = 班级人数” while **学生管理** listed fewer选课学生（演示种子「初等概率论」即如此）。  
   **Mitigated (API):** `GET /api/dashboard/stats?subject_id=…` counts `course_enrollments` rows for that subject. Regression guard: `tests/backend/integration/test_core_api_surface.py::test_dashboard_stats_subject_id_counts_enrollments_not_class_roster`.  
   **UI note (May 2026):** The **`Dashboard.vue` SPA page was deleted**; agents must not expect `/dashboard` metrics cards — bookmark `/dashboard` redirects to **`/students`**. Teacher-facing enrollment parity is asserted in Playwright via **学生管理 · 课程学生名单** header counts (`tests/e2e/web-admin/e2e-course-ui-markdown-reader.spec.js`).

7. **KaTeX delimiter literacy**  
   Authors sometimes paste math wrapped only in `[ ... ]`. `RichMarkdownDisplay` uses KaTeX `renderMathInElement` with `\(…\)`, `$…$`, `$$…$$`, `\[…\]` only—the demo block shipped with `MarkdownEditorPanel` / discussions spells this out and renders a live counter-example.

8. **Course materials reading navigation**  
   Full-page reader lives at `<admin-base>/materials/read/:id` (`MaterialRead.vue`). Prev/next order is **DFS chapter tree × API sort order per chapter** (same sequencing logic as the list endpoint). After `GET /materials/{id}`, the reader **attempts to align `selected_course`** with `material.subject_id` using `fetchTeachingCourses` so deep links work even when `localStorage.selected_course` was cleared (Playwright `login()` clears storage). If the material’s subject is not in the teacher/student course list, the UI still redirects back to `/materials`. The article (`material.title` / body) is bound **before** chapter DFS completes so readers see the heading immediately; DFS failures downgrade to “导航不完整” rather than blocking the article.  
   **Discussion parity:** the reader intentionally includes **`CourseDiscussionPanel`** (same props contract as `Materials.vue` detail dialog: `target-type="material"`, `subject_id`, `class_id`, `discussion_requires_context`, `is-student`). Agents must not assume “reading mode” is article-only; regression tests should assert the discussion card is present on `/materials/read/:id` when the material is course-scoped.

9. **Teacher sidebar: removal of the 「日常教学」 submenu shell**  
   Historically `Layout.vue` wrapped every teacher route under one `el-sub-menu` labeled 「日常教学」, forcing an extra expand click despite there being only one group. The teacher menu is now **flat `el-menu-item` rows** (same paths and labels as before). **`default-openeds` no longer references `teacher-daily`.** Student 「课程学习」 and admin 「学期与配置」 / 「消息与审计」 groupings are unchanged.  
   **Menu active highlight:** `el-menu` `default-active` is driven by `sidebarMenuActivePath`, mapping nested routes (e.g. `/materials/read/123` → `/materials`, `/homework/9/submit` → `/homework`) so the correct rail item stays selected; without this mapping, Element Plus leaves no item highlighted when `route.path` does not exactly equal a menu `index`.

10. **Removal of teacher 「课程仪表盘」 (`Dashboard.vue`) + `/teaching-calendar` extraction**  
   Product decision: delete the aggregated dashboard view as low-value/noisy. **Teaching calendar** (`TeachingCalendar.vue`, titled 「教学日历」 inside the widget) and **class semester grid** (`ClassSemesterCalendar.vue`, titled 「学期日历」) previously lived inside `Dashboard.vue`; they now render from **`TeachingCalendarPage.vue`** at **`/teaching-calendar`**.  
   - **任课教师** sidebar order: … **考勤管理** → **教学日历** → … (`Layout.vue` `teacherMenu`).  
   - **班主任** submenu replaces the old 「课程仪表盘」 child with **教学日历** linking to the same route (`classTeacherMenu`).  
   - **Login / root redirect:** teachers and class teachers default to **`/students`** (see `Login.vue`, empty-path redirect in `router/index.js`). **`/dashboard` → `/students` redirect** preserves stale bookmarks without resurrecting the Vue page.  
   - **Admin visibility:** `/teaching-calendar` is listed in `adminHiddenPaths` like other teacher tools — admins hitting it bounce to **`/students`** (admin home).  
   - **Students:** `/teaching-calendar` is blocked (student redirect list in `router.beforeEach`), same spirit as `/scores`.  
   **Backend:** `dashboard.router` APIs (`/api/dashboard/stats`, rankings, analysis) remain for **排行榜 / 数据分析** pages — only the dedicated SPA aggregate page was removed.

## Related documentation

- [LLM and Homework Guide](../product/LLM_HOMEWORK_GUIDE.md) — grading pipeline overview
- [Test Suite Map](TEST_SUITE_MAP.md) — where API tests live
- [Encoding And Mojibake Safety](ENCODING_AND_MOJIBAKE_SAFETY.md) — UTF-8 expectations for text fields
