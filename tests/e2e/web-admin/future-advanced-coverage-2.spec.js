const { expect, test } = require('@playwright/test')
const { loadE2eScenario, resetE2eScenario, enterSeededRequiredCourse } = require('./fixtures.cjs')

const scenario = () => loadE2eScenario()

function apiBase() {
  return (process.env.E2E_API_URL || 'http://127.0.0.1:8012').replace(/\/$/, '')
}

async function login(page, username, password) {
  await page.goto('/login', { waitUntil: 'load', timeout: 60000 })
  await expect(page.getByTestId('login-username')).toBeVisible({ timeout: 30000 })
  await page.getByTestId('login-username').fill(username)
  await page.getByTestId('login-password').fill(password)
  await page.getByTestId('login-submit').click()
  await page.waitForURL(url => !url.pathname.includes('/login'), { timeout: 20000 })
}

async function obtainAccessToken(username, password) {
  const body = new URLSearchParams()
  body.set('username', username)
  body.set('password', password)
  const res = await fetch(`${apiBase()}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body
  })
  if (!res.ok) {
    throw new Error(`login failed ${res.status}: ${await res.text()}`)
  }
  const data = await res.json()
  return data.access_token
}

async function apiGetJson(pathname, token) {
  const res = await fetch(`${apiBase()}${pathname}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {}
  })
  if (!res.ok) {
    throw new Error(`GET ${pathname} failed ${res.status}: ${await res.text()}`)
  }
  return res.json()
}

async function apiPostJson(pathname, token, body) {
  const res = await fetch(`${apiBase()}${pathname}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {})
    },
    body: JSON.stringify(body)
  })
  if (!res.ok) {
    throw new Error(`POST ${pathname} failed ${res.status}: ${await res.text()}`)
  }
  return res.json()
}

async function apiPutJson(pathname, token, body) {
  const res = await fetch(`${apiBase()}${pathname}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {})
    },
    body: JSON.stringify(body)
  })
  if (!res.ok) {
    throw new Error(`PUT ${pathname} failed ${res.status}: ${await res.text()}`)
  }
  return res.json()
}

test.describe.skip('Future advanced E2E coverage expansion II', () => {
  test.describe.configure({ timeout: 180_000 })

  test.beforeEach(async ({}, testInfo) => {
    const s = await resetE2eScenario()
    if (!s) {
      testInfo.skip(true, 'Missing e2e seed cache; run globalSetup with E2E_DEV_SEED_TOKEN first')
    }
  })

  test.skip('16. teacher stale dual-tab material publish versus delete converges to one surviving material record', async ({ browser }) => {
    const s = scenario()
    const ctxA = await browser.newContext()
    const ctxB = await browser.newContext()
    const pageA = await ctxA.newPage()
    const pageB = await ctxB.newPage()
    await login(pageA, s.teacher_own.username, s.teacher_own.password)
    await login(pageB, s.teacher_own.username, s.teacher_own.password)
    await enterSeededRequiredCourse(pageA, s.suffix)
    await enterSeededRequiredCourse(pageB, s.suffix)
    await pageA.goto('/materials')
    await pageB.goto('/materials')
    // Future intent:
    // tab A edits and republishes an existing material while tab B deletes it from stale state,
    // verify one authoritative final outcome with no half-visible phantom row.
  })

  test.skip('17. student stale homework detail page after teacher unpublish shows safe recovery instead of broken submit state', async ({ browser }) => {
    const s = scenario()
    const teacherPage = await browser.newPage()
    const studentPage = await browser.newPage()
    await login(teacherPage, s.teacher_own.username, s.teacher_own.password)
    await login(studentPage, s.student_plain.username, s.student_plain.password)
    await enterSeededRequiredCourse(studentPage, s.suffix)
    await studentPage.goto('/homework')
    // Future intent:
    // student opens homework detail, teacher unpublishes/removes it,
    // student stale page should recover cleanly and not create orphan submission calls.
  })

  test.skip('18. admin class rename during teacher active course session updates downstream labels without changing course identity', async ({ browser }) => {
    const s = scenario()
    const adminPage = await browser.newPage()
    const teacherPage = await browser.newPage()
    await login(adminPage, s.admin.username, s.admin.password)
    await login(teacherPage, s.teacher_own.username, s.teacher_own.password)
    await teacherPage.goto('/courses')
    // Future intent:
    // rename seeded class in admin tab while teacher course dashboards are open,
    // assert labels update eventually but selected course id and access remain stable.
  })

  test.skip('19. teacher assignment of per-course LLM policy while worker is already processing leaves old task on old config and new task on new config', async ({ browser }) => {
    const s = scenario()
    const teacherToken = await obtainAccessToken(s.teacher_own.username, s.teacher_own.password)
    await apiGetJson(`/api/llm-settings/courses/${s.course_required_id}`, teacherToken)
    // Future intent:
    // submit one grading task, mutate course LLM config mid-flight, submit second task,
    // assert first task completion is internally consistent and second task uses the new config.
  })

  test.skip('20. student and parent concurrent homework visibility after appeal reopen stays consistent with permissions', async ({ browser }) => {
    const s = scenario()
    const studentPage = await browser.newPage()
    await login(studentPage, s.student_plain.username, s.student_plain.password)
    await studentPage.goto('/homework')
    // Future intent:
    // student reopens appeal while parent view remains open in separate app/session,
    // validate the final visibility of score/comment/appeal status for both roles.
  })

  test.skip('21. teacher rapid create-edit-delete notification sequence leaves no duplicate unread counters in student dashboard', async ({ browser }) => {
    const s = scenario()
    const teacherToken = await obtainAccessToken(s.teacher_own.username, s.teacher_own.password)
    const studentToken = await obtainAccessToken(s.student_plain.username, s.student_plain.password)
    await apiGetJson('/api/dashboard', studentToken)
    await apiPostJson('/api/notifications', teacherToken, {
      title: `future_counter_${Date.now()}`,
      content: 'counter audit',
      priority: 'normal',
      is_pinned: false,
      class_id: s.class_id_1,
      subject_id: s.course_required_id
    })
    // Future intent:
    // run create-edit-delete notification loop and assert student unread badge converges to zero stale increments.
  })

  test.skip('22. admin orphan user and roster sync race does not create duplicate student rows after repeated reconcile triggers', async ({ browser }) => {
    const s = scenario()
    const adminPage = await browser.newPage()
    await login(adminPage, s.admin.username, s.admin.password)
    await adminPage.goto('/users')
    // Future intent:
    // create a user in one tab and trigger roster sync from another stale state,
    // then repeat reconcile, asserting one student row and one user linkage only.
  })

  test.skip('23. teacher score composition formula change during open student score page converges to one computed total everywhere', async ({ browser }) => {
    const s = scenario()
    const teacherPage = await browser.newPage()
    const studentPage = await browser.newPage()
    await login(teacherPage, s.teacher_own.username, s.teacher_own.password)
    await login(studentPage, s.student_plain.username, s.student_plain.password)
    await enterSeededRequiredCourse(teacherPage, s.suffix)
    await studentPage.goto('/scores')
    // Future intent:
    // mutate exam weights while student score view is stale,
    // verify final totals, labels, and backend composition all converge to the new scheme.
  })

  test.skip('24. teacher materials attachment replace under flaky network leaves one downloadable file and no stale section reference', async ({ page }) => {
    const s = scenario()
    await login(page, s.teacher_own.username, s.teacher_own.password)
    await enterSeededRequiredCourse(page, s.suffix)
    await page.goto('/materials')
    // Future intent:
    // fail first material attachment upload, retry with second file, then reorder sections,
    // assert final section points to one real file only.
  })

  test.skip('25. student stale selected elective course after backend block insertion loses self-enroll affordance without leaking old action button', async ({ page }) => {
    const s = scenario()
    const adminToken = await obtainAccessToken(s.admin.username, s.admin.password)
    await login(page, s.student_plain.username, s.student_plain.password)
    await page.goto('/courses')
    // Future intent:
    // backend inserts CourseEnrollmentBlock while student catalog page is stale,
    // assert action button disappears or safely fails and final catalog state matches block policy.
    await apiGetJson('/api/users', adminToken)
  })

  test.skip('26. teacher bulk attendance plus notification publish from parallel tabs preserves one attendance batch and one notification fanout', async ({ browser }) => {
    const s = scenario()
    const pageA = await browser.newPage()
    const pageB = await browser.newPage()
    await login(pageA, s.teacher_own.username, s.teacher_own.password)
    await login(pageB, s.teacher_own.username, s.teacher_own.password)
    await enterSeededRequiredCourse(pageA, s.suffix)
    await enterSeededRequiredCourse(pageB, s.suffix)
    await pageA.goto('/attendance')
    await pageB.goto('/notifications')
    // Future intent:
    // commit attendance and course notification in parallel and verify fanout plus attendance persistence remain isolated and complete.
  })

  test.skip('27. admin repeated demo-seed reset during active browser session forces safe re-login instead of cross-scenario data bleed', async ({ browser }) => {
    const s = scenario()
    const adminToken = await obtainAccessToken(s.admin.username, s.admin.password)
    const adminPage = await browser.newPage()
    await login(adminPage, s.admin.username, s.admin.password)
    await adminPage.goto('/dashboard')
    await apiPostJson('/api/e2e/dev/reset-scenario', null, {}).catch(() => {})
    await apiGetJson('/api/auth/me', adminToken)
    // Future intent:
    // while an admin session is open, a fresh E2E reset happens,
    // verify the old browser session fails safely and does not read mixed old/new seed data.
  })

  test.skip('28. student profile avatar replace and immediate logout-login across tabs converges to one final avatar URL', async ({ browser }) => {
    const s = scenario()
    const ctxA = await browser.newContext()
    const ctxB = await browser.newContext()
    const pageA = await ctxA.newPage()
    const pageB = await ctxB.newPage()
    await login(pageA, s.student_plain.username, s.student_plain.password)
    await login(pageB, s.student_plain.username, s.student_plain.password)
    await pageA.goto('/personal-settings')
    await pageB.goto('/dashboard')
    // Future intent:
    // replace avatar in one tab, logout/login in another immediately,
    // assert one final avatar survives and stale cache does not revert profile media.
  })

  test.skip('29. teacher pinned notification reorder and unpin race leaves deterministic final ordering in student list', async ({ browser }) => {
    const s = scenario()
    const teacherPageA = await browser.newPage()
    const teacherPageB = await browser.newPage()
    const studentPage = await browser.newPage()
    await login(teacherPageA, s.teacher_own.username, s.teacher_own.password)
    await login(teacherPageB, s.teacher_own.username, s.teacher_own.password)
    await login(studentPage, s.student_plain.username, s.student_plain.password)
    await teacherPageA.goto('/notifications')
    await teacherPageB.goto('/notifications')
    await studentPage.goto('/notifications')
    // Future intent:
    // pin/unpin and reorder notifications from two stale teacher tabs,
    // assert student final list ordering is deterministic and not duplicated.
  })

  test.skip('30. teacher stale homework grade candidate page after manual score override does not resurrect obsolete candidate on save', async ({ browser }) => {
    const s = scenario()
    const teacherPageA = await browser.newPage()
    const teacherPageB = await browser.newPage()
    await login(teacherPageA, s.teacher_own.username, s.teacher_own.password)
    await login(teacherPageB, s.teacher_own.username, s.teacher_own.password)
    await enterSeededRequiredCourse(teacherPageA, s.suffix)
    await enterSeededRequiredCourse(teacherPageB, s.suffix)
    await teacherPageA.goto('/homework')
    await teacherPageB.goto('/homework')
    // Future intent:
    // tab A opens candidate review, tab B applies manual override, tab A saves stale candidate,
    // assert final authoritative score remains the override and stale candidate is not resurrected.
  })
})
