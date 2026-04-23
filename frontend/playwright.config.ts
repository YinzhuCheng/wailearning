import { defineConfig, devices } from '@playwright/test'

/**
 * UI → API 端到端：默认不自动起服务（避免本地/CI 误跑占端口）。
 * 下一轮实现用例时：先 `npm run dev`（或设置 baseURL 指向已部署环境），再 `npx playwright test`。
 */
export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: 'list',
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL || 'http://127.0.0.1:5173',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure'
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }]
})
