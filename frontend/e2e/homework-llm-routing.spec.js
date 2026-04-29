const { expect, test } = require('@playwright/test')
const { loadE2eScenario, enterSeededRequiredCourse } = require('./fixtures.cjs')

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
    await enterSeededRequiredCourse(page, s.suffix)
    await page.goto('/homework')

    const editRow = page.getByRole('row', { name: new RegExp(`E2E_UI作业_${s.suffix}`) })
    await expect(editRow).toBeVisible({ timeout: 15000 })
    await editRow.getByTestId('homework-btn-edit').click()

    await expect(page.getByTestId('homework-llm-routing-mode')).toBeVisible({ timeout: 15000 })
  })
})
