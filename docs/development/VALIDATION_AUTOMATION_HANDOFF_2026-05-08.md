# LaTeX Copy And Rendering Handoff - 2026-05-08

This handoff replaces the previous validation automation handoff content for the
current branch. The active follow-up is the Markdown + LaTeX authoring demo in
the admin frontend.

## Branch And Context

- Worktree: the local checkout for branch `cursor/discussion-avatar-chat-ui-921d`
- Branch: `cursor/discussion-avatar-chat-ui-921d`
- User-provided screenshot is under `.agent-run/images/` in the local worktree
  (`latex渲染坑.png` at investigation time).
- `.agent-run/` is local-only and ignored. Do not commit screenshots or other
  local evidence from that directory.

## User-Visible Problem

The screenshot shows the admin authoring surface for Markdown + LaTeX content.
Two symptoms are visible:

1. The `复制示例源码` button reports:
   `复制失败：请手动展开「查看示例 Markdown 源码」选择文本`
2. The fixed LaTeX demo renders inline math successfully, but multiline block
   formulas are still displayed as source text:
   - `$$ ... $$`
   - `\[ ... \]`

Important observation: KaTeX is not globally broken. The inline examples in the
screenshot are already rendered as math. The failure is specific to multiline
block delimiters after Markdown rendering.

## Relevant Files

- `apps/web/admin/src/components/MarkdownLatexLiveDemo.vue`
  - Owns the fixed demo card, copy button, insert button, and failure message.
- `apps/web/admin/src/utils/markdownLatexDemo.js`
  - Owns the canonical demo source shown in authoring surfaces.
- `apps/web/admin/src/components/RichMarkdownDisplay.vue`
  - Shared Markdown + KaTeX display component.
- `apps/web/admin/src/components/FeedbackRichText.vue`
  - Similar Markdown + KaTeX rendering path for feedback text.
- `apps/web/admin/src/utils/markdownIt.js`
  - Shared Markdown-it setup and delimiter placeholder handling.
- `tests/e2e/web-admin/e2e-course-ui-markdown-reader.spec.js`
  - Existing E2E coverage around the demo, editor preview, and posted discussion
    Markdown/KaTeX rendering.
- `docs/development/CONTENT_FORMAT_MARKDOWN_AND_PLAIN_TEXT.md`
  - Existing product/technical notes for Markdown/plain format and known LaTeX
    delimiter pitfalls.

## Copy Failure Cause

`MarkdownLatexLiveDemo.vue` currently attempts only the modern Clipboard API:

```js
if (typeof navigator !== 'undefined' && navigator.clipboard?.writeText) {
  await navigator.clipboard.writeText(MARKDOWN_LATEX_EXAMPLE_MARKDOWN)
} else {
  throw new Error('no clipboard')
}
```

If `navigator.clipboard.writeText` is unavailable or rejects, the component
immediately shows the manual-copy warning. There is no fallback copy path.

Likely browser-side triggers include:

- the page is not in a secure context (`https` or accepted localhost context);
- browser permission policy blocks clipboard writes;
- the Clipboard API exists but the write is rejected;
- the app is embedded or launched in a context where clipboard is unavailable.

The screenshot alone proves the UI reached the `catch` path. It does not prove
which browser-side condition occurred. For implementation, that distinction is
not critical because the app should still provide a fallback.

## Rendering Failure Cause

`RichMarkdownDisplay.vue` renders Markdown first via `renderCourseMarkdown(...)`,
then calls KaTeX `renderMathInElement(...)` on the generated DOM.

`markdownIt.js` already protects escaped delimiters such as `\(`, `\)`, `\[`,
and `\]` from Markdown-it's backslash escape behavior. That protection explains
why inline `\(...\)` can render.

The remaining bug is multiline block math. The demo source contains blocks like:

```markdown
$$
\sum_{i=1}^{n} i = \frac{n(n+1)}{2}
$$
```

and:

```markdown
\[
\int_0^1 x^2\,dx=\frac{1}{3}
\]
```

Markdown-it runs before KaTeX. With the current `breaks: true` Markdown-it setup,
multiline formulas are converted into normal paragraph content with line breaks
and DOM boundaries. KaTeX auto-render then scans the already-created DOM and
does not reliably match an opening block delimiter with its closing delimiter
across the generated `<br>` / node boundaries. The result is exactly what the
screenshot shows: inline formulas render, but block formulas remain visible as
raw source.

## Initial Fix Plan

1. Add a resilient copy helper for `MarkdownLatexLiveDemo.vue`.
   - Keep `navigator.clipboard.writeText(...)` as the preferred path.
   - If it is unavailable or rejects, fall back to a temporary `textarea`,
     select its contents, and try `document.execCommand('copy')`.
   - Keep the existing manual-copy warning only if both paths fail.
   - Consider factoring the helper into a small local function in the component
     first; no broad abstraction is needed unless another component already has
     duplicate clipboard logic.

2. Fix multiline block math before or during Markdown rendering.
   - Preferred lightweight approach: in `renderCourseMarkdown(...)`, protect
     complete multiline math blocks before calling `md.render(...)`, then
     restore them into the HTML afterward so KaTeX sees continuous delimiters.
   - Cover both `$$...$$` and `\[...\]` block delimiters.
   - Keep the existing delimiter placeholder logic for inline `\(...\)` and
     escaped block delimiters.
   - Avoid enabling raw HTML in Markdown-it.

3. Keep `RichMarkdownDisplay.vue` and `FeedbackRichText.vue` consistent.
   - Both use `createCourseMarkdownIt` / `renderCourseMarkdown`.
   - A fix in `markdownIt.js` should benefit both components without duplicating
     rendering logic.

4. Add focused tests.
   - Unit-level or lightweight frontend utility test if there is an existing
     pattern for `markdownIt.js`; otherwise rely on E2E coverage.
   - Extend `tests/e2e/web-admin/e2e-course-ui-markdown-reader.spec.js` to
     assert that the fixed demo contains rendered `.katex-display` for block
     formulas, not only any `.katex` node.
   - If clipboard is tested, stub clipboard failure and assert fallback behavior,
     but do not require real OS clipboard access in CI.

## Validation To Run After Fix

Start with diff-based selection:

```powershell
python ops\scripts\dev\select_validation_targets.py --worktree
```

Likely useful checks:

```powershell
python -m json.tool tests\TEST_SELECTION_TARGETS.json
npm.cmd run build
```

Run the admin frontend build from:

```text
apps\web\admin
```

If E2E infrastructure is available, run the targeted spec:

```powershell
npm.cmd run test:e2e -- tests/e2e/web-admin/e2e-course-ui-markdown-reader.spec.js
```

If Playwright/browser startup fails because of local sandbox or missing browser
runtime, record that as an environment limitation and at least complete the
frontend build plus code inspection.

## Notes For Next Agent

- Do not switch back to the forgot-password branch. The user explicitly said to
  ignore that branch context.
- Stay in `cursor/discussion-avatar-chat-ui-921d`.
- Be careful when reading Chinese text through PowerShell: console output may
  display valid UTF-8 as mojibake. Do not treat mojibake in shell output as proof
  that tracked files are corrupt.
- The prior lightweight validation workflow work was already committed and
  pushed as `a1b840f Add lightweight validation workflow`. This handoff is for
  the next LaTeX copy/rendering task, not for continuing validation automation.
