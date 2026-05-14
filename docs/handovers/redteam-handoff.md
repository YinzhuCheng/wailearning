# Red-Team Handoff

## 1. 当前仓库状态

- 当前分支：`cursor/repository-normalization-schema-notifications`
- 当前 HEAD：`fa13b11`
- 工作区是否干净：不干净
- 未提交文件列表：
  - `apps/web/school/src/stores/user.js`
  - `apps/web/school/src/views/Scores.vue`
  - `docs/handoffs/APPEAL_NOTIFICATION_SYSTEM_HARDENING_HANDOFF_2026-05-14.md`
  - `docs/testing/agent-update-log.csv`
  - `tests/e2e/web-school/e2e-scenario-resilience.spec.js`
- diff stat 摘要：本轮状态检查时 `git diff --stat` 与 `git diff --name-only` 没有返回可见输出，但 `git status --short --branch` 明确显示以上 5 个文件处于修改状态，因此后续 agent 需要先以 `git diff <path>` 逐文件复核。
- 是否有新增文件：
  - 本轮新增了 `docs/handovers/redteam-handoff.md`
  - `git ls-files --others --exclude-standard` 本轮未返回可见输出，因此未发现其他未跟踪新增文件
- 是否有已提交但未推送的提交：未发现。`git rev-list --left-right --count origin/cursor/repository-normalization-schema-notifications...HEAD` 返回 `0 0`。
- 是否有已推送但仍需 review 的提交：
  - 很可能有。当前 `HEAD` 已与远端同位，但最近提交包含多轮围绕 `Scores.vue` / `e2e-scenario-resilience.spec.js` 的 red-team 与修复工作：
    - `fa13b11 fix: harden score appeal recovery states`
    - `44cad69 test: close out score appeal deep-link recovery`
    - `f52dce3 fix: harden score appeal deep-link recovery`
  - 是否已被人工 review，本轮无证据确认。

## 2. 前几轮工作概述

### A. Appeal notification / score-appeal deep-link 相关前端逻辑

- 实际做了什么：
  - 在 `apps/web/school/src/views/Scores.vue` 里新增了多轮恢复/降级逻辑，试图处理：
    - 外部课程 `subject_id` deep-link
    - 缺失课程上下文 warning
    - 手动切换课程后的恢复
    - accessible course + missing `appeal_id` 的提示
    - “继续使用当前课程”显式恢复入口
  - 在 `apps/web/school/src/stores/user.js` 增加了 `selectedCourseRevision`。
- 证据来源：
  - 当前未提交 diff
  - `git log --oneline -5`
- 代码阅读：[Scores.vue](../../apps/web/school/src/views/Scores.vue)、[user.js](../../apps/web/school/src/stores/user.js)
- 备注：
  - 这些修改明显来自多轮持续收敛，不是一次性完成。
  - 当前工作区仍有未提交补丁，后续 agent 必须先确认这些补丁是否自洽。

### B. Browser red-team / focused Playwright 回归

- 实际做了什么：
  - 在 `tests/e2e/web-school/e2e-scenario-resilience.spec.js` 持续追加 focused 场景，主要围绕：
    - foreign-course score-appeal deep-link 不应落错课程
    - 手动切换到另一门课程后的恢复
    - 恢复后 reload / 局部 refresh 不应复毒
    - 显式“继续使用当前课程”恢复
    - accessible course + missing `appeal_id` 不应被静默当成成功定位
- 证据来源：
  - 当前未提交 diff
- 代码阅读：[e2e-scenario-resilience.spec.js](../../tests/e2e/web-school/e2e-scenario-resilience.spec.js)
  - 交接文档：[APPEAL_NOTIFICATION_SYSTEM_HARDENING_HANDOFF_2026-05-14.md](../handoffs/APPEAL_NOTIFICATION_SYSTEM_HARDENING_HANDOFF_2026-05-14.md)
  - `docs/testing/agent-update-log.csv`
- 备注：
  - 上下文不足以精确还原每一轮红队覆盖了哪些全部面；只能从测试文件新增用例、hand-off 叙述、update-log 行判断其大致攻击目标。

### C. 文档/治理同步

- 实际做了什么：
  - 多次更新 `docs/handoffs/APPEAL_NOTIFICATION_SYSTEM_HARDENING_HANDOFF_2026-05-14.md`
  - 多次追加 `docs/testing/agent-update-log.csv`
- 证据来源：
  - 当前未提交修改
  - 代码阅读
  - `git log --oneline -5`
- 备注：
  - `agent-update-log.csv` 当前尾部存在重复 `update_sequence=61` 的两行，这说明 ledger 可能已经出现需要人工整理的历史重复。

## 3. 已确认问题

### 问题标题
- foreign-course score-appeal deep-link 可将页面带入错误课程上下文

- 影响范围：
  - `apps/web/school/src/views/Scores.vue`
  - 老师端 `/scores?subject_id=...&appeal_id=...`

- 证据：
  - 先前 focused Playwright grep 在旧版本上失败，随后相关修复已进入提交历史与 handoff 叙述
  - 见提交 `f52dce3` / `44cad69`

- 复现方式或触发条件：
  - deep-link 的 `subject_id` 指向当前老师不可访问课程

- 是否已修复：
  - 看起来已修复，但本轮未复验该旧问题的完整回归，只能引用前轮 focused 证据

- 修复涉及文件：
  - `apps/web/school/src/views/Scores.vue`
  - `tests/e2e/web-school/e2e-scenario-resilience.spec.js`

- 是否有测试覆盖：
  - 有 focused Playwright 覆盖
  - 本轮未复验

- 剩余风险：
  - 后续恢复逻辑已经继续扩张，旧回归仍应复验，避免新补丁把旧 fix 覆盖掉

### 问题标题
- 手动切换到另一门可访问课程后，坏 deep-link warning 仍可能把老师困住

- 影响范围：
  - `apps/web/school/src/views/Scores.vue`
  - Header course switcher 与 `/scores` deep-link 恢复链

- 证据：
  - focused Playwright grep 先失败，再在同一攻击场景下通过
  - handoff 与 update-log 已明确记录此问题

- 复现方式或触发条件：
  - 进入 foreign-course score-appeal deep-link warning 状态
  - 手动切到另一门可访问课程

- 是否已修复：
  - 看起来已修复，但本轮未重新复验这条旧问题的 focused 用例；仅能依赖前轮记录

- 修复涉及文件：
  - `apps/web/school/src/views/Scores.vue`
  - `tests/e2e/web-school/e2e-scenario-resilience.spec.js`

- 是否有测试覆盖：
  - 有 focused Playwright 覆盖
  - 本轮未复验

- 剩余风险：
  - 当前恢复链已经依赖更多状态变量，旧用例仍应复验

### 问题标题
- accessible course + missing `appeal_id` 会被静默当成普通列表，而不是提示目标申诉不存在

- 影响范围：
  - `apps/web/school/src/views/Scores.vue`
  - 老师端成绩申诉 deep-link

- 证据：
  - 本轮实际运行的 focused Playwright grep：
    `teacher score-appeal deep-link with a missing appeal_id inside an accessible course is not silently treated as a successful locate`
    修复前失败，修复后通过
  - 当前代码中新增了 `missingAppealTargetContext` 与 `scores-appeal-target-missing`

- 复现方式或触发条件：
  - `subject_id` 指向可访问课程
  - `appeal_id` 不存在、失效，或不在该课程范围内

- 是否已修复：
  - 看起来已修复

- 修复涉及文件：
  - `apps/web/school/src/views/Scores.vue`
  - `tests/e2e/web-school/e2e-scenario-resilience.spec.js`
  - `docs/handoffs/APPEAL_NOTIFICATION_SYSTEM_HARDENING_HANDOFF_2026-05-14.md`
  - `docs/testing/agent-update-log.csv`

- 是否有测试覆盖：
  - 有，本轮 focused Playwright 单例已通过

- 剩余风险：
  - 仅证明了“warning 出现”，未证明所有 related query/path 组合都能一致处理

## 4. 高置信风险

### 风险标题
- “继续使用当前课程”显式恢复入口缺少干净 focused 绿证据

- 为什么怀疑它存在：
  - 当前代码已加入 `scores-appeal-use-current-course`
  - 但相关 focused Playwright 多次落入 runner 挂起/超时，没有形成稳定通过证据

- 目前缺少什么证据：
  - 单条 focused 场景在 5 分钟窗口内稳定通过
  - 明确断言点击按钮后 warning 消失、URL 清理、页面可继续工作的证据

- 建议后续如何验证：
  - 单独跑：
    `node scripts/playwright-external-runner.cjs e2e-scenario-resilience.spec.js --project=chromium --grep "teacher explicit current-course recovery button clears a foreign score-appeal deep-link warning"`
  - 如仍挂起，先缩小测试步骤并确认是产品卡住还是 runner/selector 卡住

- 如果验证为真，建议修复方向：
  - 不要继续依赖全局 `selectedCourseRevision` 或复杂 watcher 互相驱动
  - 优先把“显式恢复”做成单一动作：清 stale query、清 warning 状态、刷新当前课程数据

### 风险标题
- `Scores.vue` 恢复链已演化为局部状态机，存在半截补丁或状态冲突风险

- 为什么怀疑它存在：
  - 当前页面同时维护：
    - `missingAppealCourseContext`
    - `missingAppealRouteKey`
    - `recoveredFromMissingAppealRoute`
    - `missingAppealCourseSelectionSnapshot`
    - `missingAppealTargetContext`
  - 并且同时监听 route、selected course revision、手动按钮

- 目前缺少什么证据：
  - 完整状态迁移图
  - 多场景全量回归

- 建议后续如何验证：
  - 先做代码级状态迁移复查
  - 再逐个 focused 场景重跑，而不是直接 full scenario_resilience

- 如果验证为真，建议修复方向：
  - 抽成独立 helper/composable
  - 把 “course missing / target missing / explicit recover” 三类状态明确建模

### 风险标题
- `selectedCourseRevision` 可能引入跨页面隐式耦合

- 为什么怀疑它存在：
  - store 新增了全局 revision 计数器
  - 当前只有 `Scores.vue` 明确消费，但后续页面可能开始复用

- 目前缺少什么证据：
  - 没有其他消费者并不等于未来不会扩散
  - 没有防误用约束

- 建议后续如何验证：
  - grep 所有 `selectedCourseRevision`
  - 如只有单一消费者，考虑把它内聚回局部恢复 helper

- 如果验证为真，建议修复方向：
  - 改成局部恢复事件机制，避免全局 store 状态承担页面级恢复语义

## 5. 未验证或测试情况未知的部分

- 哪些测试没有运行：
  - 本轮没有运行完整 `school.e2e.scenario_resilience`
  - 没有运行 `school.e2e.full`
  - 没有运行 backend pytest 作为本轮回归
  - 没有运行 `npm run test:appeals`

- 哪些测试运行过但本轮没有复验：
  - foreign-course deep-link 不落错课程
  - 手动切到另一门课程后恢复
  - 恢复后 reload 不复毒
  - 恢复后局部 refresh 不复毒

- 哪些测试依赖环境，当前环境是否准备好未知：
  - 所有 focused Playwright 依赖 external runner、seed/reset、Vite、uvicorn、本地 sqlite
  - 当前环境显然可启动 runner，但对某些 focused 场景是否能稳定收敛未知

- 哪些行为只靠代码阅读判断，没有执行验证：
  - `selectedCourseRevision` 对显式恢复入口的真实帮助
  - “继续使用当前课程”按钮是否稳定可用
  - 其他页面是否会被 `selectedCourseRevision` 影响

- 哪些 E2E、浏览器、多用户、多 tab、刷新、返回、并发、权限、数据迁移、兼容性场景没有覆盖：
  - “继续使用当前课程”按钮在 reload/back/forward 后的行为
  - 多 tab 下一个 tab 恢复、另一个 tab 仍带旧 query 的行为
  - 非老师角色如果以后进入同类 query，是否有一致处理
  - 与浏览器前进/后退缓存联合时的恢复
  - 权限变化中途发生时的恢复链
  - 兼容性：Element Plus dropdown 对“重选当前项”事件语义未被真正验证

## 6. 已运行命令和结果

- `git -C C:\Users\bloom\wailearning status --short`
  - 工作目录：`C:\Users\bloom`
  - 结果：通过
  - 结论：当前工作区存在修改，但部分调用未显示可见内容；后续用文件读取确认了修改文件

- `git -C C:\Users\bloom\wailearning branch --show-current`
  - 工作目录：`C:\Users\bloom`
  - 结果：通过
  - 结论：当前分支 `cursor/repository-normalization-schema-notifications`

- `git -C C:\Users\bloom\wailearning rev-parse --short HEAD`
  - 工作目录：`C:\Users\bloom`
  - 结果：通过
  - 结论：`fa13b11`

- `git -C C:\Users\bloom\wailearning diff --stat`
  - 工作目录：`C:\Users\bloom`
  - 结果：未知
  - 关键情况：多次调用未返回可见输出，但 `status` 与文件读取证明工作区并非干净

- `git -C C:\Users\bloom\wailearning diff --check`
  - 工作目录：`C:\Users\bloom`
  - 结果：通过
  - 关键结论：无 diff whitespace 错误；仅出现 `agent-update-log.csv` 的 LF/CRLF warning

- `git -C C:\Users\bloom\wailearning log --oneline -5`
  - 工作目录：`C:\Users\bloom`
  - 结果：通过
  - 关键结论：最近五个提交见本文状态章节

- `git -C C:\Users\bloom\wailearning status --short --branch`
  - 工作目录：`C:\Users\bloom`
  - 结果：通过
  - 关键结论：与远端无 ahead/behind；工作区有未提交修改

- `git -C C:\Users\bloom\wailearning rev-list --left-right --count origin/cursor/repository-normalization-schema-notifications...HEAD`
  - 工作目录：`C:\Users\bloom`
  - 结果：通过
  - 关键结论：`0 0`

- `Test-Path C:\Users\bloom\wailearning\docs\handovers`
  - 工作目录：`C:\Users\bloom`
  - 结果：通过
  - 关键结论：最初不存在

- `Get-Content` 读取：
  - `AGENTS.md`
  - `docs/handoffs/APPEAL_NOTIFICATION_SYSTEM_HARDENING_HANDOFF_2026-05-14.md`
  - `docs/testing/agent-update-log.csv`
  - `apps/web/school/src/views/Scores.vue`
  - `apps/web/school/src/stores/user.js`
  - `tests/e2e/web-school/e2e-scenario-resilience.spec.js`
  - 结果：通过
  - 关键结论：用于重建当前修改面和前几轮上下文

- `python ops/scripts/dev/select_validation_targets.py --paths tests/e2e/web-school/e2e-scenario-resilience.spec.js --json`
  - 工作目录：`C:\Users\bloom\wailearning`
  - 结果：通过
  - 关键结论：selector 仅推荐 `school.e2e.scenario_resilience` broad target

- `python ops/scripts/dev/check_docs_governance.py`
  - 工作目录：`C:\Users\bloom\wailearning`
  - 结果：通过
  - 关键结论：`No governance findings.`

- `python ops/scripts/dev/check_text_encoding.py ...`
  - 工作目录：`C:\Users\bloom\wailearning`
  - 结果：通过
  - 关键结论：`decode_errors=0 suspicious=0`

- `npm.cmd run build`
  - 工作目录：`C:\Users\bloom\wailearning\apps\web\school`
  - 结果：通过
  - 关键结论：Vite build 完成；存在既有 chunk-size warning 与 Vite CJS deprecation warning

- `node scripts/playwright-external-runner.cjs e2e-scenario-resilience.spec.js --project=chromium --grep "teacher score-appeal deep-link with a missing appeal_id inside an accessible course is not silently treated as a successful locate"`
  - 工作目录：`C:\Users\bloom\wailearning\apps\web\school`
  - 结果：先失败，后通过
  - 失败关键错误：`scores-appeal-target-missing` 不存在
  - 最终结论：该问题被本轮修复后，单例 focused Playwright 通过

- `node scripts/playwright-external-runner.cjs e2e-scenario-resilience.spec.js --project=chromium --grep "teacher explicit current-course recovery button clears a foreign score-appeal deep-link warning"`
  - 工作目录：`C:\Users\bloom\wailearning\apps\web\school`
  - 结果：未知 / 超时
  - 关键情况：runner 在当前窗口内未给出干净终态

- `node scripts/playwright-external-runner.cjs e2e-scenario-resilience.spec.js --project=chromium --grep "teacher can recover from a foreign score-appeal deep-link by explicitly re-selecting the same current accessible course"`
  - 工作目录：`C:\Users\bloom\wailearning\apps\web\school`
  - 结果：先失败，后未知/超时
  - 失败关键错误：warning 仍存在
  - 当前结论：这条路径不应被视为已验证完成

## 7. 当前修改文件说明

### `apps/web/school/src/stores/user.js`

- 修改目的：
  - 增加 `selectedCourseRevision`，为 `Scores.vue` 区分“用户显式重新选择课程”提供信号
- 修改是否完整：
  - 未知
  - 逻辑上可用，但是否为最终方案未确认
- 是否需要后续 agent 复查：
  - 需要
- 相关测试：
  - 仅间接依赖 focused Playwright
- 风险等级：中

### `apps/web/school/src/views/Scores.vue`

- 修改目的：
  - 增加 deep-link 恢复状态机
  - 区分课程上下文缺失与申诉目标缺失
  - 增加 `继续使用当前课程` 恢复入口
- 修改是否完整：
  - 可能是半截补丁
  - 其中“显式恢复按钮”路径仍缺干净 focused 绿证据
- 是否需要后续 agent 复查：
  - 强烈需要
- 相关测试：
  - `tests/e2e/web-school/e2e-scenario-resilience.spec.js`
  - `npm.cmd run build`
- 风险等级：高

### `tests/e2e/web-school/e2e-scenario-resilience.spec.js`

- 修改目的：
  - 追加 focused browser red-team 场景
- 修改是否完整：
  - 不完全确定
  - 文件已很大，新增场景较多，容易与历史失败/超时混在一起
- 是否需要后续 agent 复查：
  - 强烈需要
- 相关测试：
  - 文件自身的 focused Playwright grep
- 风险等级：高

### `docs/handoffs/APPEAL_NOTIFICATION_SYSTEM_HARDENING_HANDOFF_2026-05-14.md`

- 修改目的：
  - 记录前几轮红队命中的问题与修复意图
- 修改是否完整：
  - 不完整
  - 当前文档包含多轮叙述，但未必与当前工作区最终状态一致
- 是否需要后续 agent 复查：
  - 需要
- 相关测试：
  - 无直接测试，仅文档
- 风险等级：中

### `docs/testing/agent-update-log.csv`

- 修改目的：
  - 记录最近几轮更新摘要
- 修改是否完整：
  - 不确定
  - 当前尾部出现重复 `update_sequence=61`
- 是否需要后续 agent 复查：
  - 强烈需要
- 相关测试：
  - 本轮未跑 `static.validation_selector`
- 风险等级：中

### `docs/handovers/redteam-handoff.md`

- 修改目的：
  - 保存当前交接上下文
- 修改是否完整：
  - 本轮交接文档本身是完整的，但基于当前可见证据
- 是否需要后续 agent 复查：
  - 建议阅读后再开始下一轮
- 相关测试：
  - 无
- 风险等级：低

## 8. 设计判断与产品规则空白

- foreign-course `subject_id` + valid `appeal_id` 时，应该：
  - 直接警告并停在空态
  - 自动跳回某个安全列表页
  - 还是允许老师显式选择恢复路径
  - 当前实现选择了 warning + 恢复动作，但是否是最终产品规则未知

- accessible course + missing `appeal_id` 时，应该：
  - 展示目标缺失 notice
  - 自动清 query 并只显示普通列表
  - 还是跳回通知页
  - 当前实现选择了 notice + 保留当前课程列表，但这属于实现判断，不一定是产品定稿

- “继续使用当前课程”是否应视为显式覆盖坏 deep-link：
  - 当前实现默认是
  - 但产品是否希望保留原始 deep-link 参考入口未知

- 重选同一门当前课程是否也应自动恢复：
  - 当前有高置信风险，但未验证收口
  - 属于 spec ambiguity 与交互定义空白，不应直接当作已修复

- terminal / readonly / actionable 状态下，列表页是否还应强调“目标申诉不存在”：
  - 当前只做了 target-missing notice
  - 未证明与其它申诉状态标签/操作语义完全一致

## 9. 建议后续 agents 的接手路线

- P0：先恢复可验证基线，确认工作区、构建、核心测试状态
  - 先读本交接文档
  - 重新跑 `git status --short --branch`
  - 逐文件看 diff，而不是只看 `git diff --stat`
  - 先确认当前工作区是否真的是 5 个修改文件

- P1：复查当前 diff，确认是否有半截补丁、重复函数、编码污染、未接入 helper、未被测试覆盖的修改
  - 重点复查 `Scores.vue`
  - 重点复查 `selectedCourseRevision` 的作用范围
  - 检查 `agent-update-log.csv` 重复序号

- P2：复验已确认 bug 的回归测试
  - 先复验 accessible course + missing `appeal_id` 这条 focused 绿用例
  - 再复验 foreign-course deep-link 不落错课程
  - 再复验 manual switch to another course recovery

- P3：针对高置信风险补最小可复现测试
  - 重点是 `scores-appeal-use-current-course`
  - 必须把场景缩到 5 分钟内能给出 pass/fail 终态

- P4：再修复被测试证实的问题
  - 如果“继续使用当前课程”真的有问题，再修
  - 如果 `selectedCourseRevision` 带来副作用，再修

- P5：最后考虑结构性重构、抽象收敛或 UX 统一
  - 只在 P0-P4 完成后考虑把恢复链抽 helper/composable

- 强制要求：
  - 后续 agents 不要跳过 P0/P1 直接继续红队

## 10. 后续 agents 的禁止事项

- 不要在未读本交接文档前继续红队
- 不要在工作区不干净且未理解 diff 时继续大改
- 不要把未验证风险写成已确认 bug
- 不要把 spec ambiguity 当成实现错误强修
- 不要只靠 grep 判定复杂行为正确
- 不要在测试状态未知时提交推送
- 不要继续复制粘贴局部判断来修系统性问题
- 不要在没有复验 build/test 的情况下声称修复完成

## 11. 建议下一轮 prompt

请先阅读 `docs/handovers/redteam-handoff.md`，不要直接继续红队。先检查当前工作区和 diff，确认未提交修改是否完整且自洽；再按交接文档里的 P0/P1 恢复测试基线，逐项区分已确认问题、高置信风险和 spec ambiguity。只有在 focused 测试能在可控时间内给出明确结果时，才继续红队或修复；如果测试范围、环境或终态仍不清楚，先补最小可验证路径，不要扩大攻击面，不要做结构性重构，也不要在测试状态未知时提交推送。
