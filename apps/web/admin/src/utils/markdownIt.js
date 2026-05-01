import MarkdownIt from 'markdown-it'

/** Shared Markdown-it preset for course content and feedback (no raw HTML). */
export function createCourseMarkdownIt() {
  return new MarkdownIt({
    html: false,
    linkify: true,
    breaks: true
  })
}
