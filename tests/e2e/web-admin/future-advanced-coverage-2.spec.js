const { test } = require('@playwright/test')
const { resetE2eScenario } = require('./fixtures.cjs')
const { backlogScenario, describeBacklogSuite } = require('./backlog-e2e.cjs')

describeBacklogSuite('Future advanced E2E coverage expansion II', () => {
  test.describe.configure({ timeout: 180_000 })

  test.beforeEach(async ({}, testInfo) => {
    const s = await resetE2eScenario()
    if (!s) {
      testInfo.skip(true, 'Missing e2e seed cache; run globalSetup with E2E_DEV_SEED_TOKEN first')
    }
  })

  backlogScenario(
    '16. teacher stale dual-tab material publish versus delete converges to one surviving material record'
  )
  backlogScenario(
    '17. student stale homework detail page after teacher unpublish shows safe recovery instead of broken submit state'
  )
  backlogScenario(
    '18. admin class rename during teacher active course session updates downstream labels without changing course identity'
  )
  backlogScenario(
    '19. teacher assignment of per-course LLM policy while worker is already processing leaves old task on old config and new task on new config'
  )
  backlogScenario(
    '20. student and parent concurrent homework visibility after appeal reopen stays consistent with permissions'
  )
  backlogScenario(
    '21. teacher rapid create-edit-delete notification sequence leaves no duplicate unread counters in student dashboard'
  )
  backlogScenario(
    '22. admin orphan user and roster sync race does not create duplicate student rows after repeated reconcile triggers'
  )
  backlogScenario(
    '23. teacher score composition formula change during open student score page converges to one computed total everywhere'
  )
  backlogScenario(
    '24. teacher materials attachment replace under flaky network leaves one downloadable file and no stale section reference'
  )
  backlogScenario(
    '25. student stale selected elective course after backend block insertion loses self-enroll affordance without leaking old action button'
  )
  backlogScenario(
    '26. teacher bulk attendance plus notification publish from parallel tabs preserves one attendance batch and one notification fanout'
  )
  backlogScenario(
    '27. admin repeated demo-seed reset during active browser session forces safe re-login instead of cross-scenario data bleed'
  )
  backlogScenario(
    '28. student profile avatar replace and immediate logout-login across tabs converges to one final avatar URL'
  )
  backlogScenario(
    '29. teacher pinned notification reorder and unpin race leaves deterministic final ordering in student list'
  )
  backlogScenario(
    '30. teacher stale homework grade candidate page after manual score override does not resurrect obsolete candidate on save'
  )
})
