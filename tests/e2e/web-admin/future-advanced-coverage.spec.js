const { expect, test } = require('@playwright/test')
const { loadE2eScenario, resetE2eScenario, enterSeededRequiredCourse } = require('./fixtures.cjs')

const scenario = () => loadE2eScenario()

function apiBase() {
  return (process.env.E2E_API_URL || 'http://127.0.0.1:8012').replace(/\/$/, '')
}

async function login(page, username, password) {
  await page.goto('/login', { waitUntil: 'load', timeout: 60000 })
  await expect(page.getByTestId('login-username')).toBeVisible({ timeout: 30000 })
  await page.getByTestId('login-username').fill(username)
  await page.getByTestId('login-password').fill(password)
  await page.getByTestId('login-submit').click()
  await page.waitForURL(url => !url.pathname.includes('/login'), { timeout: 20000 })
}

async function obtainAccessToken(username, password) {
  const body = new URLSearchParams()
  body.set('username', username)
  body.set('password', password)
  const res = await fetch(`${apiBase()}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body
  })
  if (!res.ok) {
    throw new Error(`login failed ${res.status}: ${await res.text()}`)
  }
  const data = await res.json()
  return data.access_token
}

async function apiGetJson(pathname, token) {
  const res = await fetch(`${apiBase()}${pathname}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {}
  })
  if (!res.ok) {
    throw new Error(`GET ${pathname} failed ${res.status}: ${await res.text()}`)
  }
  return res.json()
}

async function apiPostJson(pathname, token, body) {
  const res = await fetch(`${apiBase()}${pathname}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {})
    },
    body: JSON.stringify(body)
  })
  if (!res.ok) {
    throw new Error(`POST ${pathname} failed ${res.status}: ${await res.text()}`)
  }
  return res.json()
}

async function apiPatchJson(pathname, token, body) {
  const res = await fetch(`${apiBase()}${pathname}`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {})
    },
    body: JSON.stringify(body)
  })
  if (!res.ok) {
    throw new Error(`PATCH ${pathname} failed ${res.status}: ${await res.text()}`)
  }
  return res.json()
}

async function apiListNotifications(token, params = {}) {
  const url = new URL(`${apiBase()}/api/notifications`)
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== '') {
      url.searchParams.set(key, String(value))
    }
  }
  const res = await fetch(url.toString(), {
    headers: { Authorization: `Bearer ${token}` }
  })
  if (!res.ok) {
    throw new Error(`notifications list failed ${res.status}: ${await res.text()}`)
  }
  return res.json()
}

test.describe.skip('Future advanced E2E coverage expansion', () => {
  test.describe.configure({ timeout: 180_000 })

  test.beforeEach(async ({}, testInfo) => {
    const s = await resetE2eScenario()
    if (!s) {
      testInfo.skip(true, 'Missing e2e seed cache; run globalSetup with E2E_DEV_SEED_TOKEN first')
    }
  })

  test.skip('1. student stale-tab homework resubmit after teacher hard review keeps one authoritative attempt history', async ({ browser }) => {
    const s = scenario()
    const teacherCtx = await browser.newContext()
    const studentCtxA = await browser.newContext()
    const studentCtxB = await browser.newContext()
    const teacherPage = await teacherCtx.newPage()
    const studentPageA = await studentCtxA.newPage()
    const studentPageB = await studentCtxB.newPage()

    await login(teacherPage, s.teacher_own.username, s.teacher_own.password)
    await login(studentPageA, s.student_plain.username, s.student_plain.password)
    await login(studentPageB, s.student_plain.username, s.student_plain.password)

    await enterSeededRequiredCourse(studentPageA, s.suffix)
    await enterSeededRequiredCourse(studentPageB, s.suffix)
    await studentPageA.goto('/homework')
    await studentPageB.goto('/homework')

    // Future intent:
    // 1. student tab A submits
    // 2. teacher reviews and closes the first summary
    // 3. stale tab B tries to resubmit or edit based on old state
    // 4. assert history converges to one valid current summary with no ghost duplicate
  })

  test.skip('2. teacher concurrent material chapter reorder from two tabs converges to one final chapter sequence', async ({ browser }) => {
    const s = scenario()
    const ctxA = await browser.newContext()
    const ctxB = await browser.newContext()
    const pageA = await ctxA.newPage()
    const pageB = await ctxB.newPage()

    await login(pageA, s.teacher_own.username, s.teacher_own.password)
    await login(pageB, s.teacher_own.username, s.teacher_own.password)
    await enterSeededRequiredCourse(pageA, s.suffix)
    await enterSeededRequiredCourse(pageB, s.suffix)
    await pageA.goto('/materials')
    await pageB.goto('/materials')

    // Future intent:
    // create 3 chapters, reorder differently in each tab, save out of order,
    // then assert API and UI both show only the last authoritative order.
  })

  test.skip('3. admin delete-class attempt blocked while related roster and course references still exist', async ({ page }) => {
    const s = scenario()
    await login(page, s.admin.username, s.admin.password)
    await page.goto('/classes')

    // Future intent:
    // attempt destructive class deletion against a seeded class with students and courses,
    // assert backend rejection, user-facing message, and no partial cleanup.
  })

  test.skip('4. teacher LLM endpoint failover during async grading leaves one completed task and no orphan queued rows', async ({ browser }) => {
    const s = scenario()
    const teacherToken = await obtainAccessToken(s.teacher_own.username, s.teacher_own.password)

    // Future intent:
    // patch endpoint preset order so first endpoint fails and second succeeds,
    // submit homework, wait for grading worker convergence,
    // verify one final grade candidate and zero stale processing rows.
    await apiGetJson(`/api/llm-settings/courses/${s.course_required_id}`, teacherToken)
  })

  test.skip('5. student dual-tab score appeal submit converges to one pending appeal and one notification chain', async ({ browser }) => {
    const s = scenario()
    const ctxA = await browser.newContext()
    const ctxB = await browser.newContext()
    const pageA = await ctxA.newPage()
    const pageB = await ctxB.newPage()

    await login(pageA, s.student_plain.username, s.student_plain.password)
    await login(pageB, s.student_plain.username, s.student_plain.password)
    await enterSeededRequiredCourse(pageA, s.suffix)
    await enterSeededRequiredCourse(pageB, s.suffix)
    await pageA.goto('/scores')
    await pageB.goto('/scores')

    // Future intent:
    // submit the same score appeal from both tabs within one stale window,
    // assert only one pending appeal remains and teacher sees one actionable item.
  })

  test.skip('6. admin batch user activation toggle with stale filters keeps final active-state set aligned with API truth', async ({ browser }) => {
    const s = scenario()
    const adminPage = await browser.newPage()
    await login(adminPage, s.admin.username, s.admin.password)
    await adminPage.goto('/users')

    // Future intent:
    // select rows under one filter, change filter before submit, batch-toggle active state,
    // assert only intended users changed and stale filtered rows were not incorrectly mutated.
  })

  test.skip('7. student notification deep-link recovery from corrupted local selected_course cache rebinds to accessible course only', async ({ page }) => {
    const s = scenario()
    await login(page, s.student_plain.username, s.student_plain.password)
    await page.evaluate(() => {
      localStorage.setItem('selected_course', JSON.stringify({ id: 987654321, name: 'corrupt-course' }))
    })
    await page.goto('/notifications')

    // Future intent:
    // navigate through course-scoped notification deep link with stale cache,
    // assert recovery selects a real accessible course and does not leak another course context.
  })

  test.skip('8. teacher concurrent homework max-submission edit and student submit keeps submission cap enforcement correct', async ({ browser }) => {
    const s = scenario()
    const teacherCtx = await browser.newContext()
    const studentCtx = await browser.newContext()
    const teacherPage = await teacherCtx.newPage()
    const studentPage = await studentCtx.newPage()

    await login(teacherPage, s.teacher_own.username, s.teacher_own.password)
    await login(studentPage, s.student_plain.username, s.student_plain.password)
    await enterSeededRequiredCourse(teacherPage, s.suffix)
    await enterSeededRequiredCourse(studentPage, s.suffix)
    await teacherPage.goto('/homework')
    await studentPage.goto('/homework')

    // Future intent:
    // student starts second submission while teacher lowers max submissions,
    // verify backend authoritative enforcement after race settles.
  })

  test.skip('9. parent portal notification read-state stays isolated from student web-admin read-state when policies require separation', async ({ browser }) => {
    const s = scenario()
    const adminToken = await obtainAccessToken(s.admin.username, s.admin.password)
    await apiListNotifications(adminToken, { page_size: 5 })

    // Future intent:
    // use parent portal and student portal in parallel against the same student-linked records,
    // assert either shared or isolated read-state based on product policy, with no accidental cross-user leakage.
  })

  test.skip('10. teacher duplicate attendance save retries produce one authoritative attendance row per student/date', async ({ page }) => {
    const s = scenario()
    await login(page, s.teacher_own.username, s.teacher_own.password)
    await enterSeededRequiredCourse(page, s.suffix)
    await page.goto('/attendance')

    // Future intent:
    // simulate transient failure during bulk attendance save,
    // retry from same form state, assert no duplicate attendance rows are created.
  })

  test.skip('11. admin semester switch plus score composition view stale tab converges to one valid grading composition', async ({ browser }) => {
    const s = scenario()
    const ctxA = await browser.newContext()
    const ctxB = await browser.newContext()
    const pageA = await ctxA.newPage()
    const pageB = await ctxB.newPage()

    await login(pageA, s.admin.username, s.admin.password)
    await login(pageB, s.admin.username, s.admin.password)
    await pageA.goto('/semesters')
    await pageB.goto('/scores')

    // Future intent:
    // switch active semester from one tab while another tab keeps a stale score composition screen,
    // then refresh and assert composition uses the final semester mapping without mixed data.
  })

  test.skip('12. teacher points award and redemption race leaves one consistent student point balance and ranking', async ({ browser }) => {
    const s = scenario()
    const teacherCtx = await browser.newContext()
    const studentCtx = await browser.newContext()
    const teacherPage = await teacherCtx.newPage()
    const studentPage = await studentCtx.newPage()

    await login(teacherPage, s.teacher_own.username, s.teacher_own.password)
    await login(studentPage, s.student_plain.username, s.student_plain.password)
    await teacherPage.goto('/points')
    await studentPage.goto('/points-display')

    // Future intent:
    // teacher awards points while student redeems, both from stale views,
    // assert final balance, ranking, and history rows converge without double-consume.
  })

  test.skip('13. student attachment replace during flaky upload leaves one surviving attachment reference and no orphan file row', async ({ page }) => {
    const s = scenario()
    const studentToken = await obtainAccessToken(s.student_plain.username, s.student_plain.password)
    await login(page, s.student_plain.username, s.student_plain.password)
    await enterSeededRequiredCourse(page, s.suffix)
    await page.goto('/homework')

    // Future intent:
    // simulate first attachment upload failure, then replace with second upload,
    // verify final submission references exactly one attachment and old partial upload is not left linked.
    await apiGetJson(`/api/homeworks/${s.homework_id}/submission/me/history`, studentToken)
  })

  test.skip('14. admin stale dual-tab system settings save converges to final branding and does not partially mix fields', async ({ browser }) => {
    const s = scenario()
    const pageA = await browser.newPage()
    const pageB = await browser.newPage()

    await login(pageA, s.admin.username, s.admin.password)
    await login(pageB, s.admin.username, s.admin.password)
    await pageA.goto('/settings')
    await pageB.goto('/settings')

    // Future intent:
    // tab B saves partial branding change first, tab A saves a different full change later,
    // assert final settings row is internally consistent and not a field-by-field mixture of both saves.
  })

  test.skip('15. teacher notification publish targeted to one student remains private across student, classmate, admin, and parent views', async ({ browser }) => {
    const s = scenario()
    const teacherToken = await obtainAccessToken(s.teacher_own.username, s.teacher_own.password)
    const adminToken = await obtainAccessToken(s.admin.username, s.admin.password)
    const uniqueTitle = `E2E_private_notification_${s.suffix}_${Date.now()}`

    await apiPostJson('/api/notifications', teacherToken, {
      title: uniqueTitle,
      content: 'private visibility coverage',
      priority: 'important',
      is_pinned: false,
      subject_id: s.course_required_id,
      student_ids: [s.student_plain.student_row_id]
    })

    // Future intent:
    // verify intended recipient sees it,
    // classmate does not see it,
    // admin sees operationally appropriate visibility,
    // parent-side behavior matches product privacy policy.
    await apiListNotifications(adminToken, { page_size: 100 })
  })
})
