const fs = require('fs')
const path = require('path')

const { expect } = require('@playwright/test')

let cached

function apiBase() {
  return (process.env.E2E_API_URL || 'http://127.0.0.1:8012').replace(/\/$/, '')
}

/**
 * @returns {Record<string, unknown>|null}
 */
function loadE2eScenario() {
  if (cached !== undefined) {
    return cached
  }
  const p = path.join(__dirname, '.cache', 'scenario.json')
  if (!fs.existsSync(p)) {
    cached = null
    return null
  }
  cached = JSON.parse(fs.readFileSync(p, 'utf8'))
  return cached
}

async function resetE2eScenario() {
  const token = (process.env.E2E_DEV_SEED_TOKEN || '').trim()
  if (!token) {
    cached = null
    return null
  }
  const res = await fetch(`${apiBase()}/api/e2e/dev/reset-scenario`, {
    method: 'POST',
    headers: { 'X-E2E-Seed-Token': token }
  })
  if (!res.ok) {
    throw new Error(`E2E seed failed (${res.status}): ${await res.text()}`)
  }
  const data = await res.json()
  const p = path.join(__dirname, '.cache', 'scenario.json')
  fs.mkdirSync(path.dirname(p), { recursive: true })
  fs.writeFileSync(p, JSON.stringify(data, null, 2), 'utf8')
  cached = data
  return data
}

/** Open the seeded required course card (stable when multiple courses exist). */
async function enterSeededRequiredCourse(page, suffix) {
  const name = `E2E必修课_${suffix}`
  await page.goto('/courses')
  const card = page.locator('article.course-card').filter({ has: page.getByRole('heading', { name: name }) })
  await expect(card).toBeVisible({ timeout: 15000 })
  await card.getByRole('button', { name: /进入课程|查看课程/ }).click()
}

module.exports = { loadE2eScenario, resetE2eScenario, enterSeededRequiredCourse }
