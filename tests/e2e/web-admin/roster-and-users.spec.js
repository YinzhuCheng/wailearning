const { expect, test } = require('@playwright/test')
const { loadE2eScenario, resetE2eScenario, enterSeededRequiredCourse } = require('./fixtures.cjs')

const scenario = () => loadE2eScenario()

async function login(page, username, password) {
  await page.goto('/login')
  await page.getByTestId('login-username').fill(username)
  await page.getByTestId('login-password').fill(password)
  await page.getByTestId('login-submit').click()
  await page.waitForURL(url => !url.pathname.includes('/login'), { timeout: 15000 })
}

test.describe('E2E roster + users (requires globalSetup seed)', () => {
  test.describe.configure({ timeout: 180_000 })
  test.beforeEach(async ({}, testInfo) => {
    const s = await resetE2eScenario()
    if (!s) {
      testInfo.skip(true, 'Missing e2e/.cache/scenario.json — set E2E_DEV_SEED_TOKEN and run globalSetup')
    }
  })

  test('admin: roster enroll adds student_b to required course', async ({ page }) => {
    const s = scenario()
    await login(page, s.admin.username, s.admin.password)

    await page.goto('/subjects')
    await page.getByTestId(`btn-roster-enroll-${s.course_required_id}`).click()
    await expect(page.getByTestId('dialog-roster-enroll')).toBeVisible()

    const row = page.locator(`[data-testid="table-roster-enroll-pick"] tr:has-text("${s.student_b.username}")`)
    await row.locator('.el-checkbox').first().click({ force: true })
    const rosterResp = page.waitForResponse(
      r =>
        r.url().includes('/roster-enroll') &&
        r.request().method() === 'POST' &&
        r.ok(),
      { timeout: 120000 }
    )
    await page.getByTestId('btn-roster-enroll-submit').click({ force: true })
    await rosterResp

    await expect(page.getByTestId('dialog-roster-enroll')).toBeHidden({ timeout: 90000 })
  })

  test('teacher: paste import opens dialog and preview', async ({ page }) => {
    const s = scenario()
    await login(page, s.teacher_own.username, s.teacher_own.password)

    await page.goto('/courses')
    await enterSeededRequiredCourse(page, s.suffix)

    await page.goto('/students')
    await page.getByTestId('students-open-paste-import').click()
    await expect(page.getByTestId('dialog-paste-import-students')).toBeVisible()

    const paste = `粘贴生\t男\t${s.suffix}_paste1`
    await page.getByTestId('paste-import-textarea').fill(paste)
    await page.getByTestId('paste-import-preview').click()
    await expect(page.getByTestId('paste-import-submit')).toBeEnabled()
  })

  test('teacher: file import dialog has templates and upload trigger', async ({ page }) => {
    const s = scenario()
    await login(page, s.teacher_own.username, s.teacher_own.password)

    await page.goto('/courses')
    await enterSeededRequiredCourse(page, s.suffix)
    await page.goto('/students')

    await page.getByRole('button', { name: '文件导入花名册' }).click()
    await expect(page.getByTestId('dialog-file-import-students')).toBeVisible()
    await expect(page.getByTestId('students-download-template-xlsx')).toBeVisible()
    await expect(page.getByTestId('students-download-template-csv')).toBeVisible()
    await expect(page.getByTestId('students-trigger-file-import')).toBeVisible()
  })

  test('admin: batch class dialog opens', async ({ page }) => {
    const s = scenario()
    await login(page, s.admin.username, s.admin.password)
    await page.goto('/users')

    const rowA = page.locator(`tr:has-text("${s.student_plain.username}")`)
    await rowA.locator('.el-checkbox').first().click({ force: true })
    await page.getByTestId('users-open-batch-class').click()
    await expect(page.getByTestId('dialog-batch-class')).toBeVisible()
    await page.getByTestId('batch-class-target-select').click({ force: true })
    await page.getByRole('option', { name: s.class_name_1 }).click()
    await expect(page.getByTestId('batch-class-confirm')).toBeEnabled()
  })

  test('admin: student file import dialog opens with template buttons', async ({ page }) => {
    const s = scenario()
    await login(page, s.admin.username, s.admin.password)
    await page.goto('/students')

    await page.getByRole('button', { name: '文件导入名单' }).click()
    await expect(page.getByTestId('dialog-file-import-students')).toBeVisible()
    await expect(page.getByTestId('students-download-template-xlsx')).toBeVisible()
    await expect(page.getByTestId('students-download-template-csv')).toBeVisible()
    await expect(page.getByTestId('students-trigger-file-import')).toBeVisible()
  })

  test('admin: users file-import-students dialog opens', async ({ page }) => {
    const s = scenario()
    await login(page, s.admin.username, s.admin.password)
    await page.goto('/users')

    await page.getByTestId('users-open-student-import').click()
    await expect(page.getByTestId('dialog-users-import-students')).toBeVisible()
  })

  test('orphan course: roster dialog shows empty state', async ({ page }) => {
    const s = scenario()
    await login(page, s.admin.username, s.admin.password)
    await page.goto('/subjects')
    await page.getByTestId(`btn-roster-enroll-${s.course_orphan_id}`).click()
    await expect(page.getByText('当前课程未绑定班级，无法从花名册进课。')).toBeVisible()
  })
})
