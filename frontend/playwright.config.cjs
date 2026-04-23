const { defineConfig, devices } = require('@playwright/test')
const path = require('path')

const E2E_API_PORT = process.env.E2E_API_PORT || '8012'
const E2E_UI_PORT = process.env.E2E_UI_PORT || '3012'
const apiBase = `http://127.0.0.1:${E2E_API_PORT}`

process.env.E2E_API_URL = process.env.E2E_API_URL || apiBase
process.env.E2E_DEV_SEED_TOKEN = process.env.E2E_DEV_SEED_TOKEN || 'test-playwright-seed'
process.env.PLAYWRIGHT_BASE_URL =
  process.env.PLAYWRIGHT_BASE_URL || `http://127.0.0.1:${E2E_UI_PORT}`

const repoRoot = path.resolve(__dirname, '..')
const sqliteUrl = `sqlite:////tmp/playwright_e2e_${E2E_API_PORT}.sqlite`
const secretKey = 'playwright-e2e-secret-key-minimum-32-chars-xx'

const apiEnv = [
  'E2E_DEV_SEED_ENABLED=true',
  `E2E_DEV_SEED_TOKEN=${process.env.E2E_DEV_SEED_TOKEN}`,
  'INIT_DEFAULT_DATA=false',
  `DATABASE_URL=${sqliteUrl}`,
  `SECRET_KEY=${secretKey}`,
  'ENABLE_LLM_GRADING_WORKER=false',
  'LLM_GRADING_WORKER_LEADER=false'
].join(' ')

/**
 * @see {import('@playwright/test').PlaywrightTestConfig}
 */
module.exports = defineConfig({
  testDir: './e2e',
  timeout: 60_000,
  globalSetup: './e2e/global-setup.cjs',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: 'list',
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL,
    trace: 'on-first-retry',
    screenshot: 'only-on-failure'
  },
  webServer: [
    {
      command: `bash -lc 'cd "${repoRoot}" && exec env ${apiEnv} python3 -m uvicorn app.main:app --host 127.0.0.1 --port ${E2E_API_PORT}'`,
      url: `${apiBase}/api/health`,
      reuseExistingServer: !process.env.CI,
      timeout: 120_000
    },
    {
      command: `bash -lc 'cd "${path.join(repoRoot, 'frontend')}" && exec env VITE_PROXY_TARGET=${apiBase} npx vite --host 127.0.0.1 --port ${E2E_UI_PORT}'`,
      url: `http://127.0.0.1:${E2E_UI_PORT}/`,
      reuseExistingServer: !process.env.CI,
      timeout: 120_000
    }
  ],
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }]
})
