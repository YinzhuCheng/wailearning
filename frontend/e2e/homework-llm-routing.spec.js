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

test.describe('E2E homework LLM routing controls (requires globalSetup seed)', () => {
  test.beforeEach(({}, testInfo) => {
    const s = scenario()
    if (!s) {
      testInfo.skip(true, 'Missing e2e/.cache/scenario.json — set E2E_DEV_SEED_TOKEN and run globalSetup')
    }
  })

  test('teacher: edit homework shows LLM routing mode control', async ({ page }) => {
    const s = scenario()
    await login(page, s.teacher_own.username, s.teacher_own.password)

    await page.goto('/courses')
    await page.getByRole('button', { name: '进入课程' }).first().click()
    await page.goto('/homework')

    const editBtn = page.getByTestId('homework-btn-edit').first()
    await expect(editBtn).toBeVisible({ timeout: 15000 })
    await editBtn.click()

    await expect(page.getByTestId('homework-llm-routing-mode')).toBeVisible({ timeout: 15000 })
  })
})
