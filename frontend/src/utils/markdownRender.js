/**
 * Markdown + LaTeX (KaTeX) rendering for course content, homework, notifications.
 * - markdown-it with html:false to block raw HTML injection
 * - markdown-it-katex for $...$, $$...$$, \(...\), \[...\]
 * - DOMPurify on output (KaTeX emits span/svg in some modes; keep allowlist permissive for math)
 */
import DOMPurify from 'dompurify'
import MarkdownIt from 'markdown-it'
import mk from 'markdown-it-katex'
import 'katex/dist/katex.min.css'

const md = new MarkdownIt({
  html: false,
  linkify: true,
  breaks: true
}).use(mk, {
  throwOnError: false,
  errorColor: '#b45309'
})

/**
 * @param {string} source
 * @returns {string} sanitized HTML safe for v-html
 */
export function renderMarkdownToSafeHtml(source) {
  if (source == null || source === '') {
    return ''
  }
  const str = typeof source === 'string' ? source : String(source)
  const raw = md.render(str)
  return DOMPurify.sanitize(raw, {
    ADD_TAGS: ['math', 'annotation', 'semantics', 'mrow', 'mi', 'mo', 'mn', 'msup', 'msub', 'mfrac', 'mtext', 'mspace'],
    ADD_ATTR: ['class', 'style', 'aria-hidden', 'role', 'xmlns', 'encoding', 'href', 'target', 'rel']
  })
}
