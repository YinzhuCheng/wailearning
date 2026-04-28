const { expect, test } = require('@playwright/test')
const { loadE2eScenario } = require('./fixtures.cjs')

const scenario = () => loadE2eScenario()

async function login(page, username, password) {
  await page.goto('/login')
  await page.getByTestId('login-username').fill(username)
  await page.getByTestId('login-password').fill(password)
  await page.getByTestId('login-submit').click()
  await page.waitForURL(url => !url.pathname.includes('/login'), { timeout: 15000 })
}

test.describe('UI: homework student actions (requires globalSetup seed)', () => {
  test.beforeEach(({}, testInfo) => {
    const s = scenario()
    if (!s) {
      testInfo.skip(true, 'Missing e2e/.cache/scenario.json — set E2E_DEV_SEED_TOKEN and run globalSetup')
    }
  })

  test('student: merged homework action opens submit page; dropdown opens detail', async ({ page }) => {
    const s = scenario()
    await login(page, s.student_plain.username, s.student_plain.password)

    await page.goto('/courses')
    await page.getByRole('button', { name: '进入课程' }).first().click()
    await page.goto('/homework')

    const row = page.locator('tbody tr').first()
    await expect(row).toBeVisible({ timeout: 15000 })

    await row.getByRole('button', { name: '作业与提交' }).click()
    await expect(page).toHaveURL(/\/homework\/\d+\/submit$/)

    await page.goBack()
    await expect(row).toBeVisible({ timeout: 15000 })

    const splitHost = row.locator('.el-dropdown').filter({ has: page.getByRole('button', { name: '作业与提交' }) })
    await splitHost.locator('.el-dropdown__caret-button').click()
    await page.getByRole('menuitem', { name: '仅查看说明' }).click()
    await expect(page.locator('.el-dialog').filter({ hasText: '作业详情' })).toBeVisible({ timeout: 10000 })
    await page.getByRole('button', { name: '关闭' }).click()
  })

  test('student: my courses page has no duplicate current-course banner', async ({ page }) => {
    const s = scenario()
    await login(page, s.student_plain.username, s.student_plain.password)
    await page.goto('/courses')
    await expect(page.getByText(/^当前课程：/)).toHaveCount(0)
  })
})
