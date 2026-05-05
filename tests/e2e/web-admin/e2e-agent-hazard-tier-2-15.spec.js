/**
 * Second batch of fifteen additive high-difficulty E2E (API-first) checks: route ``le=`` differences,
 * unauthenticated smoke, parent-code contract, course-catalog role gates, and parallel mark-all-read
 * (triple) stress on the same subject scope as the seed scenario.
 *
 * Preconditions (identical to ``e2e-agent-hazard-tier-15.spec.js``):
 * - Playwright globalSetup with ``E2E_DEV_SEED_TOKEN`` (writes ``.cache/scenario.json`` under this dir).
 * - Run **one** Playwright process at a time on the default E2E ports (Pitfall 41: ``ECONNRESET`` from
 *   parallel webServer / port 8012 contention). Use ``CI=1`` in CI to reduce worker parallelism.
 *
 * Intentional blind spots (documented in ``docs/development/DEVELOPMENT_AND_TESTING.md`` § agent hazard):
 * - No real remote LLM or SMTP; these are loopback + seed-only surfaces.
 * - Parent ``/verify`` returns 200 with ``valid: false`` for unknown codes (not HTTP 404) — do not
 *   assert status 404 on this route without reading ``api/routers/parent.py``.
 */
const { expect, test } = require('@playwright/test')
const { loadE2eScenario, resetE2eScenario } = require('./fixtures.cjs')
const { obtainAccessToken, apiGetJson, apiPostJson } = require('./future-advanced-coverage-helpers.cjs')

const scenario = () => loadE2eScenario()

function apiBase() {
  return (process.env.E2E_API_URL || 'http://127.0.0.1:8012').replace(/\/$/, '')
}

async function fetchStatus(method, pathname, { token, body, headers = {} } = {}) {
  const res = await fetch(`${apiBase()}${pathname}`, {
    method,
    headers: {
      ...(body != null ? { 'Content-Type': 'application/json' } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...headers
    },
    body: body == null ? undefined : JSON.stringify(body)
  })
  return res.status
}

async function fetchJson(method, pathname, opts = {}) {
  const res = await fetch(`${apiBase()}${pathname}`, {
    method,
    headers: {
      ...(opts.body != null ? { 'Content-Type': 'application/json' } : {}),
      ...(opts.token ? { Authorization: `Bearer ${opts.token}` } : {}),
      ...(opts.headers || {})
    },
    body: opts.body == null ? undefined : JSON.stringify(opts.body)
  })
  const text = await res.text()
  let data = null
  try {
    data = text ? JSON.parse(text) : null
  } catch {
    data = text
  }
  return { status: res.status, data, text }
}

test.describe('E2E agent hazard tier 2 (15 cases)', () => {
  test.describe.configure({ timeout: 300_000 })

  test.beforeEach(async ({}, testInfo) => {
    const s = await resetE2eScenario()
    if (!s) {
      testInfo.skip(true, 'Missing e2e seed; set E2E_DEV_SEED_TOKEN and globalSetup')
    }
  })

  test('01 GET /health and /api/health both return 200', async () => {
    const r1 = await fetch(`${apiBase()}/health`)
    const r2 = await fetch(`${apiBase()}/api/health`)
    expect(r1.ok && r2.ok).toBe(true)
  })

  test('02 GET /api/settings/public unauthenticated returns JSON', async () => {
    const { status, data } = await fetchJson('GET', '/api/settings/public')
    expect(status).toBe(200)
    expect(data && typeof data).toBe('object')
  })

  test('03 parent verify unknown code returns 200 with valid false', async () => {
    const { status, data } = await fetchJson('GET', '/api/parent/verify/NOTREAL01')
    expect(status).toBe(200)
    expect(data && data.valid).toBe(false)
  })

  test('04 teacher GET /api/subjects/course-catalog is 403', async () => {
    const s = scenario()
    const tok = await obtainAccessToken(s.teacher_own.username, s.password_teacher_student)
    const st = await fetchStatus('GET', '/api/subjects/course-catalog', { token: tok })
    expect(st).toBe(403)
  })

  test('05 teacher GET /api/subjects/elective-catalog is 403', async () => {
    const s = scenario()
    const tok = await obtainAccessToken(s.teacher_own.username, s.password_teacher_student)
    const st = await fetchStatus('GET', '/api/subjects/elective-catalog', { token: tok })
    expect(st).toBe(403)
  })

  test('06 student GET /api/homeworks page_size=200 returns 422', async () => {
    const s = scenario()
    const tok = await obtainAccessToken(s.student_plain.username, s.password_teacher_student)
    const st = await fetchStatus('GET', '/api/homeworks?page=1&page_size=200', { token: tok })
    expect(st).toBe(422)
  })

  test('07 teacher GET /api/materials page_size=200 with subject_id returns 422', async () => {
    const s = scenario()
    const tok = await obtainAccessToken(s.teacher_own.username, s.password_teacher_student)
    const subj = Number(s.course_required_id)
    const st = await fetchStatus(
      'GET',
      `/api/materials?subject_id=${subj}&page=1&page_size=200`,
      { token: tok }
    )
    expect(st).toBe(422)
  })

  test('08 teacher GET /api/points/records/{student} page_size=200 returns 422', async () => {
    const s = scenario()
    const tok = await obtainAccessToken(s.teacher_own.username, s.password_teacher_student)
    const sid = Number(s.student_plain.student_row_id)
    const st = await fetchStatus(
      'GET',
      `/api/points/records/${sid}?page=1&page_size=200`,
      { token: tok }
    )
    expect(st).toBe(422)
  })

  test('09 unauthenticated GET /api/subjects returns 401', async () => {
    const st = await fetchStatus('GET', '/api/subjects')
    expect(st).toBe(401)
  })

  test('10 admin PUT quota policy parallel_tasks=0 returns 422', async () => {
    const s = scenario()
    const tok = await obtainAccessToken(s.admin.username, s.admin.password)
    const before = await apiGetJson('/api/llm-settings/admin/quota-policy', tok)
    const { status } = await fetchJson('PUT', '/api/llm-settings/admin/quota-policy', {
      token: tok,
      body: { ...before, max_parallel_grading_tasks: 0 }
    })
    expect(status).toBe(422)
  })

  test('11 student GET /api/discussions page_size=200 returns 422', async () => {
    const s = scenario()
    const tok = await obtainAccessToken(s.student_plain.username, s.password_teacher_student)
    const mid = Number(s.material_discussion_id)
    const subj = Number(s.course_required_id)
    const cls = Number(s.class_id_1)
    const path =
      `/api/discussions?target_type=material&target_id=${mid}` +
      `&subject_id=${subj}&class_id=${cls}&page=1&page_size=200`
    const st = await fetchStatus('GET', path, { token: tok })
    expect(st).toBe(422)
  })

  test('12 triple concurrent POST mark-all-read all 200', async () => {
    const s = scenario()
    const stTok = await obtainAccessToken(s.student_plain.username, s.password_teacher_student)
    const thTok = await obtainAccessToken(s.teacher_own.username, s.password_teacher_student)
    const subj = Number(s.course_required_id)
    const cls = Number(s.class_id_1)
    for (let i = 0; i < 3; i += 1) {
      const cr = await fetchJson('POST', '/api/notifications', {
        token: thTok,
        body: { title: `tier2-triple-${i}`, content: 'x', class_id: cls, subject_id: subj }
      })
      expect(cr.status).toBe(200)
    }
    const url = `${apiBase()}/api/notifications/mark-all-read?subject_id=${subj}`
    const [a, b, c] = await Promise.all([
      fetch(url, { method: 'POST', headers: { Authorization: `Bearer ${stTok}` } }),
      fetch(url, { method: 'POST', headers: { Authorization: `Bearer ${stTok}` } }),
      fetch(url, { method: 'POST', headers: { Authorization: `Bearer ${stTok}` } })
    ])
    expect(a.ok && b.ok && c.ok).toBe(true)
    const sync = await apiGetJson(`/api/notifications/sync-status?subject_id=${subj}`, stTok)
    expect(sync.unread_count).toBe(0)
  })

  test('13 admin PUT quota override unknown student returns 404', async () => {
    const s = scenario()
    const tok = await obtainAccessToken(s.admin.username, s.admin.password)
    const { status } = await fetchJson(
      'PUT',
      '/api/llm-settings/admin/students/999999999/quota-override',
      { token: tok, body: { daily_tokens: 5000 } }
    )
    expect(status).toBe(404)
  })

  test('14 teacher GET /api/students page_size=1000 returns 200', async () => {
    const s = scenario()
    const tok = await obtainAccessToken(s.teacher_own.username, s.password_teacher_student)
    const cls = Number(s.class_id_1)
    const st = await fetchStatus('GET', `/api/students?class_id=${cls}&page=1&page_size=1000`, {
      token: tok
    })
    expect(st).toBe(200)
  })

  test('15 teacher GET /api/students page_size=2000 returns 422', async () => {
    const s = scenario()
    const tok = await obtainAccessToken(s.teacher_own.username, s.password_teacher_student)
    const cls = Number(s.class_id_1)
    const st = await fetchStatus('GET', `/api/students?class_id=${cls}&page=1&page_size=2000`, {
      token: tok
    })
    expect(st).toBe(422)
  })
})
