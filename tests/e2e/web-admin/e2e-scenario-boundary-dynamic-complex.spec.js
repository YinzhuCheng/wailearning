/**
 * Scenario-style Playwright tests: boundary (cold start / CRUD), dynamic (mutations visible end-to-end),
 * complex (multi-step, multi-role, optional API audit).
 *
 * Relies on globalSetup -> e2e/.cache/scenario.json (same as other e2e specs).
 */
const { expect, test } = require('@playwright/test')
const { loadE2eScenario, resetE2eScenario, enterSeededRequiredCourse } = require('./fixtures.cjs')

const scenario = () => loadE2eScenario()

function apiBase() {
  return (process.env.E2E_API_URL || 'http://127.0.0.1:8012').replace(/\/$/, '')
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

async function login(page, username, password) {
  await page.goto('/login', { waitUntil: 'load', timeout: 60000 })
  await page.evaluate(() => {
    try {
      localStorage.clear()
      sessionStorage.clear()
    } catch {
      /* ignore opaque origins */
    }
  })
  await expect(page.getByTestId('login-username')).toBeVisible({ timeout: 60000 })
  await page.getByTestId('login-username').fill(username)
  await page.getByTestId('login-password').fill(password)
  await page.getByTestId('login-submit').click()
  await page.waitForURL(url => !url.pathname.includes('/login'), { timeout: 20000 })
}

/** Teacher dropdown may list duplicate real_name labels; pick first matching option. */
async function pickTeacherOption(page, realName) {
  await page.getByRole('option', { name: realName }).first().click()
}

async function clickSelectOptionByLabel(page, labelText) {
  const dd = page.locator('.el-select-dropdown').last()
  await dd.waitFor({ state: 'visible', timeout: 25000 })
  const inp = dd.locator('input').first()
  try {
    await inp.fill(labelText, { timeout: 5000 })
    await new Promise(r => setTimeout(r, 250))
  } catch {
    /* non-filterable or input not in dropdown */
  }
  await dd.locator('.el-select-dropdown__item').filter({ hasText: labelText }).first().click({ timeout: 60000 })
}

/** Course form validation requires start/end dates on the first time block. */
async function fillCourseDialogDateRange(page) {
  const dlg = page.getByRole('dialog', { name: /新建课程|编辑课程/ })
  await dlg.getByPlaceholder('请选择开始日期').first().fill('2026-01-15')
  await dlg.getByPlaceholder('请选择结束日期').first().fill('2026-06-30')
}

async function confirmMessageBox(page) {
  // Element Plus MessageBox: title "删除课程" may not map to the dialog accessible name in all locales;
  // target the overlay dialog that exposes the confirm button (see TEST_EXECUTION_PITFALLS.md).
  const dlg = page.getByRole('dialog').filter({ has: page.getByRole('button', { name: /^(确定|OK)$/ }) })
  await dlg.getByRole('button', { name: /^(确定|OK)$/ }).click({ force: true })
}

/** Element Plus: click `.el-select` in an open dialog by matching label text on the form row (label may include required markers). */
async function openDialogSelectIn(dialogLocator, labelSubstring) {
  const row = dialogLocator.locator('.el-form-item').filter({ hasText: labelSubstring })
  const trigger = row.locator('.el-select .el-select__wrapper, .el-select').first()
  await trigger.click({ force: true })
}

/** Same as `openDialogSelectIn`, scoped by dialog accessible name (course dialogs use regex titles). */
async function openDialogSelectByLabel(page, labelText, dialogName) {
  const dlg = page.getByRole('dialog', { name: dialogName })
  await openDialogSelectIn(dlg, labelText)
}

async function apiCourseExistsForTeacher(token, courseNameSubstring) {
  const res = await fetch(`${apiBase()}/api/subjects`, {
    headers: { Authorization: `Bearer ${token}` }
  })
  if (!res.ok) {
    throw new Error(`subjects list ${res.status}`)
  }
  const rows = await res.json()
  return (Array.isArray(rows) ? rows : []).some(c => `${c.name || ''}`.includes(courseNameSubstring))
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
    const t = await res.text()
    throw new Error(`login failed ${res.status}: ${t}`)
  }
  const data = await res.json()
  return data.access_token
}

async function apiHomeworkTitlesForSubject(token, subjectId) {
  const url = new URL(`${apiBase()}/api/homeworks`)
  url.searchParams.set('subject_id', String(subjectId))
  url.searchParams.set('page_size', '100')
  const res = await fetch(url.toString(), {
    headers: { Authorization: `Bearer ${token}` }
  })
  if (!res.ok) {
    throw new Error(`homeworks list ${res.status}`)
  }
  const data = await res.json()
  return (data.data || []).map(h => h.title)
}

test.describe('E2E scenarios: boundary / dynamic / complex', () => {
  test.describe.configure({ timeout: 300_000 })

  test.beforeEach(async ({}, testInfo) => {
    const s = await resetE2eScenario()
    if (!s) {
      testInfo.skip(true, 'Missing e2e/.cache/scenario.json - run with Playwright globalSetup (E2E_DEV_SEED_TOKEN)')
    }
  })

  test('boundary: first dashboard load after login shows seeded teaching context', async ({ page }) => {
    const s = scenario()
    await login(page, s.teacher_own.username, s.teacher_own.password)
    await page.goto('/dashboard')
    await expect(page.locator('.layout-container')).toBeVisible({ timeout: 15000 })
    await enterSeededRequiredCourse(page, s.suffix)
    await page.goto('/homework')
    await expect(page.getByRole('cell', { name: new RegExp(`E2E_UI作业_${s.suffix}`) })).toBeVisible({
      timeout: 20000
    })
  })

  test('boundary: admin creates a course with schedule then deletes it (UI + list consistency)', async ({
    page
  }) => {
    const s = scenario()
    const u = `e2e_del_${s.suffix}`
    await login(page, s.admin.username, s.admin.password)
    await page.goto('/subjects')
    await page.getByTestId('subjects-open-create').click()
    await expect(page.getByRole('dialog', { name: /新建课程/ })).toBeVisible()
    await page.getByTestId('subjects-form-name').fill(`E2E待删课_${u}`)
    await openDialogSelectByLabel(page, '所属班级', /新建课程/)
    await clickSelectOptionByLabel(page, s.class_name_1)
    await openDialogSelectByLabel(page, '任课老师', /新建课程/)
    await pickTeacherOption(page, `E2E任课甲_${s.suffix}`)
    await page.locator('.schedule-picker__cell').filter({ hasText: /^选择$/ }).first().click()
    await fillCourseDialogDateRange(page)
    await page.getByTestId('subjects-course-save').click()
    await expect
      .poll(async () => {
        const tok = await obtainAccessToken(s.admin.username, s.admin.password)
        const res = await page.request.get(`${apiBase()}/api/subjects`, {
          headers: { Authorization: `Bearer ${tok}` }
        })
        if (!res.ok()) {
          return false
        }
        const rows = await res.json()
        return Array.isArray(rows) && rows.some(c => `${c.name || ''}`.includes(`E2E待删课_${u}`))
      }, { timeout: 120000 })
      .toBe(true)

    const adminTok = await obtainAccessToken(s.admin.username, s.admin.password)
    const subjectsRes = await page.request.get(`${apiBase()}/api/subjects`, {
      headers: { Authorization: `Bearer ${adminTok}` }
    })
    expect(subjectsRes.ok()).toBeTruthy()
    const subjectRows = await subjectsRes.json()
    const created = Array.isArray(subjectRows)
      ? subjectRows.find(c => `${c.name || ''}`.includes(`E2E待删课_${u}`))
      : null
    expect(created?.id).toBeTruthy()

    await page.goto('/subjects', { waitUntil: 'load', timeout: 120000 })
    const delPromise = page.waitForResponse(
      r =>
        r.url().includes(`/api/subjects/${created.id}`) &&
        r.request().method() === 'DELETE' &&
        !r.url().includes('/students/'),
      { timeout: 120000 }
    )
    await page.getByTestId(`subjects-delete-${created.id}`).click({ force: true })
    await confirmMessageBox(page)
    const delResp = await delPromise
    expect(delResp.ok()).toBeTruthy()

    await page.goto('/subjects', { waitUntil: 'load', timeout: 60000 })
    await expect(page.getByTestId(`subjects-delete-${created.id}`)).toHaveCount(0, { timeout: 30000 })
  })

  test('boundary: admin creates a new student user aligned to class', async ({ page }) => {
    const s = scenario()
    const uname = `e2e_newstu_${s.suffix}_${Date.now()}`
    const adminTok = await obtainAccessToken(s.admin.username, s.admin.password)
    await apiPostJson('/api/users', adminTok, {
      username: uname,
      password: s.password_teacher_student,
      real_name: 'E2E新建学生',
      role: 'student',
      class_id: s.class_id_1
    })

    await login(page, s.admin.username, s.admin.password)
    await page.goto('/users', { waitUntil: 'load', timeout: 120000 })
    await expect(page.locator('tbody tr').filter({ hasText: uname })).toHaveCount(1, { timeout: 120000 })
  })

  test('dynamic: teacher publishes homework; student sees it; API list matches', async ({ page }) => {
    const s = scenario()
    const title = `E2E动态作业_${s.suffix}_${Date.now()}`
    await login(page, s.teacher_own.username, s.teacher_own.password)
    await enterSeededRequiredCourse(page, s.suffix)
    await page.goto('/homework')
    await page.getByTestId('homework-btn-create').click()
    await expect(page.getByRole('dialog', { name: '发布作业' })).toBeVisible()
    await page.getByTestId('homework-form-title').fill(title)
    await page.getByTestId('homework-form-save').click()
    await expect(page.getByRole('dialog', { name: '发布作业' })).toBeHidden({ timeout: 25000 })
    await expect(page.getByRole('cell', { name: title })).toBeVisible({ timeout: 15000 })

    const tok = await obtainAccessToken(s.teacher_own.username, s.teacher_own.password)
    const titles = await apiHomeworkTitlesForSubject(tok, s.course_required_id)
    expect(titles.some(t => t === title)).toBeTruthy()

    await login(page, s.student_plain.username, s.student_plain.password)
    await enterSeededRequiredCourse(page, s.suffix)
    await page.goto('/homework')
    await expect(page.getByRole('row', { name: new RegExp(title.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')) })).toBeVisible({
      timeout: 20000
    })
  })

  test('dynamic: student updates display name; persists after reload', async ({ page }) => {
    const s = scenario()
    const newName = `E2E改名_${s.suffix}`
    await login(page, s.student_plain.username, s.student_plain.password)
    await page.goto('/personal-settings')
    await page.getByTestId('personal-profile-real-name').fill(newName)
    await page.getByTestId('personal-profile-save').click()
    await expect(page.getByText('已保存').first()).toBeVisible({ timeout: 10000 })
    await page.reload()
    await expect(page.getByTestId('personal-profile-real-name')).toHaveValue(newName, { timeout: 15000 })
  })

  test('complex: teacher publishes -> student sees -> teacher renames -> student sees new title (API check)', async ({
    page
  }) => {
    const s = scenario()
    const t1 = `E2E复杂A_${s.suffix}`
    const t2 = `E2E复杂B_${s.suffix}`
    await login(page, s.teacher_own.username, s.teacher_own.password)
    await enterSeededRequiredCourse(page, s.suffix)
    await page.goto('/homework')
    await page.getByTestId('homework-btn-create').click()
    await page.getByTestId('homework-form-title').fill(t1)
    await page.getByTestId('homework-form-save').click()
    await expect(page.getByRole('dialog', { name: '发布作业' })).toBeHidden({ timeout: 25000 })

    await login(page, s.student_plain.username, s.student_plain.password)
    await enterSeededRequiredCourse(page, s.suffix)
    await page.goto('/homework')
    await expect(page.getByRole('row', { name: t1 })).toBeVisible({ timeout: 20000 })

    await login(page, s.teacher_own.username, s.teacher_own.password)
    await enterSeededRequiredCourse(page, s.suffix)
    await page.goto('/homework')
    const editRow = page.getByRole('row', { name: t1 })
    await editRow.getByTestId('homework-btn-edit').click()
    await page.getByTestId('homework-form-title').fill(t2)
    await page.getByTestId('homework-form-save').click()
    await expect(page.getByRole('dialog', { name: '编辑作业' })).toBeHidden({ timeout: 25000 })

    const tok = await obtainAccessToken(s.teacher_own.username, s.teacher_own.password)
    const titles = await apiHomeworkTitlesForSubject(tok, s.course_required_id)
    expect(titles.some(x => x === t2)).toBeTruthy()
    expect(titles.some(x => x === t1)).toBeFalsy()

    await login(page, s.student_plain.username, s.student_plain.password)
    await enterSeededRequiredCourse(page, s.suffix)
    await page.goto('/homework')
    await expect(page.getByRole('row', { name: t2 })).toBeVisible({ timeout: 20000 })
    await expect(page.getByRole('row', { name: t1 })).toHaveCount(0)
  })

  test('complex: admin and teacher contexts - admin creates course; teacher sees new course card', async ({
    browser
  }) => {
    const s = scenario()
    const courseName = `E2E双角_${s.suffix}_${Date.now()}`
    const adminContext = await browser.newContext()
    const teacherContext = await browser.newContext()
    const adminPage = await adminContext.newPage()
    const teacherPage = await teacherContext.newPage()
    try {
      await login(adminPage, s.admin.username, s.admin.password)
      await adminPage.goto('/subjects')
      await adminPage.getByTestId('subjects-open-create').click()
      await adminPage.getByTestId('subjects-form-name').fill(courseName)
      await openDialogSelectByLabel(adminPage, '所属班级', /新建课程/)
      await clickSelectOptionByLabel(adminPage, s.class_name_1)
      await openDialogSelectByLabel(adminPage, '任课老师', /新建课程/)
      await pickTeacherOption(adminPage, `E2E任课甲_${s.suffix}`)
      await adminPage.locator('.schedule-picker__cell').filter({ hasText: /^选择$/ }).first().click()
      await fillCourseDialogDateRange(adminPage)
      await adminPage.getByTestId('subjects-course-save').click()
      await expect(adminPage.getByRole('dialog', { name: /新建课程/ })).toBeHidden({ timeout: 20000 })

      await login(teacherPage, s.teacher_own.username, s.teacher_own.password)
      const tok = await obtainAccessToken(s.teacher_own.username, s.teacher_own.password)
      await expect
        .poll(async () => apiCourseExistsForTeacher(tok, courseName), { timeout: 30_000 })
        .toBeTruthy()
      await teacherPage.goto('/courses')
      await expect(
        teacherPage.locator('article.course-card').filter({ has: teacherPage.getByRole('heading', { name: courseName }) })
      ).toBeVisible({ timeout: 20000 })
    } finally {
      await adminContext.close().catch(() => {})
      await teacherContext.close().catch(() => {})
    }
  })
})
