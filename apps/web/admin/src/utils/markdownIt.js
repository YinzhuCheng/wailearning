import MarkdownIt from 'markdown-it'

const LATEX_DELIMITER_TOKENS = [
  ['\\(', '@@WL_LATEX_INLINE_OPEN@@'],
  ['\\)', '@@WL_LATEX_INLINE_CLOSE@@'],
  ['\\[', '@@WL_LATEX_BLOCK_OPEN@@'],
  ['\\]', '@@WL_LATEX_BLOCK_CLOSE@@']
]

/** Shared Markdown-it preset for course content and feedback (no raw HTML). */
export function createCourseMarkdownIt() {
  return new MarkdownIt({
    html: false,
    linkify: true,
    breaks: true
  })
}

/**
 * Preserve KaTeX delimiters that Markdown-it would otherwise treat as markdown escapes.
 *
 * Without this, author input like `\\(x\\)` or `\\[x\\]` is rendered as plain `(x)` / `[x]`
 * before KaTeX auto-render runs, so preview and published discussion bodies cannot detect math.
 */
export function renderCourseMarkdown(md, raw) {
  let prepared = String(raw ?? '')
  for (const [delimiter, token] of LATEX_DELIMITER_TOKENS) {
    prepared = prepared.replaceAll(delimiter, token)
  }

  let html = md.render(prepared)
  for (const [delimiter, token] of LATEX_DELIMITER_TOKENS) {
    html = html.replaceAll(token, delimiter)
  }
  return html
}
