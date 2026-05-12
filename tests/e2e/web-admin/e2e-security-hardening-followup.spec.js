/**
 * Small browser-backed security hardening slice.
 *
 * These cases intentionally use Playwright's browser/request environment to
 * prove API authorization still holds when a user bypasses visible UI controls.
 */
const { expect, test } = require('@playwright/test')
const { loadE2eScenario, resetE2eScenario } = require('./fixtures.cjs')
const { login, obtainAccessToken } = require('./future-advanced-coverage-helpers.cjs')

const scenario = () => loadE2eScenario()

function apiBase() {
  return (process.env.E2E_API_URL || 'http://127.0.0.1:8012').replace(/\/$/, '')
}

async function apiStatus(pathname, { method = 'GET', token, headers = {}, body } = {}) {
  const res = await fetch(`${apiBase()}${pathname}`, {
    method,
    headers: {
      ...(body == null ? {} : { 'Content-Type': 'application/json' }),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...headers
    },
    body: body == null ? undefined : JSON.stringify(body)
  })
  return { status: res.status, text: await res.text() }
}

test.describe('security hardening follow-up E2E (8 cases)', () => {
  test.describe.configure({ timeout: 180_000 })

  test.beforeEach(async ({}, testInfo) => {
    const s = await resetE2eScenario()
    if (!s) {
      testInfo.skip(true, 'Missing e2e seed; run via scripts/playwright-external-runner.cjs')
    }
  })

  test('01 tampering stored role in browser does not grant admin API access', async ({ page }) => {
    const s = scenario()
    await login(page, s.student_plain.username, s.password_teacher_student)
    await page.evaluate(() => {
      localStorage.setItem('user_role', 'admin')
      localStorage.setItem('role', 'admin')
      const raw = localStorage.getItem('user')
      if (raw) {
        try {
          const parsed = JSON.parse(raw)
          parsed.role = 'admin'
          localStorage.setItem('user', JSON.stringify(parsed))
        } catch {
          /* ignore non-JSON storage */
        }
      }
    })
    const token = await page.evaluate(() => localStorage.getItem('token') || localStorage.getItem('access_token'))
    expect(token).toBeTruthy()

    const res = await page.request.get(`${apiBase()}/api/users`, {
      headers: { Authorization: `Bearer ${token}` }
    })
    expect(res.status()).toBe(403)
  })

  test('02 student direct POST to admin course creation API is forbidden', async () => {
    const s = scenario()
    const token = await obtainAccessToken(s.student_plain.username, s.password_teacher_student)
    const { status } = await apiStatus('/api/subjects', {
      method: 'POST',
      token,
      body: {
        name: `E2E_forbidden_security_${Date.now()}`,
        class_id: s.class_id_1,
        teacher_id: s.teacher_user_id,
        course_type: 'required',
        status: 'active'
      }
    })
    expect(status).toBe(403)
  })

  test('03 seed token alone cannot call powerful E2E mock-LLM endpoint', async () => {
    const { status, text } = await apiStatus('/api/e2e/dev/mock-llm/configure', {
      method: 'POST',
      headers: { 'X-E2E-Seed-Token': process.env.E2E_DEV_SEED_TOKEN || 'test-playwright-seed' },
      body: { profiles: {} }
    })
    expect(status).toBe(403)
    expect(text).toContain('administrator Bearer')
  })

  test('04 old browser token is rejected after password change in another tab', async ({ browser }) => {
    const s = scenario()
    const ctxA = await browser.newContext()
    const ctxB = await browser.newContext()
    const pageA = await ctxA.newPage()
    const pageB = await ctxB.newPage()
    const newPassword = `E2eNew_${Date.now()}!a9`
    try {
      await login(pageA, s.student_drop.username, s.password_teacher_student)
      const oldToken = await pageA.evaluate(() => localStorage.getItem('token') || localStorage.getItem('access_token'))
      expect(oldToken).toBeTruthy()

      await login(pageB, s.student_drop.username, s.password_teacher_student)
      const change = await pageB.request.post(`${apiBase()}/api/auth/change-password`, {
        headers: { Authorization: `Bearer ${oldToken}`, 'Content-Type': 'application/json' },
        data: {
          current_password: s.password_teacher_student,
          new_password: newPassword,
          confirm_password: newPassword
        }
      })
      expect(change.status()).toBe(200)

      const stale = await pageA.request.get(`${apiBase()}/api/auth/me`, {
        headers: { Authorization: `Bearer ${oldToken}` }
      })
      expect(stale.status()).toBe(401)

      const freshToken = await obtainAccessToken(s.student_drop.username, newPassword)
      const restore = await apiStatus('/api/auth/change-password', {
        method: 'POST',
        token: freshToken,
        body: {
          current_password: newPassword,
          new_password: s.password_teacher_student,
          confirm_password: s.password_teacher_student
        }
      })
      expect(restore.status).toBe(200)
    } finally {
      await ctxA.close().catch(() => {})
      await ctxB.close().catch(() => {})
    }
  })

  test('05 class teacher cannot rebind visible required course to another class via direct API', async () => {
    const s = scenario()
    const token = await obtainAccessToken(s.class_teacher.username, s.password_teacher_student)
    const before = await apiStatus(`/api/subjects/${s.course_required_id}`, { token })
    expect(before.status).toBe(200)

    const rebinding = await apiStatus(`/api/subjects/${s.course_required_id}`, {
      method: 'PUT',
      token,
      body: { class_id: s.class_id_2 }
    })
    expect(rebinding.status).toBe(403)

    const after = await apiStatus(`/api/subjects/${s.course_required_id}`, { token })
    expect(after.status).toBe(200)
    const payload = JSON.parse(after.text)
    const ids = (payload.class_links || []).map(row => Number(row.class_id))
    expect(ids).toContain(Number(s.class_id_1))
    expect(ids).not.toContain(Number(s.class_id_2))
  })

  test('06 class teacher cannot hijack teacher-owned visible course by updating metadata', async () => {
    const s = scenario()
    const token = await obtainAccessToken(s.class_teacher.username, s.password_teacher_student)

    const before = await apiStatus(`/api/subjects/${s.course_required_id}`, { token })
    expect(before.status).toBe(200)
    const beforePayload = JSON.parse(before.text)
    expect(Number(beforePayload.teacher_id)).toBe(Number(s.teacher_user_id))

    const hijack = await apiStatus(`/api/subjects/${s.course_required_id}`, {
      method: 'PUT',
      token,
      body: { name: `E2E forbidden hijack ${Date.now()}` }
    })
    expect(hijack.status).toBe(403)

    const after = await apiStatus(`/api/subjects/${s.course_required_id}`, { token })
    expect(after.status).toBe(200)
    const afterPayload = JSON.parse(after.text)
    expect(Number(afterPayload.teacher_id)).toBe(Number(s.teacher_user_id))
  })

  test('07 class teacher cannot delete teacher-owned visible course via direct API', async () => {
    const s = scenario()
    const token = await obtainAccessToken(s.class_teacher.username, s.password_teacher_student)

    const before = await apiStatus(`/api/subjects/${s.course_required_id}`, { token })
    expect(before.status).toBe(200)

    const deletion = await apiStatus(`/api/subjects/${s.course_required_id}`, { method: 'DELETE', token })
    expect(deletion.status).toBe(403)

    const after = await apiStatus(`/api/subjects/${s.course_required_id}`, { token })
    expect(after.status).toBe(200)
  })

  test('08 class teacher cannot sync teacher-owned visible course roster via direct API', async () => {
    const s = scenario()
    const token = await obtainAccessToken(s.class_teacher.username, s.password_teacher_student)

    const before = await apiStatus(`/api/subjects/${s.course_required_id}`, { token })
    expect(before.status).toBe(200)

    const sync = await apiStatus(`/api/subjects/${s.course_required_id}/sync-enrollments`, {
      method: 'POST',
      token
    })
    expect(sync.status).toBe(403)
  })
})
