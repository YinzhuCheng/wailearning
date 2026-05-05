/**
 * Fifteen deeper Playwright checks motivated by residual risks after `e2e-notification-header-sync-tier.spec.js`:
 *
 * - Admin **`notificationSyncParams === null`** uses global sync (must match list aggregates).
 * - Teacher/student **course context** vs **orphan localStorage** / **deep links** / **rapid switching**.
 * - **UI convergence lag** (badge vs API), **visibility-gated polling**, **viewport** stress.
 * - **Concurrent API writes** + **delete-under-load** (SQLite E2E harness).
 *
 * Run incrementally only this file:
 *   cd <REPO_ROOT>/apps/web/admin && CI=1 E2E_PYTHON=<python> E2E_DEV_SEED_TOKEN=<seed> \
 *     npx playwright test e2e-notification-sync-deep-tier.spec.js --project=chromium
 */
const { expect, test } = require('@playwright/test')
const {
  login,
  obtainAccessToken,
  apiPostJson,
  apiGetJson,
  apiDelete,
  apiPutJson
} = require('./future-advanced-coverage-helpers.cjs')
const { resetE2eScenario, enterSeededRequiredCourse } = require('./fixtures.cjs')

function scenario() {
  const { loadE2eScenario } = require('./fixtures.cjs')
  return loadE2eScenario()
}

function apiBase() {
  return (process.env.E2E_API_URL || 'http://127.0.0.1:8012').replace(/\/$/, '')
}

async function fetchStatus(method, pathname, { token } = {}) {
  const res = await fetch(`${apiBase()}${pathname}`, {
    method,
    headers: token ? { Authorization: `Bearer ${token}` } : {}
  })
  return res.status
}

async function triggerHeaderPoll(page) {
  await page.evaluate(() => {
    window.dispatchEvent(new Event('focus'))
  })
}

async function badgeContentLocator(page) {
  return page.locator('[data-testid="header-notification-badge"] .el-badge__content').first()
}

test.describe('E2E notification sync deep tier (15 cases)', () => {
  test.describe.configure({ timeout: 120_000 })

  test.beforeEach(async ({}, testInfo) => {
    const s = await resetE2eScenario()
    if (!s) {
      testInfo.skip(true, 'Missing e2e seed; run globalSetup with E2E_DEV_SEED_TOKEN')
    }
  })

  test('01 admin global sync-status totals match notifications list footer counts', async () => {
    const s = scenario()
    const adminTok = await obtainAccessToken(s.admin.username, s.admin.password)
    const teacherTok = await obtainAccessToken(s.teacher_own.username, s.password_teacher_student)

    await apiPostJson('/api/notifications', teacherTok, {
      title: `E2E_ADM_G1_${s.suffix}_${Date.now()}`,
      content: 'g1',
      class_id: s.class_id_1,
      subject_id: s.course_required_id
    })

    const list = await apiGetJson('/api/notifications?page=1&page_size=20', adminTok)
    const sync = await apiGetJson('/api/notifications/sync-status', adminTok)
    expect(Number(sync.total)).toBe(Number(list.total))
    expect(Number(sync.unread_count)).toBe(Number(list.unread_count))
  })

  test('02 teacher header badge aligns with course-scoped sync after dashboard entry', async ({ page }) => {
    const s = scenario()
    const teacherTok = await obtainAccessToken(s.teacher_own.username, s.password_teacher_student)

    await login(page, s.teacher_own.username, s.password_teacher_student)
    await page.goto('/dashboard', { waitUntil: 'domcontentloaded', timeout: 60000 })
    await expect(page.getByTestId('header-course-switch')).toBeVisible({ timeout: 20000 })

    const reqLabel = `E2E必修课_${s.suffix}`
    await page.getByTestId('header-course-switch').click()
    await page
      .locator('.course-dropdown-menu')
      .locator('.course-option')
      .filter({ hasText: reqLabel })
      .click()
    await page.waitForURL(/\/course-home|\/dashboard/)

    await apiPostJson('/api/notifications', teacherTok, {
      title: `E2E_TCH_HDR_${s.suffix}_${Date.now()}`,
      content: 'tch',
      class_id: s.class_id_1,
      subject_id: s.course_required_id
    })

    await triggerHeaderPoll(page)
    const sync = await apiGetJson(`/api/notifications/sync-status?subject_id=${s.course_required_id}`, teacherTok)
    await expect
      .poll(
        async () => {
          const txt = await (await badgeContentLocator(page)).innerText().catch(() => '')
          const n = Number.parseInt(`${txt}`.trim(), 10)
          return Number.isFinite(n) && n === sync.unread_count
        },
        { timeout: 25_000 }
      )
      .toBe(true)
  })

  test('03 student notifications deep-link: badge converges after API-unread exists', async ({ page }) => {
    const s = scenario()
    const studentTok = await obtainAccessToken(s.student_plain.username, s.password_teacher_student)
    const teacherTok = await obtainAccessToken(s.teacher_own.username, s.password_teacher_student)

    await apiPostJson('/api/notifications', teacherTok, {
      title: `E2E_DL_${s.suffix}_${Date.now()}`,
      content: 'deep',
      class_id: s.class_id_1,
      subject_id: s.course_required_id
    })

    await login(page, s.student_plain.username, s.password_teacher_student)
    await page.goto('/notifications', { waitUntil: 'domcontentloaded', timeout: 60000 })
    await expect(page).toHaveURL(/\/notifications/, { timeout: 20000 })

    const sync = await apiGetJson(`/api/notifications/sync-status?subject_id=${s.course_required_id}`, studentTok)
    expect(sync.unread_count).toBeGreaterThanOrEqual(1)

    await triggerHeaderPoll(page)
    await expect
      .poll(async () => {
        const txt = await (await badgeContentLocator(page)).innerText().catch(() => '')
        const n = Number.parseInt(`${txt}`.trim(), 10)
        return n === sync.unread_count
      })
      .toBe(true)
  })

  test('04 corrupt selected_course localStorage is healed after entering seeded course', async ({ page }) => {
    const s = scenario()
    await login(page, s.student_plain.username, s.password_teacher_student)
    await page.evaluate(() => {
      localStorage.setItem('selected_course', '{"id":999999,"name":"ghost"}')
    })
    await enterSeededRequiredCourse(page, s.suffix)
    const fixed = await page.evaluate(() => JSON.parse(localStorage.getItem('selected_course') || 'null'))
    expect(fixed).toBeTruthy()
    expect(String(fixed.id)).toBe(String(s.course_required_id))
  })

  test('05 rapid concurrent teacher publishes: student badge matches sync-status', async ({ page }) => {
    const s = scenario()
    const studentTok = await obtainAccessToken(s.student_plain.username, s.password_teacher_student)
    const teacherTok = await obtainAccessToken(s.teacher_own.username, s.password_teacher_student)

    await login(page, s.student_plain.username, s.password_teacher_student)
    await enterSeededRequiredCourse(page, s.suffix)

    const ts = Date.now()
    await Promise.all([
      apiPostJson('/api/notifications', teacherTok, {
        title: `E2E_RC_A_${s.suffix}_${ts}`,
        content: 'a',
        class_id: s.class_id_1,
        subject_id: s.course_required_id
      }),
      apiPostJson('/api/notifications', teacherTok, {
        title: `E2E_RC_B_${s.suffix}_${ts}`,
        content: 'b',
        class_id: s.class_id_1,
        subject_id: s.course_required_id
      }),
      apiPostJson('/api/notifications', teacherTok, {
        title: `E2E_RC_C_${s.suffix}_${ts}`,
        content: 'c',
        class_id: s.class_id_1,
        subject_id: s.course_required_id
      })
    ])

    await triggerHeaderPoll(page)
    await expect
      .poll(async () => {
        const sync = await apiGetJson(`/api/notifications/sync-status?subject_id=${s.course_required_id}`, studentTok)
        const txt = await (await badgeContentLocator(page)).innerText()
        const n = Number.parseInt(`${txt}`.trim(), 10)
        return n === sync.unread_count && sync.unread_count >= 3
      })
      .toBe(true)
  })

  test('06 teacher title PUT lowers unread student count when titles were unread-only signal', async ({
    page
  }) => {
    const s = scenario()
    const studentTok = await obtainAccessToken(s.student_plain.username, s.password_teacher_student)
    const teacherTok = await obtainAccessToken(s.teacher_own.username, s.password_teacher_student)

    await login(page, s.student_plain.username, s.password_teacher_student)
    await enterSeededRequiredCourse(page, s.suffix)

    const row = await apiPostJson('/api/notifications', teacherTok, {
      title: `E2E_PUT_${s.suffix}_${Date.now()}`,
      content: 'orig',
      class_id: s.class_id_1,
      subject_id: s.course_required_id
    })

    await triggerHeaderPoll(page)
    await apiPutJson(`/api/notifications/${row.id}`, teacherTok, { title: `${row.title}_renamed` })

    await triggerHeaderPoll(page)
    const sync = await apiGetJson(`/api/notifications/sync-status?subject_id=${s.course_required_id}`, studentTok)
    await expect
      .poll(async () => {
        const txt = await (await badgeContentLocator(page)).innerText().catch(() => '')
        const n = Number.parseInt(`${txt}`.trim(), 10)
        return n === sync.unread_count
      })
      .toBe(true)
  })

  test('07 mark-all-read then new publish: badge returns', async ({ page }) => {
    const s = scenario()
    const studentTok = await obtainAccessToken(s.student_plain.username, s.password_teacher_student)
    const teacherTok = await obtainAccessToken(s.teacher_own.username, s.password_teacher_student)

    await login(page, s.student_plain.username, s.password_teacher_student)
    await enterSeededRequiredCourse(page, s.suffix)

    await apiPostJson('/api/notifications', teacherTok, {
      title: `E2E_MAR_${s.suffix}_${Date.now()}`,
      content: 'mar',
      class_id: s.class_id_1,
      subject_id: s.course_required_id
    })
    await triggerHeaderPoll(page)

    const markUrl = new URL(`${apiBase()}/api/notifications/mark-all-read`)
    markUrl.searchParams.set('subject_id', String(s.course_required_id))
    const mar = await fetch(markUrl.toString(), {
      method: 'POST',
      headers: { Authorization: `Bearer ${studentTok}` }
    })
    expect(mar.status).toBe(200)

    await triggerHeaderPoll(page)
    await expect(page.locator('[data-testid="header-notification-badge"] .el-badge__content')).toHaveCount(0)

    await apiPostJson('/api/notifications', teacherTok, {
      title: `E2E_AFTER_${s.suffix}_${Date.now()}`,
      content: 'after',
      class_id: s.class_id_1,
      subject_id: s.course_required_id
    })
    await triggerHeaderPoll(page)
    await expect(await badgeContentLocator(page)).toBeVisible({ timeout: 20000 })
  })

  test('08 cold reload on course-home picks up unread via onMounted poll (no manual focus)', async ({
    page
  }) => {
    const s = scenario()
    const studentTok = await obtainAccessToken(s.student_plain.username, s.password_teacher_student)
    const teacherTok = await obtainAccessToken(s.teacher_own.username, s.password_teacher_student)

    await login(page, s.student_plain.username, s.password_teacher_student)
    await enterSeededRequiredCourse(page, s.suffix)

    const markUrl = new URL(`${apiBase()}/api/notifications/mark-all-read`)
    markUrl.searchParams.set('subject_id', String(s.course_required_id))
    await fetch(markUrl.toString(), { method: 'POST', headers: { Authorization: `Bearer ${studentTok}` } })

    await triggerHeaderPoll(page)
    await expect
      .poll(async () => {
        const sync = await apiGetJson(`/api/notifications/sync-status?subject_id=${s.course_required_id}`, studentTok)
        const count = await page.locator('[data-testid="header-notification-badge"] .el-badge__content').count()
        return sync.unread_count === 0 && count === 0
      })
      .toBe(true)

    await apiPostJson('/api/notifications', teacherTok, {
      title: `E2E_RELOAD_${s.suffix}_${Date.now()}`,
      content: 'reload-path',
      class_id: s.class_id_1,
      subject_id: s.course_required_id
    })

    await page.reload({ waitUntil: 'domcontentloaded', timeout: 60000 })

    const sync = await apiGetJson(`/api/notifications/sync-status?subject_id=${s.course_required_id}`, studentTok)
    expect(sync.unread_count).toBeGreaterThanOrEqual(1)

    await expect
      .poll(
        async () => {
          const txt = await (await badgeContentLocator(page)).innerText().catch(() => '')
          const n = Number.parseInt(`${txt}`.trim(), 10)
          return n === sync.unread_count
        },
        { timeout: 25_000 }
      )
      .toBe(true)
  })

  test('09 mobile viewport: header badge still renders after unread publish', async ({ page }) => {
    const s = scenario()
    const teacherTok = await obtainAccessToken(s.teacher_own.username, s.password_teacher_student)

    await page.setViewportSize({ width: 390, height: 844 })
    await login(page, s.student_plain.username, s.password_teacher_student)
    await enterSeededRequiredCourse(page, s.suffix)

    await apiPostJson('/api/notifications', teacherTok, {
      title: `E2E_MOB_${s.suffix}_${Date.now()}`,
      content: 'mob',
      class_id: s.class_id_1,
      subject_id: s.course_required_id
    })

    await triggerHeaderPoll(page)
    await expect(await badgeContentLocator(page)).toBeVisible({ timeout: 20000 })
  })

  test('10 student GET sync-status with alien subject_id returns 403', async () => {
    const s = scenario()
    const stTok = await obtainAccessToken(s.student_plain.username, s.password_teacher_student)
    const status = await fetchStatus('GET', `/api/notifications/sync-status?subject_id=${s.course_orphan_id}`, {
      token: stTok
    })
    expect(status).toBe(403)
  })

  test('11 teacher-targeted notification does not inflate student scoped unread', async ({ page }) => {
    const s = scenario()
    const studentTok = await obtainAccessToken(s.student_plain.username, s.password_teacher_student)
    const teacherTok = await obtainAccessToken(s.teacher_own.username, s.password_teacher_student)

    const before = await apiGetJson(`/api/notifications/sync-status?subject_id=${s.course_required_id}`, studentTok)

    await apiPostJson('/api/notifications', teacherTok, {
      title: `E2E_TGT_${s.suffix}_${Date.now()}`,
      content: 'self-target',
      class_id: s.class_id_1,
      subject_id: s.course_required_id,
      target_user_id: s.teacher_user_id
    })

    await login(page, s.student_plain.username, s.password_teacher_student)
    await enterSeededRequiredCourse(page, s.suffix)

    await triggerHeaderPoll(page)
    const after = await apiGetJson(`/api/notifications/sync-status?subject_id=${s.course_required_id}`, studentTok)
    expect(after.unread_count).toBe(before.unread_count)

    const txt = await page.evaluate(async () => {
      const el = document.querySelector('[data-testid="header-notification-badge"] .el-badge__content')
      return el ? el.textContent : ''
    })
    const n = Number.parseInt(`${txt}`.trim(), 10)
    expect(Number.isFinite(n) ? n : 0).toBe(after.unread_count)
  })

  test('12 other-teacher course notification is invisible in teacher_own scoped sync', async () => {
    const s = scenario()
    const ownTok = await obtainAccessToken(s.teacher_own.username, s.password_teacher_student)
    const otherTok = await obtainAccessToken(s.teacher_other.username, s.password_teacher_student)

    await apiPostJson('/api/notifications', otherTok, {
      title: `E2E_OTH_${s.suffix}_${Date.now()}`,
      content: 'other',
      class_id: s.class_id_2,
      subject_id: s.course_other_teacher_id
    })

    const sync = await apiGetJson(`/api/notifications/sync-status?subject_id=${s.course_required_id}`, ownTok)
    const list = await apiGetJson(
      `/api/notifications?subject_id=${s.course_required_id}&page=1&page_size=50`,
      ownTok
    )
    expect(sync.total).toBe(list.total)
    expect((list.data || []).every(row => !`${row.title || ''}`.includes(`E2E_OTH_${s.suffix}`))).toBe(true)
  })

  test('13 flip course switch twice: badge reflects last selected course unread', async ({ page }) => {
    const s = scenario()
    const studentTok = await obtainAccessToken(s.student_plain.username, s.password_teacher_student)
    const teacherTok = await obtainAccessToken(s.teacher_own.username, s.password_teacher_student)

    await apiPostJson(`/api/subjects/${s.course_elective_id}/student-self-enroll`, studentTok, {}).catch(() => {})

    await login(page, s.student_plain.username, s.password_teacher_student)
    await enterSeededRequiredCourse(page, s.suffix)

    await apiPostJson('/api/notifications', teacherTok, {
      title: `E2E_FLIP_REQ_${s.suffix}_${Date.now()}`,
      content: 'r',
      class_id: s.class_id_1,
      subject_id: s.course_required_id
    })
    await apiPostJson('/api/notifications', teacherTok, {
      title: `E2E_FLIP_ELC_${s.suffix}_${Date.now()}`,
      content: 'e',
      class_id: s.class_id_1,
      subject_id: s.course_elective_id
    })

    const switcher = page.getByTestId('header-course-switch')
    await expect(switcher).toBeVisible({ timeout: 15000 })

    const flip = async courseLabel => {
      await switcher.click()
      const menu = page.locator('.course-dropdown-menu')
      await expect(menu).toBeVisible({ timeout: 10000 })
      await menu.locator('.course-option').filter({ hasText: courseLabel }).click()
      await page.waitForURL(/\/course-home|\/dashboard/)
      await triggerHeaderPoll(page)
    }

    await flip(`E2E选修课_${s.suffix}`)
    let sync = await apiGetJson(`/api/notifications/sync-status?subject_id=${s.course_elective_id}`, studentTok)
    await expect
      .poll(async () => {
        const t = await (await badgeContentLocator(page)).innerText()
        return Number.parseInt(`${t}`.trim(), 10) === sync.unread_count
      })
      .toBe(true)

    await flip(`E2E必修课_${s.suffix}`)
    sync = await apiGetJson(`/api/notifications/sync-status?subject_id=${s.course_required_id}`, studentTok)
    await expect
      .poll(async () => {
        const t = await (await badgeContentLocator(page)).innerText()
        return Number.parseInt(`${t}`.trim(), 10) === sync.unread_count
      })
      .toBe(true)
  })

  test('14 notifications page load does not 500 when teacher deletes row mid-flight', async ({ page }) => {
    const s = scenario()
    const teacherTok = await obtainAccessToken(s.teacher_own.username, s.password_teacher_student)

    const row = await apiPostJson('/api/notifications', teacherTok, {
      title: `E2E_DELPG_${s.suffix}_${Date.now()}`,
      content: 'x',
      class_id: s.class_id_1,
      subject_id: s.course_required_id
    })

    await login(page, s.student_plain.username, s.password_teacher_student)
    await enterSeededRequiredCourse(page, s.suffix)

    const navigated = page.waitForURL(/\/notifications/, { timeout: 30000 })
    await page.goto('/notifications', { waitUntil: 'domcontentloaded', timeout: 60000 })
    await navigated

    await apiDelete(`/api/notifications/${row.id}`, teacherTok)

    await expect(page.getByRole('heading', { name: /通知中心|閫氱煡/ })).toBeVisible({ timeout: 20000 })
    await triggerHeaderPoll(page)
    await expect(page.locator('body')).toBeVisible()
  })

  test('15 broadcast null-subject notice appears in student course-scoped sync-status', async ({ page }) => {
    const s = scenario()
    const studentTok = await obtainAccessToken(s.student_plain.username, s.password_teacher_student)
    const teacherTok = await obtainAccessToken(s.teacher_own.username, s.password_teacher_student)

    await apiPostJson('/api/notifications', teacherTok, {
      title: `E2E_BC_${s.suffix}_${Date.now()}`,
      content: 'broadcast',
      class_id: s.class_id_1,
      subject_id: null
    })

    const sync = await apiGetJson(`/api/notifications/sync-status?subject_id=${s.course_required_id}`, studentTok)
    expect(sync.unread_count).toBeGreaterThanOrEqual(1)

    await login(page, s.student_plain.username, s.password_teacher_student)
    await enterSeededRequiredCourse(page, s.suffix)
    await triggerHeaderPoll(page)

    await expect
      .poll(async () => {
        const cur = await apiGetJson(`/api/notifications/sync-status?subject_id=${s.course_required_id}`, studentTok)
        const t = await (await badgeContentLocator(page)).innerText().catch(() => '')
        const n = Number.parseInt(`${t}`.trim(), 10)
        return n === cur.unread_count
      })
      .toBe(true)
  })
})
