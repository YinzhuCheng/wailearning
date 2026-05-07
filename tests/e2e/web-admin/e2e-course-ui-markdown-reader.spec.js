/**
 * Targeted E2E for course UI: Markdown LaTeX demo, sidebar collapse control,
 * materials layout + reader route (including discussion on reader),
 * flat teacher sidebar without 「日常教学」 submenu, flat student sidebar without 「课程学习」 submenu,
 * and the historical teaching-calendar deep link redirect.
 *
 * Dashboard (`/dashboard`) was removed from the product UI (May 2026); enrollment
 * count regressions for `GET /api/dashboard/stats` remain covered in pytest
 * (`tests/backend/integration/test_core_api_surface.py`).
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

  test('students screen header matches course enrollment count', async ({ page }) => {
    const s = scenario()
    await login(page, s.teacher_own.username, s.teacher_own.password)
    await clickCourseSwitcherOption(page, `E2E必修课_${s.suffix}`)
    await page.goto('/students')
    await expect(page.getByText(/课程学生名单/)).toBeVisible({ timeout: 20000 })
    await expect(page.locator('.header-count')).toContainText('共 2 人', { timeout: 15000 })
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
    await page.goto('/students')
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

  test('teacher sidebar keeps calendar inside attendance and hides removed standalone pages', async ({ page }) => {
    const s = scenario()
    await login(page, s.teacher_own.username, s.teacher_own.password)
    await page.goto('/students')
    await expect(page.locator('.sidebar-menu .el-sub-menu__title').filter({ hasText: '日常教学' })).toHaveCount(0)
    await expect(page.locator('.sidebar-menu').getByRole('menuitem', { name: '考勤管理' })).toBeVisible({
      timeout: 15000
    })
    await expect(page.locator('.sidebar-menu').getByRole('menuitem', { name: '教学日历' })).toHaveCount(0)
    await expect(page.locator('.sidebar-menu').getByRole('menuitem', { name: '课程资料' })).toBeVisible()
    await expect(page.locator('.sidebar-menu').getByRole('menuitem', { name: '课程仪表盘' })).toHaveCount(0)
  })

  test('student sidebar has no 课程学习 wrapper; former children are top-level', async ({ page }) => {
    const s = scenario()
    const pw = s.student_plain.password || s.password_teacher_student
    await login(page, s.student_plain.username, pw)
    await page.goto('/courses')
    await expect(page.locator('.sidebar-menu .el-sub-menu__title').filter({ hasText: '课程学习' })).toHaveCount(0)
    await expect(page.locator('.sidebar-menu').getByRole('menuitem', { name: '选课与进度' })).toBeVisible({
      timeout: 15000
    })
    await expect(page.locator('.sidebar-menu').getByRole('menuitem', { name: '课程通知' })).toBeVisible()
  })

  test('historical teaching-calendar deep link redirects to attendance with embedded TeachingCalendar', async ({ page }) => {
    const s = scenario()
    await login(page, s.teacher_own.username, s.teacher_own.password)
    await clickCourseSwitcherOption(page, `E2E必修课_${s.suffix}`)
    await page.goto('/teaching-calendar')
    await expect(page).toHaveURL(/\/attendance$/, { timeout: 15000 })
    await expect(page.locator('.attendance-page .page-title')).toHaveText('考勤管理', { timeout: 15000 })
    await expect(page.locator('.attendance-page .teaching-calendar h3')).toHaveText('教学日历', {
      timeout: 15000
    })
  })

  test('material reader highlights 课程资料 in sidebar via active path mapping', async ({ page }) => {
    const s = scenario()
    await login(page, s.teacher_own.username, s.teacher_own.password)
    await page.goto(`/materials/read/${s.material_discussion_id}`)
    await expect(page.locator('.material-read-title')).toContainText(`E2E讨论资料_${s.suffix}`, { timeout: 15000 })
    const materialsItem = page.locator('.sidebar-menu .el-menu-item').filter({ hasText: '课程资料' })
    await expect(materialsItem).toHaveClass(/is-active/, { timeout: 10000 })
  })

  test('material detail discussion keeps demo collapsed by default, shows live preview, and renders posted KaTeX', async ({
    page
  }) => {
    const s = scenario()
    await login(page, s.teacher_own.username, s.teacher_own.password)
    await clickCourseSwitcherOption(page, `E2E必修课_${s.suffix}`)
    await page.goto('/materials')
    await page.locator('.el-table tbody tr').first().click()
    const dlg = page.getByRole('dialog', { name: '资料详情' })
    await expect(dlg).toBeVisible({ timeout: 20000 })
    const stamp = Date.now()
    const textarea = dlg.locator('.discussion-input textarea')
    await expect(dlg.getByRole('button', { name: '查看 Markdown + LaTeX 示例' })).toBeVisible({ timeout: 15000 })
    await expect(dlg.getByTestId('markdown-latex-demo-render')).toHaveCount(0)
    const fmtBar = dlg.locator('.discussion-format-bar')
    await expect(fmtBar.getByRole('radio', { name: 'Markdown' })).toBeChecked({ timeout: 5000 })
    await textarea.fill(`md-material-${stamp}\n\n公式：\\(x^2+y^2=z^2\\)`)
    await expect(dlg.getByTestId('discussion-markdown-preview').locator('.katex').first()).toBeVisible({
      timeout: 15000
    })
    await dlg.getByRole('button', { name: '查看 Markdown + LaTeX 示例' }).click()
    await expect(dlg.getByTestId('markdown-latex-demo-render')).toBeVisible({ timeout: 15000 })
    await dlg.getByTestId('discussion-submit').click()
    const row = dlg.locator('.discussion-row').filter({ hasText: `md-material-${stamp}` })
    await expect(row).toBeVisible({ timeout: 15000 })
    await expect(row.locator('.katex').first()).toBeVisible({ timeout: 15000 })
  })
})
