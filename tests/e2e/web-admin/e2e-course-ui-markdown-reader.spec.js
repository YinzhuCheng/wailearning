/**
 * Targeted E2E for course UI fixes: dashboard enrollment vs roster, Markdown LaTeX demo,
 * sidebar collapse control, materials layout + reader route (including discussion on reader),
 * flat teacher sidebar without 「日常教学」 submenu.
 *
 * Depends on Playwright globalSetup + fixtures reset scenario (same contract as e2e-core-flows-smoke).
 */
const { expect, test } = require('@playwright/test')
const { loadE2eScenario, resetE2eScenario } = require('./fixtures.cjs')
const { clickCourseSwitcherOption, login } = require('./future-advanced-coverage-helpers.cjs')

function scenario() {
  return loadE2eScenario()
}

test.describe('Course UI + Markdown LaTeX demo (seeded)', () => {
  test.describe.configure({ timeout: 180_000 })

  test.beforeEach(async ({}, testInfo) => {
    const data = await resetE2eScenario()
    if (!data) {
      testInfo.skip(true, 'Missing E2E scenario — globalSetup must seed scenario.json')
    }
  })

  test('dashboard student total uses enrollment count for required course', async ({ page }) => {
    const s = scenario()
    await login(page, s.teacher_own.username, s.teacher_own.password)
    await page.goto('/dashboard')
    await clickCourseSwitcherOption(page, `E2E必修课_${s.suffix}`)
    const card = page.locator('button.metric-card').filter({ hasText: '学生总数' })
    await expect(card).toBeVisible({ timeout: 20000 })
    // Class roster has 3 students; required course enrolls only st_plain + st_drop (see e2e_dev reset-scenario).
    await expect(card.locator('.metric-value')).toHaveText('2', { timeout: 15000 })
  })

  test('students screen header matches course enrollment count', async ({ page }) => {
    const s = scenario()
    await login(page, s.teacher_own.username, s.teacher_own.password)
    await clickCourseSwitcherOption(page, `E2E必修课_${s.suffix}`)
    await page.goto('/students')
    await expect(page.getByText(/课程学生名单/)).toBeVisible({ timeout: 20000 })
    await expect(page.locator('.header-count')).toContainText('共 2 人', { timeout: 15000 })
  })

  test('dashboard shows zero students for elective with no enrollments', async ({ page }) => {
    const s = scenario()
    await login(page, s.teacher_own.username, s.teacher_own.password)
    await page.goto('/dashboard')
    await clickCourseSwitcherOption(page, `E2E选修课_${s.suffix}`)
    const card = page.locator('button.metric-card').filter({ hasText: '学生总数' })
    await expect(card.locator('.metric-value')).toHaveText('0', { timeout: 15000 })
  })

  test('homework publish dialog shows rendered Markdown LaTeX demo', async ({ page }) => {
    const s = scenario()
    await login(page, s.teacher_own.username, s.teacher_own.password)
    await clickCourseSwitcherOption(page, `E2E必修课_${s.suffix}`)
    await page.goto('/homework')
    await page.getByTestId('homework-btn-create').click()
    const dlg = page.getByRole('dialog', { name: /发布作业/ })
    await expect(dlg).toBeVisible({ timeout: 15000 })
    const bodyPanel = dlg.locator('.md-panel').first()
    await expect(bodyPanel.getByTestId('markdown-latex-demo-render')).toBeVisible({ timeout: 15000 })
    await expect(bodyPanel.getByTestId('markdown-latex-demo-render').locator('.katex').first()).toBeVisible({
      timeout: 15000
    })
  })

  test('homework dialog hides LaTeX demo when switching body to plain text', async ({ page }) => {
    const s = scenario()
    await login(page, s.teacher_own.username, s.teacher_own.password)
    await clickCourseSwitcherOption(page, `E2E必修课_${s.suffix}`)
    await page.goto('/homework')
    await page.getByTestId('homework-btn-create').click()
    const dlg = page.getByRole('dialog', { name: /发布作业/ })
    await expect(dlg).toBeVisible({ timeout: 15000 })
    const bodyPanel = dlg.locator('.md-panel').first()
    await expect(bodyPanel.getByTestId('markdown-latex-demo-render')).toBeVisible({ timeout: 10000 })
    await bodyPanel.locator('.md-panel__format .el-radio-button').filter({ hasText: '纯文本' }).click()
    await expect(bodyPanel.getByTestId('markdown-latex-demo-render')).toHaveCount(0)
    await bodyPanel.locator('.md-panel__format .el-radio-button').filter({ hasText: 'Markdown' }).click()
    await expect(bodyPanel.getByTestId('markdown-latex-demo-render')).toBeVisible({ timeout: 10000 })
  })

  test('desktop sidebar logo area has no redundant collapse button', async ({ page }) => {
    const s = scenario()
    await login(page, s.teacher_own.username, s.teacher_own.password)
    await page.goto('/dashboard')
    await expect(page.locator('aside.sidebar .logo > button.el-button')).toHaveCount(0)
    await expect(page.getByTestId('sidebar-edge-handle')).toBeVisible({ timeout: 15000 })
  })

  test('materials layout stacks chapter panel above table (column flex)', async ({ page }) => {
    const s = scenario()
    await login(page, s.teacher_own.username, s.teacher_own.password)
    await clickCourseSwitcherOption(page, `E2E必修课_${s.suffix}`)
    await page.goto('/materials')
    await expect(page.locator('.materials-layout')).toBeVisible({ timeout: 20000 })
    const dir = await page.locator('.materials-layout').evaluate(el => getComputedStyle(el).flexDirection)
    expect(dir).toBe('column')
  })

  test('material reader route shows nav chrome and KaTeX-capable body', async ({ page }) => {
    const s = scenario()
    await login(page, s.teacher_own.username, s.teacher_own.password)
    await page.goto(`/materials/read/${s.material_discussion_id}`)
    await expect(page.getByRole('button', { name: '返回章节目录' })).toBeVisible({ timeout: 25000 })
    await expect(page.getByRole('button', { name: '上一篇' })).toBeVisible()
    await expect(page.getByRole('button', { name: '下一篇' })).toBeVisible()
    await expect(page.locator('.material-read-title')).toContainText(`E2E讨论资料_${s.suffix}`, {
      timeout: 15000
    })
    const discuss = page.locator('.material-read-page .discussion-card')
    await expect(discuss).toBeVisible({ timeout: 15000 })
    await expect(discuss.getByText('讨论区', { exact: true })).toBeVisible()
    await expect(discuss.getByText(/暂无讨论，发表第一条回复吧。/)).toBeVisible({ timeout: 10000 })
  })

  test('materials table read link opens reader route', async ({ page }) => {
    const s = scenario()
    await login(page, s.teacher_own.username, s.teacher_own.password)
    await clickCourseSwitcherOption(page, `E2E必修课_${s.suffix}`)
    await page.goto('/materials')
    await expect(page.locator('.el-table tbody tr').first()).toBeVisible({ timeout: 20000 })
    await page.getByTestId('materials-open-read-page').first().click()
    await expect(page).toHaveURL(new RegExp(`/materials/read/${s.material_discussion_id}`), {
      timeout: 15000
    })
    await expect(page.locator('.material-read-title')).toBeVisible({ timeout: 15000 })
  })

  test('teacher sidebar lists daily routes without a 日常教学 submenu title', async ({ page }) => {
    const s = scenario()
    await login(page, s.teacher_own.username, s.teacher_own.password)
    await page.goto('/dashboard')
    await expect(page.locator('.sidebar-menu .el-sub-menu__title').filter({ hasText: '日常教学' })).toHaveCount(0)
    await expect(page.locator('.sidebar-menu').getByRole('menuitem', { name: '课程仪表盘' })).toBeVisible({
      timeout: 15000
    })
    await expect(page.locator('.sidebar-menu').getByRole('menuitem', { name: '课程资料' })).toBeVisible()
  })

  test('material reader highlights 课程资料 in sidebar via active path mapping', async ({ page }) => {
    const s = scenario()
    await login(page, s.teacher_own.username, s.teacher_own.password)
    await page.goto(`/materials/read/${s.material_discussion_id}`)
    await expect(page.locator('.material-read-title')).toContainText(`E2E讨论资料_${s.suffix}`, { timeout: 15000 })
    const materialsItem = page.locator('.sidebar-menu .el-menu-item').filter({ hasText: '课程资料' })
    await expect(materialsItem).toHaveClass(/is-active/, { timeout: 10000 })
  })

  test('material detail discussion shows Markdown LaTeX demo', async ({ page }) => {
    const s = scenario()
    await login(page, s.teacher_own.username, s.teacher_own.password)
    await clickCourseSwitcherOption(page, `E2E必修课_${s.suffix}`)
    await page.goto('/materials')
    await page.locator('.el-table tbody tr').first().click()
    const dlg = page.getByRole('dialog', { name: '资料详情' })
    await expect(dlg).toBeVisible({ timeout: 20000 })
    await expect(dlg.getByTestId('markdown-latex-demo-render')).toBeVisible({ timeout: 15000 })
    const fmtBar = dlg.locator('.discussion-format-bar')
    await expect(fmtBar.getByRole('radio', { name: 'Markdown' })).toBeChecked({ timeout: 5000 })
    await fmtBar.locator('.el-radio-button').filter({ hasText: '纯文本' }).click()
    await expect(dlg.getByTestId('markdown-latex-demo-render')).toHaveCount(0)
  })
})
