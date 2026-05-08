import MarkdownIt from 'markdown-it'

const LATEX_DELIMITER_TOKENS = [
  ['\\(', '@@WL_LATEX_INLINE_OPEN@@'],
  ['\\)', '@@WL_LATEX_INLINE_CLOSE@@'],
  ['\\[', '@@WL_LATEX_BLOCK_OPEN@@'],
  ['\\]', '@@WL_LATEX_BLOCK_CLOSE@@']
]

const LATEX_BLOCK_PATTERNS = [
  {
    left: '$$',
    right: '$$',
    pattern: /(^|\n)[ \t]*\$\$[ \t]*\n([\s\S]*?)\n[ \t]*\$\$[ \t]*(?=\n|$)/g
  },
  {
    left: '\\[',
    right: '\\]',
    pattern: /(^|\n)[ \t]*\\\[[ \t]*\n([\s\S]*?)\n[ \t]*\\\][ \t]*(?=\n|$)/g
  }
]

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

function blockMathToken(index, source) {
  let token = ''
  do {
    token = `@@WL_LATEX_BLOCK_MATH_${index}_${Math.random().toString(36).slice(2)}@@`
  } while (source.includes(token))
  return token
}

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
  let prepared = String(raw ?? '').replace(/\r\n?/g, '\n')
  const blockMath = []
  for (const { left, right, pattern } of LATEX_BLOCK_PATTERNS) {
    prepared = prepared.replace(pattern, (match, prefix, body) => {
      const token = blockMathToken(blockMath.length, prepared)
      blockMath.push({ token, left, body, right })
      return `${prefix}${token}`
    })
  }

  for (const [delimiter, token] of LATEX_DELIMITER_TOKENS) {
    prepared = prepared.replaceAll(delimiter, token)
  }

  let html = md.render(prepared)
  for (const [delimiter, token] of LATEX_DELIMITER_TOKENS) {
    html = html.replaceAll(token, delimiter)
  }
  for (const { token, left, body, right } of blockMath) {
    html = html.split(token).join(`${escapeHtml(left)}\n${escapeHtml(body)}\n${escapeHtml(right)}`)
  }
  return html
}
