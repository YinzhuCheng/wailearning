import assert from 'node:assert/strict'
import { spawnSync } from 'node:child_process'
import test from 'node:test'
import { fileURLToPath } from 'node:url'
import path from 'node:path'

import MarkdownIt from '../../../apps/web/admin/node_modules/markdown-it/index.mjs'
import { copyText } from '../../../apps/web/admin/src/utils/clipboard.js'
import { createCourseMarkdownIt, renderCourseMarkdown } from '../../../apps/web/admin/src/utils/markdownIt.js'

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../..')
const doubleDollar = String.fromCharCode(36, 36)

function render(raw) {
  return renderCourseMarkdown(createCourseMarkdownIt(), raw)
}

function fakeDocument({ execResult = true, execThrows = false } = {}) {
  const created = []
  const removed = []
  const doc = {
    body: {
      appendChild(el) {
        created.push(el)
      },
      removeChild(el) {
        removed.push(el)
      }
    },
    createElement(tag) {
      return {
        tag,
        value: '',
        style: {},
        attrs: {},
        focused: false,
        selected: false,
        range: null,
        setAttribute(name, value) {
          this.attrs[name] = value
        },
        focus() {
          this.focused = true
        },
        select() {
          this.selected = true
        },
        setSelectionRange(start, end) {
          this.range = [start, end]
        }
      }
    },
    execCommand(command) {
      assert.equal(command, 'copy')
      if (execThrows) {
        throw new Error('copy rejected')
      }
      return execResult
    },
    created,
    removed
  }
  return doc
}

test('renderCourseMarkdown keeps multiline $$ display math continuous', () => {
  const html = render(['A', '', doubleDollar, '\\sum_{i=1}^{n} i', doubleDollar].join('\n'))
  assert.match(html, /\$\$\n\\sum_\{i=1\}\^\{n\} i\n\$\$/)
  assert.doesNotMatch(html, /\$\$<br/)
})

test('renderCourseMarkdown keeps multiline \\[ display math continuous', () => {
  const html = render(['A', '', '\\[', '\\int_0^1 x^2\\,dx=\\frac{1}{3}', '\\]'].join('\n'))
  assert.match(html, /\\\[\n\\int_0\^1 x\^2\\,dx=\\frac\{1\}\{3\}\n\\\]/)
  assert.doesNotMatch(html, /\\\[<br/)
})

test('renderCourseMarkdown normalizes CRLF before protecting display math', () => {
  const html = render(['A', '', doubleDollar, 'x+y', doubleDollar].join('\r\n'))
  assert.match(html, /\$\$\nx\+y\n\$\$/)
  assert.doesNotMatch(html, /\$\$<br/)
})

test('renderCourseMarkdown preserves multiple display math blocks in order', () => {
  const html = render(['A', '', doubleDollar, 'x', doubleDollar, '', '\\[', 'y', '\\]', '', doubleDollar, 'z', doubleDollar].join('\n'))
  assert.ok(html.indexOf(`${doubleDollar}\nx\n${doubleDollar}`) < html.indexOf('\\[\ny\n\\]'))
  assert.ok(html.indexOf('\\[\ny\n\\]') < html.indexOf(`${doubleDollar}\nz\n${doubleDollar}`))
})

test('renderCourseMarkdown escapes HTML inside protected display math', () => {
  const html = render(['A', '', doubleDollar, '<script>alert(1)</script>', doubleDollar].join('\n'))
  assert.match(html, /&lt;script&gt;alert\(1\)&lt;\/script&gt;/)
  assert.doesNotMatch(html, /<script>/)
})

test('renderCourseMarkdown keeps user placeholder-like text intact', () => {
  const html = render(`literal @@WL_LATEX_BLOCK_MATH_0_collision@@\n\n${doubleDollar}\nx\n${doubleDollar}`)
  assert.match(html, /@@WL_LATEX_BLOCK_MATH_0_collision@@/)
  assert.match(html, /\$\$\nx\n\$\$/)
})

test('renderCourseMarkdown preserves escaped inline delimiters for KaTeX auto-render', () => {
  const html = render('inline \\(x^2\\) and bracket \\[y\\]')
  assert.match(html, /\\\(x\^2\\\)/)
  assert.match(html, /\\\[y\\\]/)
})

test('copyText uses Clipboard API without DOM fallback when write succeeds async', async () => {
  let wrote = ''
  const doc = fakeDocument()
  const ok = await copyText('abc', {
    navigatorObject: { clipboard: { writeText: async text => { wrote = text } } },
    documentObject: doc
  })
  assert.equal(ok, true)
  assert.equal(wrote, 'abc')
  assert.equal(doc.created.length, 0)
})

test('copyText falls back to textarea when Clipboard API rejects and cleans up', async () => {
  const doc = fakeDocument({ execResult: true })
  const ok = await copyText('abc', {
    navigatorObject: { clipboard: { writeText: async () => { throw new Error('denied') } } },
    documentObject: doc
  })
  assert.equal(ok, true)
  assert.equal(doc.created.length, 1)
  assert.equal(doc.removed.length, 1)
  assert.equal(doc.created[0].value, 'abc')
  assert.deepEqual(doc.created[0].range, [0, 3])
})

test('playwright_preflight reports missing managed backend Python checks as structured JSON', () => {
  const missingPython = path.join(repoRoot, '.agent-run', 'missing-e2e-python.exe')
  const result = spawnSync(
    process.env.PYTHON || 'python',
    ['ops/scripts/dev/playwright_preflight.py', '--json'],
    {
      cwd: repoRoot,
      encoding: 'utf8',
      env: {
        ...process.env,
        E2E_PYTHON: missingPython,
        PLAYWRIGHT_USE_EXTERNAL_SERVERS: ''
      }
    }
  )
  assert.notEqual(result.status, 0)
  const payload = JSON.parse(result.stdout)
  const statuses = new Map(payload.checks.map(check => [check.name, check.status]))
  assert.equal(statuses.get('playwright-config'), 'pass')
  assert.equal(statuses.get('vite-bin'), 'pass')
  assert.equal(statuses.get('e2e-python'), 'fail')
  assert.equal(statuses.get('python-version'), 'fail')
  assert.equal(statuses.get('requirements-python-compat'), 'fail')
  assert.equal(statuses.get('backend-imports'), 'fail')
  assert.equal(statuses.get('password-hash-smoke'), 'fail')
})
