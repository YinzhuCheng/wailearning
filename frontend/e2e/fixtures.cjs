const fs = require('fs')
const path = require('path')

const { expect } = require('@playwright/test')

let cached

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

/** Open the seeded required course card (stable when multiple courses exist). */
async function enterSeededRequiredCourse(page, suffix) {
  const name = `E2E必修课_${suffix}`
  await page.goto('/courses')
  const card = page.locator('article.course-card').filter({ has: page.getByRole('heading', { name: name }) })
  await expect(card).toBeVisible({ timeout: 15000 })
  await card.getByRole('button', { name: /进入课程|查看课程/ }).click()
}

module.exports = { loadE2eScenario, enterSeededRequiredCourse }
