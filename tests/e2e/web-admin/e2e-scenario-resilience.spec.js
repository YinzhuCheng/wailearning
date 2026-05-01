const { expect, test } = require('@playwright/test')
const { loadE2eScenario, resetE2eScenario, enterSeededRequiredCourse } = require('./fixtures.cjs')

const scenario = () => loadE2eScenario()

function apiBase() {
  return (process.env.E2E_API_URL || 'http://127.0.0.1:8012').replace(/\/$/, '')
}

function escapeRegex(text) {
  return `${text || ''}`.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

async function login(page, username, password) {
  await page.goto('/login', { waitUntil: 'load', timeout: 60000 })
  await page.evaluate(() => {
    try {
      localStorage.clear()
      sessionStorage.clear()
    } catch {
      /* ignore */
    }
  })
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

async function apiPutJson(pathname, token, body) {
  const res = await fetch(`${apiBase()}${pathname}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {})
    },
    body: JSON.stringify(body)
  })
  if (!res.ok) {
    throw new Error(`PUT ${pathname} failed ${res.status}: ${await res.text()}`)
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

async function apiDelete(pathname, token) {
  const res = await fetch(`${apiBase()}${pathname}`, {
    method: 'DELETE',
    headers: token ? { Authorization: `Bearer ${token}` } : {}
  })
  if (!res.ok) {
    throw new Error(`DELETE ${pathname} failed ${res.status}: ${await res.text()}`)
  }
  return res.json()
}

async function apiListHomeworkRows(token, subjectId) {
  const url = new URL(`${apiBase()}/api/homeworks`)
  url.searchParams.set('subject_id', String(subjectId))
  url.searchParams.set('page_size', '100')
  const res = await fetch(url.toString(), {
    headers: { Authorization: `Bearer ${token}` }
  })
  if (!res.ok) {
    throw new Error(`homeworks list failed ${res.status}: ${await res.text()}`)
  }
  const data = await res.json()
  return data.data || []
}

async function apiListCourseStudents(token, subjectId) {
  return apiGetJson(`/api/subjects/${subjectId}/students`, token)
}

async function apiGetCourseLlmConfig(token, subjectId) {
  return apiGetJson(`/api/llm-settings/courses/${subjectId}`, token)
}

async function apiListClasses(token) {
  return apiGetJson('/api/classes', token)
}

async function apiStudentCourseCatalog(token) {
  return apiGetJson('/api/subjects/course-catalog', token)
}

async function apiHomeworkSubmissionHistory(token, homeworkId) {
  return apiGetJson(`/api/homeworks/${homeworkId}/submission/me/history`, token)
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

async function apiListScoreAppeals(token, params = {}) {
  const url = new URL(`${apiBase()}/api/scores/appeals`)
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== '') {
      url.searchParams.set(key, String(value))
    }
  }
  const res = await fetch(url.toString(), {
    headers: { Authorization: `Bearer ${token}` }
  })
  if (!res.ok) {
    throw new Error(`score appeals list failed ${res.status}: ${await res.text()}`)
  }
  return res.json()
}

async function apiListUsers(token) {
  return apiGetJson('/api/users', token)
}

async function apiBatchSetClass(token, userIds, classId) {
  return apiPostJson('/api/users/batch-set-class', token, {
    user_ids: userIds,
    class_id: classId
  })
}

async function apiFindUserIdByUsername(token, username) {
  const users = await apiListUsers(token)
  const user = users.find(row => row.username === username)
  if (!user) {
    throw new Error(`user ${username} not found`)
  }
  return user.id
}

async function confirmPrimaryDialog(page) {
  const dialog = page.locator('.el-overlay .el-dialog').last()
  await expect(dialog).toBeVisible({ timeout: 15000 })
  const buttons = [
    page.getByRole('button', { name: /^(OK|确定|确认|保存|是)$/ }),
    dialog.getByRole('button', { name: /^(OK|确定|确认|保存|是)$/ })
  ]
  for (const button of buttons) {
    if (await button.count()) {
      await button.first().click()
      return
    }
  }
  throw new Error('No confirmation button found in active dialog')
}

async function currentSelectedCourseId(page) {
  return page.evaluate(() => {
    const raw = localStorage.getItem('selected_course')
    if (!raw) return null
    try {
      const parsed = JSON.parse(raw)
      return parsed?.id ?? null
    } catch {
      return null
    }
  })
}

function homeworkRow(page, title) {
  return page.getByRole('row', { name: new RegExp(escapeRegex(title)) })
}

function courseCard(page, courseName) {
  return page.locator('article.course-card').filter({
    has: page.getByRole('heading', { name: courseName })
  })
}

function courseCatalogRow(page, courseName) {
  return page.locator('tr').filter({ hasText: courseName }).first()
}

async function openHomeworkEditDialog(page, title) {
  const row = homeworkRow(page, title)
  await expect(row).toBeVisible({ timeout: 20000 })
  await row.getByTestId('homework-btn-edit').click()
  await expect(page.getByRole('dialog', { name: /发布作业|编辑作业/ })).toBeVisible({ timeout: 15000 })
}

async function clickCourseCatalogAction(page, courseName) {
  const row = courseCatalogRow(page, courseName)
  await expect(row).toBeVisible({ timeout: 20000 })
  const button = row.getByRole('button').first()
  await expect(button).toBeVisible({ timeout: 10000 })
  await button.click()
}

async function openRosterDialog(page, courseId) {
  await page.goto('/subjects')
  await page.getByTestId(`btn-roster-enroll-${courseId}`).click()
  await expect(page.getByTestId('dialog-roster-enroll')).toBeVisible({ timeout: 15000 })
}

async function selectRosterStudent(page, studentNo) {
  const row = page.locator(`[data-testid="table-roster-enroll-pick"] tr:has-text("${studentNo}")`)
  await expect(row).toBeVisible({ timeout: 15000 })
  await row.locator('.el-checkbox').first().click()
}

async function submitSeededHomeworkAndReview(browser, s, teacherToken, options = {}) {
  const reviewScore = options.reviewScore ?? 78
  const reviewComment = options.reviewComment ?? `E2E评阅_${s.suffix}_${Date.now()}`
  const content = options.content ?? `E2E提交_${s.suffix}_${Date.now()}`
  const studentToken = options.studentToken || await obtainAccessToken(s.student_plain.username, s.student_plain.password)
  await apiPostJson(`/api/homeworks/${s.homework_id}/submission`, studentToken, {
    content,
    attachment_name: null,
    attachment_url: null,
    remove_attachment: false,
    used_llm_assist: false,
    submission_mode: 'full'
  })
  await expect
    .poll(async () => {
      const history = await apiHomeworkSubmissionHistory(studentToken, s.homework_id)
      return history.summary?.id || null
    }, { timeout: 30000 })
    .not.toBeNull()

  const history = await apiHomeworkSubmissionHistory(studentToken, s.homework_id)
  const submissionId = history.summary?.id
  if (!submissionId) {
    throw new Error('submission summary not found')
  }
  await apiPutJson(`/api/homeworks/${s.homework_id}/submissions/${submissionId}/review`, teacherToken, {
    review_score: reviewScore,
    review_comment: reviewComment
  })
  return { submissionId, content, reviewScore, reviewComment }
}

test.describe('E2E resilience scenarios', () => {
  test.describe.configure({ timeout: 180_000 })

  test.beforeEach(async ({}, testInfo) => {
    const s = await resetE2eScenario()
    if (!s) {
      testInfo.skip(true, 'Missing e2e/.cache/scenario.json; run with Playwright globalSetup first')
    }
  })

  test('concurrent stale homework edit converges to one final state across teacher and student views', async ({ browser }) => {
    const s = scenario()
    const initialTitle = `E2E_UI作业_${s.suffix}`
    const intermediateTitle = `E2E并发中间态_${s.suffix}_${Date.now()}`
    const finalTitle = `E2E并发最终态_${s.suffix}_${Date.now()}`
    const teacherToken = await obtainAccessToken(s.teacher_own.username, s.teacher_own.password)

    const teacherA = await browser.newContext()
    const teacherB = await browser.newContext()
    const studentCtx = await browser.newContext()
    const pageA = await teacherA.newPage()
    const pageB = await teacherB.newPage()
    const studentPage = await studentCtx.newPage()

    try {
      await login(pageA, s.teacher_own.username, s.teacher_own.password)
      await login(pageB, s.teacher_own.username, s.teacher_own.password)

      await enterSeededRequiredCourse(pageA, s.suffix)
      await enterSeededRequiredCourse(pageB, s.suffix)
      await pageA.goto('/homework')
      await pageB.goto('/homework')

      await openHomeworkEditDialog(pageA, initialTitle)
      await pageA.getByTestId('homework-form-title').fill(finalTitle)

      await openHomeworkEditDialog(pageB, initialTitle)
      await pageB.getByTestId('homework-form-title').fill(intermediateTitle)
      await pageB.getByTestId('homework-form-save').click()
      await expect(pageB.getByRole('dialog', { name: /发布作业|编辑作业/ })).toBeHidden({ timeout: 25000 })
      await expect(homeworkRow(pageB, intermediateTitle)).toBeVisible({ timeout: 20000 })

      await pageA.getByTestId('homework-form-save').click()
      await expect(pageA.getByRole('dialog', { name: /发布作业|编辑作业/ })).toBeHidden({ timeout: 25000 })
      await expect(homeworkRow(pageA, finalTitle)).toBeVisible({ timeout: 20000 })

      await expect
        .poll(async () => {
          const rows = await apiListHomeworkRows(teacherToken, s.course_required_id)
          return {
            finalCount: rows.filter(row => row.title === finalTitle).length,
            intermediateCount: rows.filter(row => row.title === intermediateTitle).length,
            initialCount: rows.filter(row => row.title === initialTitle).length
          }
        }, { timeout: 30000 })
        .toEqual({ finalCount: 1, intermediateCount: 0, initialCount: 0 })

      await login(studentPage, s.student_plain.username, s.student_plain.password)
      await enterSeededRequiredCourse(studentPage, s.suffix)
      await studentPage.goto('/homework')
      await expect(homeworkRow(studentPage, finalTitle)).toBeVisible({ timeout: 20000 })
      await expect(homeworkRow(studentPage, intermediateTitle)).toHaveCount(0)
      await expect(homeworkRow(studentPage, initialTitle)).toHaveCount(0)
    } finally {
      await teacherA.close().catch(() => {})
      await teacherB.close().catch(() => {})
      await studentCtx.close().catch(() => {})
    }
  })

  test('retrying homework creation after API failure leaves one authoritative record', async ({ page }) => {
    const s = scenario()
    const teacherToken = await obtainAccessToken(s.teacher_own.username, s.teacher_own.password)
    const title = `E2E重试作业_${s.suffix}_${Date.now()}`
    const beforeRows = await apiListHomeworkRows(teacherToken, s.course_required_id)
    let failedOnce = false
    const baselineConfig = await apiGetCourseLlmConfig(teacherToken, s.course_required_id)

    await apiPutJson(`/api/llm-settings/courses/${s.course_required_id}`, teacherToken, {
      is_enabled: true,
      response_language: baselineConfig.response_language || null,
      quota_timezone: 'Asia/Shanghai',
      estimated_chars_per_token: baselineConfig.estimated_chars_per_token,
      estimated_image_tokens: baselineConfig.estimated_image_tokens,
      max_input_tokens: baselineConfig.max_input_tokens,
      max_output_tokens: baselineConfig.max_output_tokens,
      system_prompt: baselineConfig.system_prompt || '',
      teacher_prompt: baselineConfig.teacher_prompt || '',
      endpoints: baselineConfig.endpoints || [],
      groups: baselineConfig.groups || []
    })

    await login(page, s.teacher_own.username, s.teacher_own.password)
    await enterSeededRequiredCourse(page, s.suffix)
    await page.goto('/homework')

    await page.route('**/api/homeworks', async route => {
      const request = route.request()
      if (!failedOnce && request.method() === 'POST') {
        failedOnce = true
        await route.fulfill({
          status: 503,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'simulated create failure' })
        })
        return
      }
      await route.continue()
    })

    await page.getByTestId('homework-btn-create').click()
    await page.getByTestId('homework-form-title').fill(title)
    await page.getByTestId('homework-form-save').click()
    await expect(page.getByRole('dialog', { name: /发布作业/ })).toBeVisible({ timeout: 15000 })
    await expect(page.getByTestId('homework-form-save')).toBeEnabled({ timeout: 15000 })

    await page.getByTestId('homework-form-save').click()
    await expect(page.getByRole('dialog', { name: /发布作业/ })).toBeHidden({ timeout: 25000 })
    await expect(homeworkRow(page, title)).toBeVisible({ timeout: 20000 })

    const afterRows = await apiListHomeworkRows(teacherToken, s.course_required_id)
    const createdRows = afterRows.filter(row => row.title === title)
    expect(createdRows).toHaveLength(1)
    expect(afterRows).toHaveLength(beforeRows.length + 1)
  })

  test('student mid-session class migration invalidates stale course access and backend enrollment', async ({ browser }) => {
    const s = scenario()
    const adminToken = await obtainAccessToken(s.admin.username, s.admin.password)
    const studentToken = await obtainAccessToken(s.student_plain.username, s.student_plain.password)
    const studentUserId = await apiFindUserIdByUsername(adminToken, s.student_plain.username)
    const classes = await apiListClasses(adminToken)
    const class2 = classes.find(row => Number(row.id) === Number(s.class_id_2))
    if (!class2) {
      throw new Error(`class ${s.class_id_2} not found`)
    }

    const adminCtx = await browser.newContext()
    const studentCtx = await browser.newContext()
    const adminPage = await adminCtx.newPage()
    const studentPage = await studentCtx.newPage()
    const requiredCourseName = `E2E必修课_${s.suffix}`

    try {
      await login(studentPage, s.student_plain.username, s.student_plain.password)
      await studentPage.goto('/courses')
      await expect(courseCard(studentPage, requiredCourseName)).toBeVisible({ timeout: 20000 })

      await login(adminPage, s.admin.username, s.admin.password)
      await adminPage.goto('/users')
      const studentRow = adminPage.locator(`tr:has-text("${s.student_plain.username}")`)
      await expect(studentRow).toBeVisible({ timeout: 15000 })
      await studentRow.locator('.el-checkbox').first().click()
      await adminPage.getByTestId('users-open-batch-class').click()
      await expect(adminPage.getByTestId('dialog-batch-class')).toBeVisible({ timeout: 15000 })
      await adminPage.getByTestId('batch-class-target-select').click()
      await adminPage.getByRole('option', { name: class2.name }).click()
      await adminPage.getByTestId('batch-class-confirm').click()
      await confirmPrimaryDialog(adminPage)

      await expect
        .poll(async () => {
          const me = await apiGetJson('/api/auth/me', studentToken)
          const students = await apiListCourseStudents(adminToken, s.course_required_id)
          return {
            classId: Number(me.class_id || 0),
            stillEnrolled: students.some(row => Number(row.student_id) === Number(s.student_plain.student_row_id))
          }
        }, { timeout: 30000 })
        .toEqual({ classId: Number(s.class_id_2), stillEnrolled: false })

      await studentPage.goto('/courses')
      await studentPage.reload()
      await expect(courseCard(studentPage, requiredCourseName)).toHaveCount(0)
    } finally {
      await apiBatchSetClass(adminToken, [studentUserId], s.class_id_1).catch(() => {})
      await adminCtx.close().catch(() => {})
      await studentCtx.close().catch(() => {})
    }
  })

  test('stale roster dialog after class migration does not enroll the moved student into the old class course', async ({ browser }) => {
    const s = scenario()
    const adminToken = await obtainAccessToken(s.admin.username, s.admin.password)
    const studentUserId = await apiFindUserIdByUsername(adminToken, s.student_b.username)
    const classes = await apiListClasses(adminToken)
    const class2 = classes.find(row => Number(row.id) === Number(s.class_id_2))
    if (!class2) {
      throw new Error(`class ${s.class_id_2} not found`)
    }

    const page1Ctx = await browser.newContext()
    const page2Ctx = await browser.newContext()
    const page1 = await page1Ctx.newPage()
    const page2 = await page2Ctx.newPage()

    try {
      await login(page1, s.admin.username, s.admin.password)
      await login(page2, s.admin.username, s.admin.password)

      await openRosterDialog(page1, s.course_required_id)
      await selectRosterStudent(page1, s.student_b.username)

      await page2.goto('/users')
      const movedRow = page2.locator(`tr:has-text("${s.student_b.username}")`)
      await expect(movedRow).toBeVisible({ timeout: 15000 })
      await movedRow.locator('.el-checkbox').first().click()
      await apiBatchSetClass(adminToken, [studentUserId], s.class_id_2)

      await page1.getByTestId('btn-roster-enroll-submit').click()
      await expect(page1.getByTestId('dialog-roster-enroll')).toBeHidden({ timeout: 25000 })

      await expect
        .poll(async () => {
          const rows = await apiListCourseStudents(adminToken, s.course_required_id)
          return rows.filter(row => Number(row.student_id) === Number(s.student_b.student_row_id)).length
        }, { timeout: 30000 })
        .toBe(0)
    } finally {
      await apiBatchSetClass(adminToken, [studentUserId], s.class_id_1).catch(() => {})
      await page1Ctx.close().catch(() => {})
      await page2Ctx.close().catch(() => {})
    }
  })

  test('two student contexts self-enrolling the same elective remain idempotent and converge to one enrollment', async ({ browser }) => {
    const s = scenario()
    const adminToken = await obtainAccessToken(s.admin.username, s.admin.password)
    const studentToken = await obtainAccessToken(s.student_plain.username, s.student_plain.password)
    const electiveName = `E2E选修课_${s.suffix}`

    const ctxA = await browser.newContext()
    const ctxB = await browser.newContext()
    const pageA = await ctxA.newPage()
    const pageB = await ctxB.newPage()

    try {
      await login(pageA, s.student_plain.username, s.student_plain.password)
      await login(pageB, s.student_plain.username, s.student_plain.password)
      await pageA.goto('/courses')
      await pageB.goto('/courses')

      await clickCourseCatalogAction(pageA, electiveName)
      await clickCourseCatalogAction(pageB, electiveName)

      await expect
        .poll(async () => {
          const catalog = await apiStudentCourseCatalog(studentToken)
          const elective = catalog.find(row => Number(row.id) === Number(s.course_elective_id))
          const students = await apiListCourseStudents(adminToken, s.course_elective_id)
          return {
            enrolledInCatalog: Boolean(elective?.is_enrolled),
            enrollmentRows: students.filter(row => Number(row.student_id) === Number(s.student_plain.student_row_id)).length
          }
        }, { timeout: 30000 })
        .toEqual({
          enrolledInCatalog: true,
          enrollmentRows: 1
        })
    } finally {
      await ctxA.close().catch(() => {})
      await ctxB.close().catch(() => {})
    }
  })

  test('stale self-drop from two student contexts leaves the elective removed exactly once', async ({ browser }) => {
    const s = scenario()
    const adminToken = await obtainAccessToken(s.admin.username, s.admin.password)
    const studentToken = await obtainAccessToken(s.student_plain.username, s.student_plain.password)
    const electiveName = `E2E选修课_${s.suffix}`

    await apiPostJson(`/api/subjects/${s.course_elective_id}/student-self-enroll`, studentToken, {})

    const ctxA = await browser.newContext()
    const ctxB = await browser.newContext()
    const pageA = await ctxA.newPage()
    const pageB = await ctxB.newPage()

    try {
      await login(pageA, s.student_plain.username, s.student_plain.password)
      await login(pageB, s.student_plain.username, s.student_plain.password)
      await pageA.goto('/courses')
      await pageB.goto('/courses')

      await clickCourseCatalogAction(pageA, electiveName)
      await clickCourseCatalogAction(pageB, electiveName)

      await expect
        .poll(async () => {
          const catalog = await apiStudentCourseCatalog(studentToken)
          const elective = catalog.find(row => Number(row.id) === Number(s.course_elective_id))
          const students = await apiListCourseStudents(adminToken, s.course_elective_id)
          return {
            enrolledInCatalog: Boolean(elective?.is_enrolled),
            enrollmentRows: students.filter(row => Number(row.student_id) === Number(s.student_plain.student_row_id)).length
          }
        }, { timeout: 30000 })
        .toEqual({
          enrolledInCatalog: false,
          enrollmentRows: 0
        })
    } finally {
      await ctxA.close().catch(() => {})
      await ctxB.close().catch(() => {})
    }
  })

  test('profile save retries cleanly after API failure and persists one final display name', async ({ page }) => {
    const s = scenario()
    const studentToken = await obtainAccessToken(s.student_plain.username, s.student_plain.password)
    const newName = `E2E重试改名_${s.suffix}_${Date.now()}`
    let failedOnce = false

    await login(page, s.student_plain.username, s.student_plain.password)
    await page.route('**/api/auth/me', async route => {
      if (!failedOnce && route.request().method() === 'PATCH') {
        failedOnce = true
        await route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'simulated profile save failure' })
        })
        return
      }
      await route.continue()
    })

    await page.goto('/personal-settings')
    await page.getByTestId('personal-profile-real-name').fill(newName)
    await page.getByTestId('personal-profile-save').click()
    await expect(page.getByTestId('personal-profile-real-name')).toHaveValue(newName, { timeout: 15000 })
    await page.getByTestId('personal-profile-save').click()

    await expect
      .poll(async () => {
        const me = await apiGetJson('/api/auth/me', studentToken)
        return me.real_name
      }, { timeout: 30000 })
      .toBe(newName)
  })

  test('student submission retries after API failure and persists exactly one attempt', async ({ page }) => {
    const s = scenario()
    const studentToken = await obtainAccessToken(s.student_plain.username, s.student_plain.password)
    const content = `E2E重试提交_${s.suffix}_${Date.now()}`
    let failedOnce = false

    await login(page, s.student_plain.username, s.student_plain.password)
    await enterSeededRequiredCourse(page, s.suffix)
    await page.goto(`/homework/${s.homework_id}/submit`)

    await page.route(`**/api/homeworks/${s.homework_id}/submission`, async route => {
      if (!failedOnce && route.request().method() === 'POST') {
        failedOnce = true
        await route.fulfill({
          status: 504,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'simulated submission timeout' })
        })
        return
      }
      await route.continue()
    })

    await page.locator('textarea').first().fill(content)
    await page.getByRole('button', { name: /保存提交/ }).click()
    await expect(page.locator('textarea').first()).toHaveValue(content, { timeout: 15000 })
    await page.getByRole('button', { name: /保存提交/ }).click()

    await expect
      .poll(async () => {
        const history = await apiHomeworkSubmissionHistory(studentToken, s.homework_id)
        return {
          attempts: history.attempts.length,
          content: history.summary?.content || ''
        }
      }, { timeout: 30000 })
      .toEqual({
        attempts: 1,
        content
      })
  })

  test('duplicate appeal attempts from stale student pages collapse to one authoritative pending appeal', async ({ browser }) => {
    const s = scenario()
    const teacherToken = await obtainAccessToken(s.teacher_own.username, s.teacher_own.password)
    const studentToken = await obtainAccessToken(s.student_plain.username, s.student_plain.password)
    const submitContent = `E2E申诉提交_${s.suffix}_${Date.now()}`
    const appealText = `这是一条用于并发申诉去重验证的说明_${s.suffix}`

    const setupPageCtx = await browser.newContext()
    const setupPage = await setupPageCtx.newPage()
    try {
      await login(setupPage, s.student_plain.username, s.student_plain.password)
      await enterSeededRequiredCourse(setupPage, s.suffix)
      await setupPage.goto(`/homework/${s.homework_id}/submit`)
      await setupPage.locator('textarea').first().fill(submitContent)
      await setupPage.getByRole('button', { name: /保存提交/ }).click()
    } finally {
      await setupPageCtx.close().catch(() => {})
    }

    const history = await apiHomeworkSubmissionHistory(studentToken, s.homework_id)
    const submissionId = history.summary?.id
    if (!submissionId) {
      throw new Error('submission summary not found')
    }
    await apiPutJson(`/api/homeworks/${s.homework_id}/submissions/${submissionId}/review`, teacherToken, {
      review_score: 78,
      review_comment: `E2E申诉前评分_${s.suffix}`
    })

    const ctxA = await browser.newContext()
    const ctxB = await browser.newContext()
    const pageA = await ctxA.newPage()
    const pageB = await ctxB.newPage()

    try {
      await login(pageA, s.student_plain.username, s.student_plain.password)
      await login(pageB, s.student_plain.username, s.student_plain.password)
      await enterSeededRequiredCourse(pageA, s.suffix)
      await enterSeededRequiredCourse(pageB, s.suffix)
      await pageA.goto(`/homework/${s.homework_id}/submit`)
      await pageB.goto(`/homework/${s.homework_id}/submit`)

      await pageA.getByRole('button', { name: /申诉/ }).click()
      await pageA.locator('.el-dialog textarea').fill(appealText)
      await pageA.getByRole('button', { name: /提交申诉/ }).click()

      await pageB.getByRole('button', { name: /申诉/ }).click()
      await pageB.locator('.el-dialog textarea').fill(`${appealText}_重复`)
      await pageB.getByRole('button', { name: /提交申诉/ }).click()

      await expect
        .poll(async () => {
          const fresh = await apiHomeworkSubmissionHistory(studentToken, s.homework_id)
          return fresh.summary?.appeal_status || null
        }, { timeout: 30000 })
        .toBe('pending')
    } finally {
      await ctxA.close().catch(() => {})
      await ctxB.close().catch(() => {})
    }
  })

  test('course LLM config keeps default timezone and recovers cleanly after a failed save', async ({ page }) => {
    const s = scenario()
    const teacherToken = await obtainAccessToken(s.teacher_own.username, s.teacher_own.password)
    const courseName = `E2E必修课_${s.suffix}`
    let failedOnce = false

    await login(page, s.teacher_own.username, s.teacher_own.password)
    await page.goto('/subjects')

    const row = page.getByRole('row', { name: new RegExp(escapeRegex(courseName)) })
    await expect(row).toBeVisible({ timeout: 15000 })
    await row.getByRole('button', { name: /LLM/ }).click()

    const dialog = page.getByRole('dialog', { name: /LLM/ })
    await expect(dialog).toBeVisible({ timeout: 15000 })

    const timezoneInput = dialog
      .locator('.el-form-item')
      .filter({ has: page.getByText(/时区|quota_timezone|Asia\/Shanghai/) })
      .locator('input')
      .first()

    await expect(timezoneInput).toHaveValue('Asia/Shanghai', { timeout: 15000 })

    const enableSwitch = dialog.getByRole('switch')
    await expect(enableSwitch).toHaveAttribute('aria-checked', 'true', { timeout: 15000 })
    await expect(dialog.locator('.attachment-help')).toBeVisible({ timeout: 15000 })
    await timezoneInput.fill('')

    await page.route(`**/api/llm-settings/courses/${s.course_required_id}`, async route => {
      if (!failedOnce && route.request().method() === 'PUT') {
        failedOnce = true
        await route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'simulated llm save failure' })
        })
        return
      }
      await route.continue()
    })

    await dialog.getByRole('button', { name: /保存配置/ }).click()
    await expect(dialog).toBeVisible({ timeout: 15000 })
    await expect(timezoneInput).toHaveValue('', { timeout: 15000 })

    await dialog.getByRole('button', { name: /保存配置/ }).click()
    await expect(dialog).toBeHidden({ timeout: 25000 })

    await expect
      .poll(async () => {
        const config = await apiGetCourseLlmConfig(teacherToken, s.course_required_id)
        return {
          is_enabled: Boolean(config.is_enabled),
          quota_timezone: config.quota_timezone
        }
      }, { timeout: 30000 })
      .toEqual({
        is_enabled: true,
        quota_timezone: 'Asia/Shanghai'
      })
  })

  test('student deep-link to homework submit auto-selects course context after fresh login', async ({ page }) => {
    const s = scenario()

    await login(page, s.student_plain.username, s.student_plain.password)
    await page.goto(`/homework/${s.homework_id}/submit`)

    await expect(page).toHaveURL(new RegExp(`/homework/${s.homework_id}/submit$`))
    await expect(page.locator('textarea').first()).toBeVisible({ timeout: 20000 })
    await expect.poll(() => currentSelectedCourseId(page), { timeout: 15000 }).toBe(s.course_required_id)
  })

  test('student deep-link to student scores auto-selects course context after fresh login', async ({ page }) => {
    const s = scenario()

    await login(page, s.student_plain.username, s.student_plain.password)
    await page.goto('/student-scores')

    await expect(page).toHaveURL(/\/student-scores$/)
    await expect(page.getByRole('heading', { name: /鎴戠殑鎴愮哗|我的成绩/ })).toBeVisible({ timeout: 20000 })
    await expect(page.locator('textarea').first()).toBeVisible({ timeout: 20000 })
    await expect.poll(() => currentSelectedCourseId(page), { timeout: 15000 }).toBeTruthy()
  })

  test('student deep-link to notifications auto-selects course context after fresh login', async ({ page }) => {
    const s = scenario()

    await login(page, s.student_plain.username, s.student_plain.password)
    await page.goto('/notifications')

    await expect(page).toHaveURL(/\/notifications$/)
    await expect(page.getByRole('heading', { name: /閫氱煡涓績|通知中心/ })).toBeVisible({ timeout: 20000 })
    await expect.poll(() => currentSelectedCourseId(page), { timeout: 15000 }).toBeTruthy()
  })

  test('deep-link homework submit recovers from a stale invalid selected_course cache', async ({ page }) => {
    const s = scenario()

    await login(page, s.student_plain.username, s.student_plain.password)
    await page.evaluate(() => {
      localStorage.setItem('selected_course', JSON.stringify({ id: 999999, name: 'stale-course' }))
    })
    await page.goto(`/homework/${s.homework_id}/submit`)

    await expect(page).toHaveURL(new RegExp(`/homework/${s.homework_id}/submit$`))
    await expect(page.locator('textarea').first()).toBeVisible({ timeout: 20000 })
    await expect.poll(() => currentSelectedCourseId(page), { timeout: 15000 }).toBe(s.course_required_id)
  })

  test('concurrent duplicate homework appeal requests return one success and one conflict without a server error', async () => {
    const s = scenario()
    const teacherToken = await obtainAccessToken(s.teacher_own.username, s.teacher_own.password)
    const studentToken = await obtainAccessToken(s.student_b.username, s.student_b.password)
    const appealText = `E2E并发申诉_${s.suffix}_${Date.now()}`
    await apiPostJson(`/api/homeworks/${s.homework_id}/submission`, studentToken, {
      content: `E2E申诉前提交_${s.suffix}_${Date.now()}`,
      attachment_name: null,
      attachment_url: null,
      remove_attachment: false,
      used_llm_assist: false,
      submission_mode: 'full'
    })

    const history = await apiHomeworkSubmissionHistory(studentToken, s.homework_id)
    const submissionId = history.summary?.id
    if (!submissionId) {
      throw new Error('submission summary not found')
    }
    await apiPutJson(`/api/homeworks/${s.homework_id}/submissions/${submissionId}/review`, teacherToken, {
      review_score: 84,
      review_comment: `E2E并发申诉前评阅_${s.suffix}`
    })

    const results = await Promise.all([
      fetch(`${apiBase()}/api/homeworks/${s.homework_id}/submissions/${submissionId}/appeal`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${studentToken}`
        },
        body: JSON.stringify({ reason_text: appealText })
      }),
      fetch(`${apiBase()}/api/homeworks/${s.homework_id}/submissions/${submissionId}/appeal`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${studentToken}`
        },
        body: JSON.stringify({ reason_text: `${appealText}_duplicate` })
      })
    ])
    const statuses = results.map(resp => resp.status).sort((a, b) => a - b)
    expect(statuses).toEqual([200, 400])

    await expect
      .poll(async () => {
        const history = await apiHomeworkSubmissionHistory(studentToken, s.homework_id)
        const notifications = await apiListNotifications(teacherToken, { subject_id: s.course_required_id, page_size: 100 })
        return {
          appealStatus: history.summary?.appeal_status || null,
          matchingNotifications: (notifications.data || []).filter(row =>
            row.notification_kind === 'grade_appeal' &&
            Number(row.related_homework_id) === Number(s.homework_id) &&
            Number(row.related_student_id) === Number(s.student_b.student_row_id)
          ).length
        }
      }, { timeout: 30000 })
      .toEqual({
        appealStatus: 'pending',
        matchingNotifications: 1
      })
  })

  test('student deep-link to homework list auto-selects course context after fresh login', async ({ page }) => {
    const s = scenario()

    await login(page, s.student_plain.username, s.student_plain.password)
    await page.goto('/homework')

    await expect(page).toHaveURL(/\/homework$/)
    await expect(page.getByRole('heading', { name: /浣滀笟绠＄悊|课程作业|作业/ })).toBeVisible({ timeout: 20000 })
    await expect.poll(() => currentSelectedCourseId(page), { timeout: 15000 }).toBe(s.course_required_id)
  })

  test('student deep-link to notifications recovers from a stale invalid selected_course cache', async ({ page }) => {
    const s = scenario()

    await login(page, s.student_plain.username, s.student_plain.password)
    await page.evaluate(() => {
      localStorage.setItem('selected_course', JSON.stringify({ id: 999999, name: 'stale-course' }))
    })
    await page.goto('/notifications')

    await expect(page).toHaveURL(/\/notifications$/)
    await expect(page.getByRole('heading', { name: /閫氱煡涓績|通知中心/ })).toBeVisible({ timeout: 20000 })
    await expect.poll(() => currentSelectedCourseId(page), { timeout: 15000 }).toBeTruthy()
  })

  test('concurrent score appeal requests create at most one pending row for the same component', async () => {
    const s = scenario()
    const teacherToken = await obtainAccessToken(s.teacher_own.username, s.teacher_own.password)
    const reasonText = `E2E成绩申诉_${s.suffix}_${Date.now()}`
    const studentToken = await obtainAccessToken(s.student_plain.username, s.student_plain.password)
    const payloadA = {
      semester: '2026-秋季',
      target_component: 'total',
      reason_text: reasonText,
      score_id: null
    }
    const payloadB = {
      semester: '2026-秋季',
      target_component: 'total',
      reason_text: `${reasonText}_duplicate`,
      score_id: null
    }

    const responses = await Promise.all([
      fetch(`${apiBase()}/api/scores/appeals?subject_id=${s.course_required_id}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${studentToken}`
        },
        body: JSON.stringify(payloadA)
      }),
      fetch(`${apiBase()}/api/scores/appeals?subject_id=${s.course_required_id}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${studentToken}`
        },
        body: JSON.stringify(payloadB)
      })
    ])
    const statuses = responses.map(resp => resp.status).sort((a, b) => a - b)
    expect(statuses).toEqual([200, 400])

    await expect
      .poll(async () => {
        const rows = await apiListScoreAppeals(teacherToken, {
          subject_id: s.course_required_id,
          status: 'pending'
        })
        return rows.filter(row =>
          Number(row.subject_id) === Number(s.course_required_id) &&
          row.target_component === 'total' &&
          String(row.reason_text || '').startsWith(reasonText)
        ).length
      }, { timeout: 30000 })
      .toBe(1)
  })

  test('teacher notifications contain one score-appeal row after duplicate concurrent score appeals', async () => {
    const s = scenario()
    const teacherToken = await obtainAccessToken(s.teacher_own.username, s.teacher_own.password)
    const reasonText = `E2E成绩通知_${s.suffix}_${Date.now()}`
    const studentToken = await obtainAccessToken(s.student_plain.username, s.student_plain.password)
    await Promise.all([
      fetch(`${apiBase()}/api/scores/appeals?subject_id=${s.course_required_id}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${studentToken}`
        },
        body: JSON.stringify({
          semester: '2026-秋季',
          target_component: 'homework_avg',
          reason_text: reasonText,
          score_id: null
        })
      }),
      fetch(`${apiBase()}/api/scores/appeals?subject_id=${s.course_required_id}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${studentToken}`
        },
        body: JSON.stringify({
          semester: '2026-秋季',
          target_component: 'homework_avg',
          reason_text: `${reasonText}_duplicate`,
          score_id: null
        })
      })
    ])

    await expect
      .poll(async () => {
        const notifications = await apiListNotifications(teacherToken, { subject_id: s.course_required_id, page_size: 100 })
        return (notifications.data || []).filter(row =>
          row.notification_kind === 'score_grade_appeal' &&
          Number(row.subject_id) === Number(s.course_required_id) &&
          Number(row.related_student_id) === Number(s.student_plain.student_row_id) &&
          String(row.content || '').includes(reasonText)
        ).length
      }, { timeout: 30000 })
      .toBe(1)
  })

  test('student deep-link to student scores recovers from a stale invalid selected_course cache', async ({ page }) => {
    const s = scenario()

    await login(page, s.student_plain.username, s.student_plain.password)
    await page.evaluate(() => {
      localStorage.setItem('selected_course', JSON.stringify({ id: 999999, name: 'stale-course' }))
    })
    await page.goto('/student-scores')

    await expect(page).toHaveURL(/\/student-scores$/)
    await expect(page.locator('textarea').first()).toBeVisible({ timeout: 20000 })
    await expect.poll(() => currentSelectedCourseId(page), { timeout: 15000 }).toBeTruthy()
  })

  test('duplicate stale teacher roster-enroll submits create one authoritative elective enrollment', async ({ browser }) => {
    const s = scenario()
    const teacherToken = await obtainAccessToken(s.teacher_own.username, s.teacher_own.password)
    const electiveName = `E2E选修课_${s.suffix}`

    await apiDelete(`/api/subjects/${s.course_elective_id}/students/${s.student_b.student_row_id}`, teacherToken).catch(() => {})

    const ctxA = await browser.newContext()
    const ctxB = await browser.newContext()
    const pageA = await ctxA.newPage()
    const pageB = await ctxB.newPage()

    try {
      await login(pageA, s.teacher_own.username, s.teacher_own.password)
      await login(pageB, s.teacher_own.username, s.teacher_own.password)

      await openRosterDialog(pageA, s.course_elective_id)
      await openRosterDialog(pageB, s.course_elective_id)
      await selectRosterStudent(pageA, s.student_b.username)
      await selectRosterStudent(pageB, s.student_b.username)

      await Promise.all([
        pageA.getByTestId('btn-roster-enroll-submit').click(),
        pageB.getByTestId('btn-roster-enroll-submit').click()
      ])

      await expect
        .poll(async () => {
          const rows = await apiListCourseStudents(teacherToken, s.course_elective_id)
          return rows.filter(row => Number(row.student_id) === Number(s.student_b.student_row_id)).length
        }, { timeout: 30000 })
        .toBe(1)

      await pageA.goto('/subjects')
      await expect(pageA.getByRole('row', { name: new RegExp(escapeRegex(electiveName)) })).toBeVisible({ timeout: 15000 })
    } finally {
      await apiDelete(`/api/subjects/${s.course_elective_id}/students/${s.student_b.student_row_id}`, teacherToken).catch(() => {})
      await ctxA.close().catch(() => {})
      await ctxB.close().catch(() => {})
    }
  })

  test('concurrent stale student elective drops converge to one final unenrolled state', async ({ browser }) => {
    const s = scenario()
    const studentToken = await obtainAccessToken(s.student_plain.username, s.student_plain.password)
    const teacherToken = await obtainAccessToken(s.teacher_own.username, s.teacher_own.password)
    const electiveName = `E2E选修课_${s.suffix}`

    await apiPostJson(`/api/subjects/${s.course_elective_id}/student-self-enroll`, studentToken, {}).catch(() => {})

    const ctxA = await browser.newContext()
    const ctxB = await browser.newContext()
    const pageA = await ctxA.newPage()
    const pageB = await ctxB.newPage()

    try {
      await login(pageA, s.student_plain.username, s.student_plain.password)
      await login(pageB, s.student_plain.username, s.student_plain.password)
      await pageA.goto('/courses')
      await pageB.goto('/courses')

      await Promise.all([
        clickCourseCatalogAction(pageA, electiveName),
        clickCourseCatalogAction(pageB, electiveName)
      ])

      await expect
        .poll(async () => {
          const rows = await apiListCourseStudents(teacherToken, s.course_elective_id)
          const catalog = await apiStudentCourseCatalog(studentToken)
          const elective = catalog.find(row => Number(row.id) === Number(s.course_elective_id))
          return {
            enrollments: rows.filter(row => Number(row.student_id) === Number(s.student_plain.student_row_id)).length,
            isEnrolled: Boolean(elective?.is_enrolled)
          }
        }, { timeout: 30000 })
        .toEqual({
          enrollments: 0,
          isEnrolled: false
        })
    } finally {
      await ctxA.close().catch(() => {})
      await ctxB.close().catch(() => {})
    }
  })

  test('stale student elective page rejects self-enroll after admin migrates the student to another class', async ({ browser }) => {
    const s = scenario()
    const adminToken = await obtainAccessToken(s.admin.username, s.admin.password)
    const teacherToken = await obtainAccessToken(s.teacher_own.username, s.teacher_own.password)
    const studentToken = await obtainAccessToken(s.student_b.username, s.student_b.password)
    const studentUserId = await apiFindUserIdByUsername(adminToken, s.student_b.username)
    const classes = await apiListClasses(adminToken)
    const class2 = classes.find(row => Number(row.id) === Number(s.class_id_2))
    const electiveName = `E2E选修课_${s.suffix}`
    if (!class2) {
      throw new Error(`class ${s.class_id_2} not found`)
    }

    await apiDelete(`/api/subjects/${s.course_elective_id}/students/${s.student_b.student_row_id}`, teacherToken).catch(() => {})

    const adminCtx = await browser.newContext()
    const studentCtx = await browser.newContext()
    const adminPage = await adminCtx.newPage()
    const studentPage = await studentCtx.newPage()

    try {
      await login(studentPage, s.student_b.username, s.student_b.password)
      await studentPage.goto('/courses')
      await expect(courseCatalogRow(studentPage, electiveName)).toBeVisible({ timeout: 20000 })

      await login(adminPage, s.admin.username, s.admin.password)
      await adminPage.goto('/users')
      const studentRow = adminPage.locator(`tr:has-text("${s.student_b.username}")`)
      await expect(studentRow).toBeVisible({ timeout: 15000 })
      await studentRow.locator('.el-checkbox').first().click()
      await adminPage.getByTestId('users-open-batch-class').click()
      await adminPage.getByTestId('batch-class-target-select').click()
      await adminPage.getByRole('option', { name: class2.name }).click()
      await adminPage.getByTestId('batch-class-confirm').click()
      await confirmPrimaryDialog(adminPage)

      await clickCourseCatalogAction(studentPage, electiveName)

      await expect
        .poll(async () => {
          const me = await apiGetJson('/api/auth/me', studentToken)
          const rows = await apiListCourseStudents(teacherToken, s.course_elective_id)
          return {
            classId: Number(me.class_id || 0),
            enrollments: rows.filter(row => Number(row.student_id) === Number(s.student_b.student_row_id)).length
          }
        }, { timeout: 30000 })
        .toEqual({
          classId: Number(s.class_id_2),
          enrollments: 0
        })
    } finally {
      await apiBatchSetClass(adminToken, [studentUserId], s.class_id_1).catch(() => {})
      await apiDelete(`/api/subjects/${s.course_elective_id}/students/${s.student_b.student_row_id}`, teacherToken).catch(() => {})
      await adminCtx.close().catch(() => {})
      await studentCtx.close().catch(() => {})
    }
  })

  test('opening the same fresh notification from two stale student tabs converges to a single read state', async ({ browser }) => {
    const s = scenario()
    const teacherToken = await obtainAccessToken(s.teacher_own.username, s.teacher_own.password)
    const studentToken = await obtainAccessToken(s.student_plain.username, s.student_plain.password)
    const title = `E2E通知双开已读_${s.suffix}_${Date.now()}`

    await apiPostJson('/api/notifications', teacherToken, {
      title,
      content: 'parallel read convergence',
      priority: 'important',
      is_pinned: false,
      class_id: s.class_id_1,
      subject_id: s.course_required_id
    })

    const ctxA = await browser.newContext()
    const ctxB = await browser.newContext()
    const pageA = await ctxA.newPage()
    const pageB = await ctxB.newPage()

    try {
      await login(pageA, s.student_plain.username, s.student_plain.password)
      await login(pageB, s.student_plain.username, s.student_plain.password)
      await enterSeededRequiredCourse(pageA, s.suffix)
      await enterSeededRequiredCourse(pageB, s.suffix)
      await pageA.goto('/notifications')
      await pageB.goto('/notifications')

      const rowA = pageA.locator('tr').filter({ hasText: title }).first()
      const rowB = pageB.locator('tr').filter({ hasText: title }).first()
      await expect(rowA).toBeVisible({ timeout: 20000 })
      await expect(rowB).toBeVisible({ timeout: 20000 })

      await Promise.all([rowA.click(), rowB.click()])

      await expect
        .poll(async () => {
          const list = await apiListNotifications(studentToken, { subject_id: s.course_required_id, page_size: 100 })
          const match = (list.data || []).find(row => row.title === title)
          return Boolean(match?.is_read)
        }, { timeout: 30000 })
        .toBe(true)
    } finally {
      await ctxA.close().catch(() => {})
      await ctxB.close().catch(() => {})
    }
  })

  test('dual-tab student mark-all-read leaves every fresh course notification read', async ({ browser }) => {
    const s = scenario()
    const teacherToken = await obtainAccessToken(s.teacher_own.username, s.teacher_own.password)
    const studentToken = await obtainAccessToken(s.student_plain.username, s.student_plain.password)
    const titles = [
      `E2E通知批量已读A_${s.suffix}_${Date.now()}`,
      `E2E通知批量已读B_${s.suffix}_${Date.now()}`
    ]

    for (const title of titles) {
      await apiPostJson('/api/notifications', teacherToken, {
        title,
        content: 'mark-all-read convergence',
        priority: 'normal',
        is_pinned: false,
        class_id: s.class_id_1,
        subject_id: s.course_required_id
      })
    }

    const ctxA = await browser.newContext()
    const ctxB = await browser.newContext()
    const pageA = await ctxA.newPage()
    const pageB = await ctxB.newPage()

    try {
      await login(pageA, s.student_plain.username, s.student_plain.password)
      await login(pageB, s.student_plain.username, s.student_plain.password)
      await enterSeededRequiredCourse(pageA, s.suffix)
      await enterSeededRequiredCourse(pageB, s.suffix)
      await pageA.goto('/notifications')
      await pageB.goto('/notifications')

      await Promise.all([
        pageA.getByRole('button', { name: /已读/ }).click(),
        pageB.getByRole('button', { name: /已读/ }).click()
      ])

      await expect
        .poll(async () => {
          const list = await apiListNotifications(studentToken, { subject_id: s.course_required_id, page_size: 100 })
          return titles.map(title => {
            const row = (list.data || []).find(item => item.title === title)
            return Boolean(row?.is_read)
          })
        }, { timeout: 30000 })
        .toEqual([true, true])
    } finally {
      await ctxA.close().catch(() => {})
      await ctxB.close().catch(() => {})
    }
  })

  test('profile save retries after a transient failure and persists one final display name', async ({ page }) => {
    const s = scenario()
    const studentToken = await obtainAccessToken(s.student_plain.username, s.student_plain.password)
    const originalName = (await apiGetJson('/api/auth/me', studentToken)).real_name
    const nextName = `E2E改名重试_${s.suffix}_${Date.now()}`
    let failedOnce = false

    try {
      await login(page, s.student_plain.username, s.student_plain.password)
      await page.goto('/personal-settings')

      await page.route('**/api/auth/me', async route => {
        if (!failedOnce && route.request().method() === 'PATCH') {
          failedOnce = true
          await route.fulfill({
            status: 503,
            contentType: 'application/json',
            body: JSON.stringify({ detail: 'simulated profile save failure' })
          })
          return
        }
        await route.continue()
      })

      await page.getByTestId('personal-profile-real-name').fill(nextName)
      await page.getByTestId('personal-profile-save').click()
      await expect(page.getByTestId('personal-profile-real-name')).toHaveValue(nextName, { timeout: 15000 })
      await page.getByTestId('personal-profile-save').click()

      await expect
        .poll(async () => (await apiGetJson('/api/auth/me', studentToken)).real_name, { timeout: 30000 })
        .toBe(nextName)
    } finally {
      await apiPatchJson('/api/auth/me', studentToken, { real_name: originalName }).catch(() => {})
    }
  })

  test('stale dual-tab profile saves converge to the last submitted display name', async ({ browser }) => {
    const s = scenario()
    const studentToken = await obtainAccessToken(s.student_plain.username, s.student_plain.password)
    const originalName = (await apiGetJson('/api/auth/me', studentToken)).real_name
    const intermediateName = `E2E个人设置中间态_${s.suffix}_${Date.now()}`
    const finalName = `E2E个人设置最终态_${s.suffix}_${Date.now()}`

    const ctxA = await browser.newContext()
    const ctxB = await browser.newContext()
    const pageA = await ctxA.newPage()
    const pageB = await ctxB.newPage()

    try {
      await login(pageA, s.student_plain.username, s.student_plain.password)
      await login(pageB, s.student_plain.username, s.student_plain.password)
      await pageA.goto('/personal-settings')
      await pageB.goto('/personal-settings')

      await pageA.getByTestId('personal-profile-real-name').fill(finalName)
      await pageB.getByTestId('personal-profile-real-name').fill(intermediateName)
      await pageB.getByTestId('personal-profile-save').click()
      await pageA.getByTestId('personal-profile-save').click()

      await expect
        .poll(async () => (await apiGetJson('/api/auth/me', studentToken)).real_name, { timeout: 30000 })
        .toBe(finalName)
    } finally {
      await apiPatchJson('/api/auth/me', studentToken, { real_name: originalName }).catch(() => {})
      await ctxA.close().catch(() => {})
      await ctxB.close().catch(() => {})
    }
  })

  test('password change can recover from a wrong-current-password attempt and invalidates the old password', async ({ page }) => {
    const s = scenario()
    const nextPassword = `TempPass_${Date.now()}!`

    try {
      await login(page, s.student_plain.username, s.student_plain.password)
      await page.goto('/personal-settings')

      const passwordInputs = page.locator('input[type="password"]')
      await passwordInputs.nth(0).fill('definitely-wrong-password')
      await passwordInputs.nth(1).fill(nextPassword)
      await passwordInputs.nth(2).fill(nextPassword)
      await page.getByRole('button', { name: /密码/ }).click()

      await passwordInputs.nth(0).fill(s.student_plain.password)
      await passwordInputs.nth(1).fill(nextPassword)
      await passwordInputs.nth(2).fill(nextPassword)
      await page.getByRole('button', { name: /密码/ }).click()

      await expect
        .poll(async () => {
          try {
            await obtainAccessToken(s.student_plain.username, s.student_plain.password)
            return 'old-still-valid'
          } catch {
            await obtainAccessToken(s.student_plain.username, nextPassword)
            return 'new-only'
          }
        }, { timeout: 30000 })
        .toBe('new-only')
    } finally {
      const newToken = await obtainAccessToken(s.student_plain.username, nextPassword).catch(() => null)
      if (newToken) {
        await apiPostJson('/api/auth/change-password', newToken, {
          current_password: nextPassword,
          new_password: s.student_plain.password,
          confirm_password: s.student_plain.password
        }).catch(() => {})
      }
    }
  })

  test('retrying notification publish after API failure leaves one authoritative notification row', async ({ page }) => {
    const s = scenario()
    const teacherToken = await obtainAccessToken(s.teacher_own.username, s.teacher_own.password)
    const title = `E2E通知重试_${s.suffix}_${Date.now()}`
    let failedOnce = false

    await login(page, s.teacher_own.username, s.teacher_own.password)
    await enterSeededRequiredCourse(page, s.suffix)
    await page.goto('/notifications')

    await page.route('**/api/notifications', async route => {
      const request = route.request()
      if (!failedOnce && request.method() === 'POST') {
        failedOnce = true
        await route.fulfill({
          status: 503,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'simulated notification create failure' })
        })
        return
      }
      await route.continue()
    })

    await page.getByRole('button', { name: /发布/ }).click()
    const dialog = page.getByRole('dialog')
    await expect(dialog).toBeVisible({ timeout: 15000 })
    await dialog.locator('input').first().fill(title)
    await dialog.locator('textarea').first().fill('notification retry convergence')
    await dialog.getByRole('button', { name: /保存/ }).click()
    await expect(dialog).toBeVisible({ timeout: 15000 })
    await dialog.getByRole('button', { name: /保存/ }).click()
    await expect(dialog).toBeHidden({ timeout: 25000 })

    await expect
      .poll(async () => {
        const list = await apiListNotifications(teacherToken, { subject_id: s.course_required_id, page_size: 100 })
        return (list.data || []).filter(row => row.title === title).length
      }, { timeout: 30000 })
      .toBe(1)
  })

  test('opening notifications after a stale selected_course cache still preserves fresh read state after mark-all-read', async ({ page }) => {
    const s = scenario()
    const teacherToken = await obtainAccessToken(s.teacher_own.username, s.teacher_own.password)
    const studentToken = await obtainAccessToken(s.student_plain.username, s.student_plain.password)
    const title = `E2E通知脏缓存已读_${s.suffix}_${Date.now()}`

    await apiPostJson('/api/notifications', teacherToken, {
      title,
      content: 'stale selected course recovery',
      priority: 'normal',
      is_pinned: false,
      class_id: s.class_id_1,
      subject_id: s.course_required_id
    })

    await login(page, s.student_plain.username, s.student_plain.password)
    await page.evaluate(() => {
      localStorage.setItem('selected_course', JSON.stringify({ id: 999999, name: 'stale-course' }))
    })
    await page.goto('/notifications')
    await expect.poll(() => currentSelectedCourseId(page), { timeout: 15000 }).toBeTruthy()
    await page.getByRole('button', { name: /已读/ }).click()

    await expect
      .poll(async () => {
        const list = await apiListNotifications(studentToken, { subject_id: s.course_required_id, page_size: 100 })
        const row = (list.data || []).find(item => item.title === title)
        return Boolean(row?.is_read)
      }, { timeout: 30000 })
      .toBe(true)
  })

  test('admin stale batch-class flip-flop converges to the last move and restores the student course access', async ({ browser }) => {
    const s = scenario()
    const adminToken = await obtainAccessToken(s.admin.username, s.admin.password)
    const studentToken = await obtainAccessToken(s.student_plain.username, s.student_plain.password)
    const studentUserId = await apiFindUserIdByUsername(adminToken, s.student_plain.username)
    const classes = await apiListClasses(adminToken)
    const class1 = classes.find(row => Number(row.id) === Number(s.class_id_1))
    const class2 = classes.find(row => Number(row.id) === Number(s.class_id_2))
    if (!class1 || !class2) {
      throw new Error('expected seed classes not found')
    }

    const ctxA = await browser.newContext()
    const ctxB = await browser.newContext()
    const studentCtx = await browser.newContext()
    const pageA = await ctxA.newPage()
    const pageB = await ctxB.newPage()
    const studentPage = await studentCtx.newPage()
    const requiredCourseName = `E2E必修课_${s.suffix}`

    try {
      await login(pageA, s.admin.username, s.admin.password)
      await login(pageB, s.admin.username, s.admin.password)
      await login(studentPage, s.student_plain.username, s.student_plain.password)

      await pageA.goto('/users')
      await pageB.goto('/users')

      const rowA = pageA.locator(`tr:has-text("${s.student_plain.username}")`)
      const rowB = pageB.locator(`tr:has-text("${s.student_plain.username}")`)
      await expect(rowA).toBeVisible({ timeout: 15000 })
      await expect(rowB).toBeVisible({ timeout: 15000 })
      await rowA.locator('.el-checkbox').first().click()
      await rowB.locator('.el-checkbox').first().click()

      await pageA.getByTestId('users-open-batch-class').click()
      await pageA.getByTestId('batch-class-target-select').click()
      await pageA.getByRole('option', { name: class2.name }).click()
      await pageA.getByTestId('batch-class-confirm').click()
      await confirmPrimaryDialog(pageA)

      await apiBatchSetClass(adminToken, [studentUserId], s.class_id_1)

      await expect
        .poll(async () => {
          const me = await apiGetJson('/api/auth/me', studentToken)
          const catalog = await apiStudentCourseCatalog(studentToken)
          return {
            classId: Number(me.class_id || 0),
            requiredVisible: catalog.some(row => Number(row.id) === Number(s.course_required_id))
          }
        }, { timeout: 30000 })
        .toEqual({
          classId: Number(s.class_id_1),
          requiredVisible: true
        })

      await studentPage.goto('/courses')
      await expect(courseCatalogRow(studentPage, requiredCourseName)).toBeVisible({ timeout: 20000 })
    } finally {
      await apiBatchSetClass(adminToken, [studentUserId], s.class_id_1).catch(() => {})
      await ctxA.close().catch(() => {})
      await ctxB.close().catch(() => {})
      await studentCtx.close().catch(() => {})
    }
  })
})
