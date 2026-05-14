#!/usr/bin/env node

const { spawn } = require('child_process')
const path = require('path')

const schoolRoot = path.resolve(__dirname, '..')
const runner = path.join(schoolRoot, 'scripts', 'playwright-external-runner.cjs')
const captureScript = path.join(schoolRoot, 'scripts', 'capture-student-homework-layout.cjs')
const outputArg = process.argv[2] || path.join('pics', 'student-homework-layout-fixed.png')

const child = spawn(
  process.execPath,
  [runner, captureScript, outputArg],
  {
    cwd: schoolRoot,
    stdio: 'inherit',
    windowsHide: true,
    env: {
      ...process.env,
      PLAYWRIGHT_USE_EXTERNAL_SERVERS: 'true'
    }
  }
)

child.once('exit', code => {
  process.exit(code ?? 1)
})
