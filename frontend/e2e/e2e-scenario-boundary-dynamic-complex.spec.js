/**
 * Scenario-style Playwright tests: boundary (cold start / CRUD), dynamic (mutations visible end-to-end),
 * complex (multi-step, multi-role, optional API audit).
 *
 * Relies on globalSetup → e2e/.cache/scenario.json (same as other e2e specs).
 */
const { expect, test } = require('@playwright/test')
const { loadE2eScenario, enterSeededRequiredCourse } = require('./fixtures.cjs')

const scenario = () => loadE2eScenario()

function apiBase() {
  return (process.env.E2E_API_URL || 'http://127.0.0.1:8012').replace(/\/$/, '')
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

/** Course form validation requires start/end dates on the first time block. */
async function fillCourseDialogDateRange(page) {
  const dlg = page.getByRole('dialog', { name: /新建课程|编辑课程/ })
  await dlg.getByPlaceholder('请选择开始日期').first().fill('2026-01-15')
  await dlg.getByPlaceholder('请选择结束日期').first().fill('2026-06-30')
}

async function confirmMessageBox(page) {
  await page.getByRole('dialog', { name: '删除课程' }).getByRole('button', { name: /^(OK|确定)$/ }).click()
}

/** Element Plus: click the select control inside a form item by its label text. */
async function openDialogSelectByLabel(page, labelText) {
  const row = page.locator('.el-dialog .el-form-item').filter({ has: page.getByText(labelText, { exact: true }) })
  await row.locator('.el-select').click()
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
  test.describe.configure({ timeout: 120_000 })

  test.beforeEach(({}, testInfo) => {
    if (!scenario()) {
      testInfo.skip(true, 'Missing e2e/.cache/scenario.json — run with Playwright globalSetup (E2E_DEV_SEED_TOKEN)')
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
    await openDialogSelectByLabel(page, '所属班级')
    await page.getByRole('option', { name: s.class_name_1 }).click()
    await openDialogSelectByLabel(page, '任课老师')
    await pickTeacherOption(page, `E2E任课甲_${s.suffix}`)
    await page.locator('.schedule-picker__cell').filter({ hasText: /^选择$/ }).first().click()
    await fillCourseDialogDateRange(page)
    await page.getByTestId('subjects-course-save').click()
    await expect(page.getByRole('dialog', { name: /新建课程/ })).toBeHidden({ timeout: 20000 })
    const row = page.getByRole('row', { name: new RegExp(`E2E待删课_${u}`) })
    await expect(row).toBeVisible({ timeout: 15000 })
    await row.getByRole('button', { name: '删除' }).click()
    await confirmMessageBox(page)
    await expect(row).toHaveCount(0, { timeout: 15000 })
  })

  test('boundary: admin creates a new student user aligned to class', async ({ page }) => {
    const s = scenario()
    const uname = `e2e_newstu_${s.suffix}`
    await login(page, s.admin.username, s.admin.password)
    await page.goto('/users')
    await page.getByTestId('users-open-create').click()
    await expect(page.getByRole('dialog', { name: '新建用户' })).toBeVisible()
    await page.getByLabel('用户名').fill(uname)
    await page.getByLabel('密码').fill(s.password_teacher_student)
    await page.getByLabel('姓名').fill('E2E新建学生')
    await page.locator('.el-dialog label.el-radio').filter({ hasText: '学生' }).click()
    await openDialogSelectByLabel(page, '所属班级')
    await page.getByRole('option', { name: s.class_name_1 }).click()
    await page.getByRole('button', { name: '保存' }).click()
    await expect(page.getByRole('dialog', { name: '新建用户' })).toBeHidden({ timeout: 20000 })
    await expect(page.getByRole('row', { name: new RegExp(uname) })).toBeVisible({ timeout: 15000 })
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

  test('complex: teacher publishes → student sees → teacher renames → student sees new title (API check)', async ({
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

  test('complex: admin and teacher contexts — admin creates course; teacher sees new course card', async ({
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
      await openDialogSelectByLabel(adminPage, '所属班级')
      await adminPage.getByRole('option', { name: s.class_name_1 }).click()
      await openDialogSelectByLabel(adminPage, '任课老师')
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
