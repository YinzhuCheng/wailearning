const fs = require('fs')
const path = require('path')

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

module.exports = { loadE2eScenario }
