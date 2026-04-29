# 测试说明

本仓库包含两类自动化测试：

- 后端 `pytest`：覆盖接口、业务规则和部分行为级逻辑。
- 前端 `Playwright E2E`：从真实浏览器登录和点击开始，必要时再用 API 校验最终后端状态。

两者分工不同。`pytest` 更适合局部规则和分支覆盖，E2E 更适合验证多角色、多步骤、异步和并发场景下系统最终是否收敛到正确状态。

## 后端测试

在仓库根目录安装依赖并运行：

```bash
pip install -r requirements.txt
pytest
```

重点目录：

- `tests/`
- `tests/behavior/`
- `tests/test_*`

## 前端 E2E

目录：

- `frontend/e2e/`

主要配置：

- `frontend/playwright.config.cjs`

运行方式：

```bash
cd frontend
npm ci
npx playwright install chromium
npm run test:e2e
```

### 环境说明

- Playwright 会自动拉起 FastAPI 和 Vite。
- 默认端口：
  - API：`127.0.0.1:8012`
  - UI：`127.0.0.1:3012`
- `globalSetup` 会调用 `POST /api/e2e/dev/reset-scenario` 重置隔离种子数据。
- 场景缓存写入 `frontend/e2e/.cache/scenario.json`。

### Windows 说明

- Playwright 已支持原生 Windows 启动，不再依赖 `bash -lc`。
- Windows 下 E2E SQLite 写到当前用户临时目录，而不是 `/tmp`。
- 优先使用仓库内 `.venv\Scripts\python.exe` 作为 API 解释器。
- Windows 需要 `tzdata`，否则课程 LLM 配置等涉及时区的接口可能报 `ZoneInfoNotFoundError`。

## 当前 E2E 覆盖

现有高强度用例主要集中在：

- `frontend/e2e/e2e-scenario-resilience.spec.js`

这份 spec 当前覆盖了 31 条高价值场景，核心类别包括：

- 教师并发编辑同一作业，最终状态只能收敛到一个 authoritative 版本
- 创建作业、发通知、提交作业在首次失败后的重试幂等性
- 学生在会话中被调班后，课程访问、花名册、选课关系的同步失效与恢复
- 教师花名册弹窗、学生选课/退选在双标签页或多上下文下的并发一致性
- 成绩申诉、作业申诉在并发下只允许出现一条有效 pending 记录
- 课程 LLM 配置在默认值缺失、保存失败时的恢复能力
- 学生深链路进入 `/homework`、`/student-scores`、`/notifications` 时的课程上下文自动恢复
- 个人资料、密码、通知已读状态在多标签页和失败重试下的最终一致性

## 这轮测试中暴露出的真实坑

这部分记录“测试不是为了证明一切正常，而是实际打出来过的问题”。

### 1. 学生深链路依赖 `selected_course`，无上下文时会被错误重定向

现象：

- 学生 fresh login 后直接进入 `/homework/:id/submit`、`/student-scores`、`/notifications` 等页面时，前端可能因为本地没有 `selected_course` 而被过早跳回 `/courses`。

处理：

- 路由守卫先尝试 `ensureSelectedCourse()` 自动恢复课程上下文，再决定是否重定向。

涉及文件：

- `frontend/src/router/index.js`

### 2. 并发作业申诉会撞唯一约束并泄漏成 500

现象：

- 两个陈旧页面或两个并发请求同时对同一 submission 发起申诉时，后端可能在 `flush()` 阶段撞上唯一约束，返回 500。

处理：

- 将唯一约束冲突转成显式的 400 幂等冲突响应。

涉及文件：

- `app/routers/homework.py`

### 3. 并发成绩申诉原本没有数据库级防重，容易出现双 pending

现象：

- 仅靠“先查再写”不足以防止并发；两个请求可以同时通过存在性检查，然后各自插入 pending 申诉。

处理：

- 增加部分唯一索引，只允许同一学生、同一课程、同一学期、同一 component 存在一条 `pending` 申诉。
- 冲突时返回 400，而不是 500。

涉及文件：

- `app/bootstrap.py`
- `app/routers/scores.py`

### 4. 学生选课/退选在并发下会撞唯一约束或出现状态抖动

现象：

- 两个学生页面同时自选同一选修课，或同时退选同一选修课，原逻辑缺少并发容错。
- 花名册加人同样存在同类问题。

处理：

- `student-self-enroll`、`student-self-drop`、`roster-enroll` 补了 `IntegrityError` 处理，改成幂等收敛。

涉及文件：

- `app/routers/subjects.py`

### 5. 通知已读状态在双标签页下可能重复写入

现象：

- 两个页面同时点开同一通知或同时执行“全部标为已读”，`notification_reads` 可能发生重复插入竞争。

处理：

- 增加 `(notification_id, user_id)` 唯一索引。
- `mark_as_read` / `mark_all_as_read` 出现并发冲突后改为回滚并重读收敛。

涉及文件：

- `app/bootstrap.py`
- `app/routers/notifications.py`

### 6. Windows 测试环境并不是“依赖装完就能跑”

现象：

- 原始 Playwright 配置偏向 Linux/WSL，Windows 下会卡在 shell/path 行为上。
- 时区数据缺失会让部分 LLM 配置接口直接失败。

处理：

- Playwright 启动链改成 Windows 可用。
- `requirements.txt` 补 `tzdata`。

涉及文件：

- `frontend/playwright.config.cjs`
- `requirements.txt`

## 系统潜在风险

这些不一定都已复现成当前 bug，但从这轮测试和代码形态看，后续值得持续关注。

### 1. 账号身份与花名册绑定仍然脆弱

- 学生账号的 `username`、`class_id`、`Student.student_no`、`CourseEnrollment` 强耦合。
- 这类链路很容易在“中途改学号/改班级/批量导入”时出现缓存与真实数据脱节。

### 2. 前端大量页面仍依赖本地缓存的课程上下文

- `selected_course` 恢复逻辑已经补了一层，但更多深链路仍可能受 stale localStorage 影响。
- 后续任何新增学生页面，都应该默认带“无上下文启动”和“脏缓存启动”测试。

### 3. 幂等性目前是按热点接口补的，不是系统性设计

- 已经修过的接口包括作业申诉、成绩申诉、选课、退选、通知已读。
- 其他写接口若仍采用“先查再写”模式，在并发下仍可能暴露同类问题。

### 4. LLM 相关链路仍是最高风险区

- 现在已覆盖的是“配置保存失败”和部分默认值。
- 真正高风险的是评分任务执行过程里的 timeout、非法响应、重试退避、额度竞争、任务卡死和轮询恢复。

### 5. 测试代码本身也会因文案/编码/定位器策略变脆

- 这轮有一个失败并不是产品 bug，而是测试里课程名字符串被编码污染，导致定位器找错文本。
- 对复杂场景应优先用稳定的 `data-testid`、结构定位或后端最终态校验，不要过度依赖中文展示文案。

## 后续测试方向

更完整的复杂场景草案见：

- `docs/E2E_COMPLEX_SCENARIOS.md`

下一波优先级最高的方向：

### 1. 学生账号改学号 / 改用户名后的全链路一致性

- 旧 token 是否失效
- 新账号重新登录后课程是否仍然正确
- 花名册、成绩、作业、通知 target 是否仍指向正确学生

### 2. LLM 执行期失败矩阵

- timeout
- 429 / 配额耗尽
- 5xx
- 非 JSON
- 空响应
- 部分成功后轮询失败

### 3. 长链路异步恢复

- 提交成功但刷新失败
- 后台任务成功但前端轮询丢失
- 用户手动刷新或重登后能否恢复 authoritative 状态

### 4. 冷启动 / 半初始化 / 脏迁移数据

- 可选字段缺失
- 老数据只有部分新字段
- 默认值自动补齐是否稳定

### 5. 更多真正的多用户并发

- 管理员批量改班与教师批量加课同时发生
- 教师改课程、学生正在选课、家长端同时读数据
- 双教师或教师+管理员同时编辑同一实体

## 建议

- 新增重要写接口时，默认补一条“重复提交 / 并发提交 / stale page 再提交”的用例。
- 新增学生页面时，默认补“fresh login 无课程上下文”和“stale selected_course 缓存”两条用例。
- 新增异步任务时，默认补“首次失败后恢复”和“轮询中断后恢复”用例。
- 对真正需要幂等的写路径，优先同时加数据库唯一约束和接口层冲突处理，不只写前端防抖。
