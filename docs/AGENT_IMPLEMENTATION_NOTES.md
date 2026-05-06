# Agent / 自动化开发说明（面向 LLM 编码代理）

本文档优先服务于 **LLM agent coding system**：允许冗长、逐步、可检索的细节；人类读者若觉得过长，可只读「摘要」与小节标题。

## 摘要（人类可读）

- **部署期 LLM**：在 `.env` / `.env.production` 中设置 `INIT_LLM_BASE_URL`、`INIT_LLM_API_KEY`、`INIT_LLM_MODEL_NAME`（及可选 `INIT_LLM_PRESET_NAME`）后，首次 `bootstrap` 会：创建/更新端点预设、执行 **纯文本 + 多模态图片** 连通性探测（与管理员在 UI 中点击「校验」等效）、在探测通过时写入 **演示课程 + 默认启用课程 LLM + 示例作业开启自动评分 + 两名学生已提交（无分数）**。
- **评分要点拆分**：`rubric_text` = 学生始终可见；`rubric_teacher_text` = 仅教师与自动评分可见；`reference_answer` = 仅教师与自动评分可见，语义上为 **「参考答案或思路」**；LLM 组装提示词时已按此分层标注。
- **课程管理权限**：班主任在其班级课程列表中可使用与管理员/任课教师相同的 **编辑课程、课程封面、LLM 配置**；**删除课程**仍建议仅管理员（前端对班主任隐藏删除按钮）。
- **管理员创建 LLM 预设**：`POST /api/llm-settings/presets` 与（在关键字段变更时的）`PUT .../presets/{id}` 会在保存后 **自动执行** 文本+图片校验，无需再手动点校验（仍保留 `POST .../validate` 供复测）。

---

## 1. 环境变量：`INIT_LLM_*`（部署向导）

### 1.1 变量列表

| 变量 | 默认 | 说明 |
|------|------|------|
| `INIT_LLM_PRESET_NAME` | `deployment-primary` | 预设名称；已存在则 **更新** URL/Key/模型/超时。 |
| `INIT_LLM_BASE_URL` | 空 | OpenAI 兼容 Chat Completions 的 base（含 `/v1` 路径前缀，与现有 UI 一致）。 |
| `INIT_LLM_API_KEY` | 空 | 若为空，则 **整段 INIT_LLM 逻辑跳过**（不报错）。 |
| `INIT_LLM_MODEL_NAME` | 空 | 同上，三者缺一不可才执行。 |
| `INIT_LLM_CONNECT_TIMEOUT_SECONDS` | `10` | 连接超时。 |
| `INIT_LLM_READ_TIMEOUT_SECONDS` | `120` | 读超时。 |

### 1.2 执行时机与事务

- 在 `app.bootstrap.bootstrap()` 中，当 `INIT_DEFAULT_DATA=true` 且已完成 `seed_default_admin` 等基础种子后调用 `seed_initial_llm_deployment_bundle(db)`。
- **预设行**在探测结束后 **立即 `commit`**，避免演示课程种子失败时回滚掉已写入的 Key（便于排障）。
- 演示课程与 `CourseLLMConfig` 连接在后续步骤中 `commit`；若演示数据插入失败，预设与校验结果仍保留。

### 1.3 视觉探测使用的图片

- 与 `app.llm_grading.validate_vision_connectivity` 一致：请求体包含 **内联 `data:image/png;base64,...` 的极小 PNG**（非用户上传文件；等价于「上传一张图片做连通性检测」的协议路径）。
- 若需改为读取仓库内真实 logo 文件，应 **单一入口** 修改 `validate_vision_connectivity` 或抽取共享的「探测图」加载函数，避免 `bootstrap` 与 `llm_settings` 分叉。

### 1.4 演示数据标识（幂等）

- 班级名：`演示班级`（Unicode 在源码中以 `\u` 转义写入 `bootstrap.py`，避免部分编辑器/管道编码导致中文乱码）。
- 课程名：`演示课程（系统示例）`
- 作业标题：`示例作业（第一周）`
- 若课程已存在：仍会 **重新执行** `_wire_course_llm_from_preset`，保证升级后配置与端点链接可被修复。

---

## 2. 作业模型：`rubric_teacher_text`

### 2.1 数据库

- `homeworks.rubric_teacher_text`：`TEXT NULL`，由 `ensure_schema_updates()` 中 `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` 添加（PostgreSQL）；SQLite 走同类兼容分支。

### 2.2 API 可见性

- **学生**（`UserRole.STUDENT`）：`HomeworkResponse` 中 **`rubric_text` 保留**，`rubric_teacher_text` 与 `reference_answer` 强制为 `null`（见 `app/routers/homework.py` 中 `_serialize_homework_for_user`）。
- **教师/管理员**：完整字段。

### 2.3 LLM 提示词组装

- 文件：`app/llm_grading.py` → `_build_student_material`。
- 顺序与标签用于提醒模型：**学生可见要点 → 教师专用要点 → 参考答案或思路**；并强调勿向学生泄露后两类内容。

### 2.4 迟交、多次提交与「总评展示分」（聚合规则，面向 agent 精确复现）

#### 2.4.1 业务目标（修复前的问题）

- **旧行为（已废弃）**：`get_best_score_candidate` 仅查看 **`latest_attempt_id` 对应批次** 的 `HomeworkScoreCandidate`。若学生最后一次提交为 **迟交且开启「迟交影响评分」**，该批次 `counts_toward_final_score=false`，自动分被过滤后，**总评可能变为空**，即使此前按时提交已有高分。这与教务直觉（惩罚迟交那次，而非「吞掉历史高分」）不一致。

#### 2.4.2 新行为（当前实现）

- **聚合入口**：`app/llm_grading.py` → `get_best_score_candidate`（`refresh_submission_summary` 在每次刷新提交汇总时调用）。
- **参与聚合的候选行**（`HomeworkScoreCandidate`）必须满足：
  1. `score` 非空；且
  2. 其所属 `HomeworkAttempt` 满足 **`counts_toward_final_score == True`**（按时，或迟交但作业未开启「迟交影响评分」），**或者** 候选 `source == "teacher"`（**教师手动评分始终可参与聚合**，即使打在迟交批次上——便于教师对补交单独给分）。
- **同一 attempt 内**：与旧逻辑一致——若存在教师候选，取教师分中的最优（分数高、时间新）；否则在自动分中取最优。
- **跨 attempt**：在「每个 attempt 的代表候选」中取 **分数最高** 者；分数相同则取 **提交时间更晚** 的 attempt，再比 `attempt_id`。
- **持久化字段**：`homework_submissions.graded_best_attempt_id`（`ensure_schema_updates` 中 `ALTER TABLE ... ADD COLUMN IF NOT EXISTS graded_best_attempt_id INTEGER`）在 `refresh_submission_summary` 中写入，表示 **当前总评分数/评语所来自的 attempt**。用于前端「计入总评」标签与文案，**不必**再猜 `latest_attempt_id`。

#### 2.4.3 API 与前端契约

- **响应字段**（示意）：
  - `HomeworkSubmissionResponse.graded_attempt_id`：对应 ORM 的 `graded_best_attempt_id`。
  - `HomeworkResponse.graded_attempt_id` + `latest_submission_attempt_id`：学生作业列表可判断 **总评来源是否与最新提交不同**。
  - `HomeworkSubmissionStatusResponse.graded_attempt_id`：教师批改列表「总评来源」列。
- **学生页**：`frontend/src/views/HomeworkSubmission.vue` — 描述区说明总评来源；时间轴上对 `graded_attempt_id` 匹配项打 **「计入总评」**；若开启迟交惩罚且最新批次 ≠ 总评来源，显示 **说明性 `el-alert`**。
- **教师发布作业**：`frontend/src/views/Homework.vue` — 迟交规则下增加简短说明（自动分 vs 教师分参与总评的差异）。

#### 2.4.4 测试与易错点

- **回归用例**：`tests/test_llm_concurrency_scenarios.py::test_aggregate_score_keeps_best_counting_attempt_after_late_resubmit` — 第一次按时提交得 88 分，截止后第二次迟交自动 33 分且作业 `late_submission_affects_score=True`，断言 `GET /api/homeworks/{id}/submission/me` 的 `review_score` 仍为 **88** 且 `graded_attempt_id` 指向 **第一次 attempt**。
- **坑**：若在未来修改 `get_best_score_candidate` 时去掉 `joinedload(HomeworkScoreCandidate.attempt)`，`_candidate_eligible_for_aggregate_grade` 可能因 `attempt` 未加载而 **错误排除候选**（lazy load 在已 detach 会话时也会出问题）。应保持 **查询时预加载 attempt** 或改显式 join 条件。
- **坑**：教师给 **迟交批次** 打分时，该分数会进入聚合；若产品日后要求「教师分也仅能在计入批次上生效」，需单独开需求改 `_candidate_eligible_for_aggregate_grade`，与本文档脱钩。

---

## 3. 课程封面：`subjects.cover_image_url`

- 字符串 URL/路径，存储方式与现有附件字段一致（通常配合 `POST /api/files/upload`）。
- **权限**：沿用 `PUT /api/subjects/{id}` 既有规则（管理员任意；任课教师需 `ensure_course_access`）。
- 前端：`frontend/src/views/Subjects.vue` 中班主任视图与管理员视图 **共享** 编辑/LLM 对话框；封面在编辑表单内上传。

---

## 4. 测试与 Mock（代理易踩坑）

### 4.1 `POST /api/llm-settings/presets` 现会真实校验

- 单测若不 Mock，会对外网发起 `httpx` 请求，导致 **缓慢、不稳定或失败**。
- 对策：`tests/test_llm_settings_api.py` 使用 **`@pytest.fixture(autouse=True)`** 对 `app.routers.llm_settings.validate_text_connectivity` 与 `validate_vision_connectivity` 打桩为成功。
- **例外**：`test_cannot_bind_unvalidated_preset` 在内层 `with mock.patch(...)` 将 **vision** 设为失败，以得到「未通过视觉校验」的预设，从而断言课程绑定拒绝。

### 4.2 示意路径占位（用户要求的「坑」记录）

- **症状**：在 `<仓库根>/tests/test_llm_settings_api.py` 中，若删除对 `validate_*` 的 autouse Mock，运行 `pytest tests/test_llm_settings_api.py::test_duplicate_preset_name_400` 可能因 DNS/防火墙 **非确定性失败**。
- **症状**：在 `<仓库根>/app/bootstrap.py` 的 `seed_initial_llm_deployment_bundle` 中，若 `INIT_LLM_*` 指向不可达端点，**预设行仍会写入**且 `validation_status=failed`，演示课程 **不会** 创建；日志含 `INIT_LLM: endpoint ... did not pass vision validation`。
- **症状**：PostgreSQL 与 SQLite 对 `ADD COLUMN IF NOT EXISTS` 支持路径不同；若手工改 SQL 模板，需在 `ensure_schema_updates` 的 **SQLite 分支**同步处理，否则 CI（SQLite）与生产（PostgreSQL）会 **schema 漂移**。

### 4.3 编码与乱码

- 中文常量：在 `bootstrap.py` 中大量使用 `\uXXXX` 转义，避免在某些环境写入 UTF-8 源码时出现 **mojibake**。
- 文档与 UI 文案：编辑时请确认编辑器为 **UTF-8**，勿混用 Latin-1 粘贴。

### 4.4 专项 E2E 风格 API 用例（`tests/test_llm_course_e2e_scenarios.py`）

- **定位**：共 **15** 条用例，使用 `fastapi.testclient.TestClient` + 本仓库 `tests/conftest.py` 的 SQLite 配置，覆盖「部署期 INIT_LLM 种子、评分要点可见性、课程封面与末次写入、全局 capabilities、自动评分前置条件、课程 LLM 多组 payload 往返、智能助教门禁与聊天、无课程端点时走全局 fallback 评分、班主任布置自动评分作业、课程 LLM 关闭后再开启后允许打开自动评分」等与近期需求相关的交叉场景。
- **`INIT_LLM` 单测技巧**：直接 `monkeypatch` 修改 `app.config.settings` 的 `INIT_LLM_*` 与 `INIT_ADMIN_USERNAME`，在库中先插入对应管理员与 `semesters` 行，再对 `app.bootstrap.validate_text_connectivity` / `validate_vision_connectivity` 打桩，调用 `seed_initial_llm_deployment_bundle(db)`，避免依赖外网与完整 `bootstrap()` 副作用。
- **严重坑：不要对 `httpx.Client.post` 做全局 patch 来测 API**：Starlette/FastAPI 的 `TestClient` 底层同样使用 `httpx` 发请求；若 `unittest.mock.patch.object(httpx.Client, "post", ...)` 未区分 URL，**会把 TestClient 收到的 HTTP 响应替换成你伪造的 LLM JSON**，表现为接口「返回了 choices 而不是 `AssistantChatResponse`」的假阳性/假阴性。对策：对 **`app.routers.llm_settings.run_course_assistant_turn`**（或 `invoke_course_assistant_chat`）等业务入口打桩，或仅在 `fake_post` 内对 **chat completions URL** 分支，而对其余 URL 调用 `real_post`。
- **capabilities 与数据残留**：同一 DB 内若已存在 `validation_status=validated` 且 `supports_vision=True` 的预设，则 `GET /api/llm-settings/capabilities` 恒为 true；要断言「系统无可用端点」，需在单测内显式 **降级或删除** 预设行，而不是仅新建「无业务数据」用户。

### 4.5 Markdown / LaTeX 前端渲染与发布前预览

- **依赖（`frontend/package.json`）**：`markdown-it`、`markdown-it-katex`、`katex`、`dompurify`。安装命令示意：`<仓库根>/frontend/` 下执行 `npm install`；若构建环境无 Node（例如极简 agent 容器出现 `npm: command not found`），需在 CI 或本地完整前端镜像中执行 `npm ci && npm run build` 做回归。
- **渲染管道**：`frontend/src/utils/markdownRender.js` 导出 `renderMarkdownToSafeHtml(source)`。
  - `MarkdownIt({ html: false, linkify: true, breaks: true })`：**关闭** Markdown 内嵌原生 HTML，降低 XSS 面；再由 `markdown-it-katex` 处理 `$...$`、`$$...$$`、`\(...\)`、`\[...\]`（与 `markdown-it-katex` 默认行为一致，细节以该包文档为准）。
  - `katex` 选项 `throwOnError: false`：非法公式渲染为带颜色的错误占位，避免整页白屏。
  - 输出经 **DOMPurify.sanitize**，并 `ADD_TAGS` / `ADD_ATTR` 放宽以保留 KaTeX 可能产生的结构（如部分 MathML 相关标签）；若未来升级 KaTeX 后公式被「洗没」，优先检查净化白名单。
- **全局样式**：`frontend/src/styles/markdown-content.css`（标题、列表、代码块、表格、`.katex-display` 横向滚动）；`frontend/src/main.js` 引入之；KaTeX 自带 CSS 在 `markdownRender.js` 中 `import 'katex/dist/katex.min.css'`。
- **组件**：
  - `MarkdownPreview.vue`：接收 `source`、`compact`，`v-html` 展示 **已保存** 内容（学生/教师只读场景）。
  - `MarkdownEditorWithPreview.vue`：`el-input` 多行 + 文案提示 + **「预览渲染效果」** → `el-dialog` 内嵌 `MarkdownPreview`，供发布者在 **提交表单前** 核对 Markdown 与公式。
- **已接入的发布入口（含预览按钮）**：`frontend/src/views/Homework.vue`（作业正文、`rubric_text`、`rubric_teacher_text`、`reference_answer`）、`Materials.vue`（资料说明）、`Notifications.vue`（通知正文）、`MyCourses.vue`（新建课程简介）、`Subjects.vue`（课程简介编辑）。
- **已接入的阅读端**：`Homework.vue` 作业详情对话框；`HomeworkSubmission.vue`（作业说明、学生可见评分要点、历次提交与评语、聚合评语）；`HomeworkSubmissions.vue`（作业说明与教师可见 rubric、列表「提交说明」单元格、历史时间轴、已保存评语）；`Materials.vue` 资料详情；`MyCourses.vue` 课程卡片内简介（紧凑渲染 + `max-height` 裁剪）。
- **产品/解析坑**：
  - **美元符号**：正文中单独使用 `$3$` 这类可能被当作行内公式；长文本中的货币若与 KaTeX 冲突，可改用 `\\( ... \\)` 写公式或调整文案避免孤立的 `$` 对。
  - **bundle 体积**：生产构建会打入 KaTeX 字体与较大 JS chunk（Vite 可能拆出 `MarkdownPreview-*.js`）；若需极致首屏，可后续改为路由级或对话框级 **动态 import** `markdownRender` / `MarkdownPreview`（当前未做，以免过度工程化）。
- **与作业总评 UI 的交叉修复**：`HomeworkSubmission.vue` 使用计算属性 `hasAggregateScoreOrComment`（有 **分数或评语** 即视为有总评展示），避免「仅有分数、无评语」时误显示「暂无计入总评的分数」——该问题在接入 `MarkdownPreview` 替换纯文本时一并修正。

---

## 5. `INIT_DEFAULT_DATA=true` 默认初始化数据总览（用户、课程、内涵与形式）

本节描述 **仅设置 `INIT_DEFAULT_DATA=true`（默认）** 且 **未配置或未通过校验 `INIT_LLM_*`** 时，`app.bootstrap.bootstrap()` 写入数据库的 **可登录用户与教学对象**；若同时配置 `INIT_LLM_*` 且视觉校验通过，还会在 **本节数据之后** 追加「演示班级 / 演示课程 / 演示作业与提交」等（见 §1 与 `seed_initial_llm_deployment_bundle`）。

### 5.1 全局非教学数据

| 类型 | 内容 | 说明 |
|------|------|------|
| 管理员 | 用户名 `settings.INIT_ADMIN_USERNAME`（默认 `admin`），密码 `INIT_ADMIN_PASSWORD` | 角色 `admin`，由 `seed_default_admin` 创建。 |
| 学期 | `DEFAULT_SEMESTERS` 中 2024–2026 共 6 个中文季标学期 | `seed_default_semesters`，`is_active=True`。 |
| 系统设置 | `system_name`、`system_intro`、`copyright` 等键 | `seed_default_system_settings`。 |

### 5.2 初等概率论选修种子（`app/seed_default_probability.py`）

**入口**：`bootstrap()` 在 `seed_initial_llm_deployment_bundle` **之后** 调用 `seed_elementary_probability_elective_course(db)`；**幂等**：若已存在同名课程 `初等概率论（公共选修·2026春）` 则跳过。

| 类型 | 标识 / 形式 | 内涵 |
|------|-------------|------|
| 任课教师（用户） | 用户名 `teacher_pro`，密码 **`teacher_pro`**（与用户名相同，仅演示） | 角色 `teacher`，`class_id` 为空；显示名「概率论专业教师（示例）」。 |
| 班级 | 名称 `2026级理工选修试点班`，`grade=2026` | 容纳 4 名演示学生；与「演示班级」（INIT_LLM）**不同**，二者可并存。 |
| 学生（用户 + `students` 行） | `prob_stu_001` … `prob_stu_004`，密码分别为 `ProbStu001!` … `ProbStu004!` | 姓名：陈小威、林小朔、王小川、赵小岳；学号 `prob-2026-001` … `004`；均绑定上述班级。 |
| 课程 | `Subject.name = 初等概率论（公共选修·2026春）`，`course_type = elective` | 绑定当前 **激活学期**（无则取第一条学期）；任课为 `teacher_pro`；含简介、上课时间字符串（杜撰）。 |
| 选课 | **仅 2 人** 写入 `course_enrollments`：`prob_stu_001`、`prob_stu_002`，`enrollment_type=elective`，`can_remove=True` | **003、004 在同班但未选本课**，体现选修 opt-in。 |
| 课程资料 | `course_materials` 一条，标题含「第1章」「Markdown」 | `content` 为 **Markdown + LaTeX 风格公式**（`$...$`、`$$...$$`）：样本空间、Kolmogorov 公理、加法公式、参考书名（Ross / Grimmett & Welsh / Durrett / 国内教材）等。**前端** 在「课程资料」详情与（若重新编辑）预览对话框中按 §4.5 渲染。 |
| 作业 | 一章习题，Markdown 题干；`rubric_text` / `rubric_teacher_text` / `reference_answer` 齐全 | **自动评分**：仅当库中已存在 **通过视觉校验的活跃 LLM 预设**（`get_latest_validated_vision_preset` 非空）时为 `True`，并 ` _wire_course_llm_from_preset`；否则为 `False` 并 **打印说明**。若开启自动评分，种子会为已插入的提交调用 `queue_grading_task`（依赖 worker 或手工 `process_grading_task`）。 |
| 提交 | **两名已选课学生均有一条** `homework_submissions` + `homework_attempts` | 001 为较长 Markdown 作答，002 为较短作答；**未选课学生无提交**。 |

### 5.3 与「全班同步选课」相关的代码约定（agent 修改时注意）

- `sync_course_enrollments`（`app/course_access.py`）：对 **`course_type == "elective"`** 的课程 **返回 0**，不再把全班学生批量写入选课表。
- `sync_student_course_enrollments`：新建学生时 **不会** 自动为其加入班上 **选修** 课程，仅同步必修课等；选修须由管理员/学生端显式选课（或种子手写 `CourseEnrollment`）。

### 5.4 合并 `INIT_LLM_*` 通过时的额外数据（摘要）

- 演示班级名、演示课程名、演示作业名等常量见 `app/bootstrap.py` 中 `DEMO_SEED_*`。
- 演示学生学号 `demo-2026-001` …（与 `prob-*` **不同**）。
- 概率论种子仍独立存在；**LLM 演示课** 与 **概率论选修课** 可同时出现在学期列表中。

---

## 6. 与产品文档的交叉引用

- 生产部署总览：`DEPLOY.md`、`docs/FRESH_SERVER_DEPLOY_CN.md`
- 运维与安全：`docs/SECURITY-AND-OPERATIONS.md`
- 项目功能概览：`README.md`（若需对外同步「评分要点双框」等行为，可择机增补，本任务以代码与本文为准）
- 迭代遗留 / 双轨专项清理报告（本轮）：`docs/CLEANUP_SESSION_DUAL_TRACK_2026-05-06.md`

---

## 7. 回归检查清单（agent 自测）

1. `pytest tests/ -q` 或分文件：`pytest tests/test_llm_settings_api.py -q` 通过。
2. `pytest tests/test_homework_llm_grading.py -q`（若存在对 `HomeworkResponse` 字段数的假设，需更新）。
3. `pytest tests/test_llm_course_e2e_scenarios.py -q` 通过（15 条 LLM/课程/作业交叉场景）。
4. `pytest tests/test_llm_concurrency_scenarios.py -q` 建议全跑；其中含 **迟交聚合** 用例 `test_aggregate_score_keeps_best_counting_attempt_after_late_resubmit`。
5. 前端：`npm run build`（在 `frontend/`）无语法错误。
6. 手动：学生账号打开作业详情页，只能看到 **评分要点（对学生可见）**，看不到教师框与参考答案。

---

## 8. pytest 与手工冒烟脚本（避免「假测试文件」双轨）

### 8.1 背景与坑

- 历史上仓库根目录存在若干命名为 `test_*.py` 的文件，内容为 **`requests` 直连本机 `8001` 的手工脚本**，并非 pytest 用例。
- **症状**：在 `<仓库根>` 执行裸 `pytest`（未限定路径）时，pytest 会尝试收集这些文件；若本机未启动后端，会在 **收集阶段** 报 `ConnectionError`（见 `<仓库根>/pytest.ini` 引入前的行为）。
- **另一坑**：`scripts/dev_smoke/manual_smoke_login_dashboard.py` 曾包含以 `test_` 前缀命名的函数；pytest 会将其当作用例，但函数签名需要 fixture，导致混乱。
- **`tests/test_llm_stress_scenarios.py::test_course_endpoints_cleared_before_grading_fails` 历史假设**：旧断言期望 `error_code == endpoint_missing`，但主业务早已在 `_grade_with_endpoint_group` 中于 **课程无端点行** 时回退到 `get_latest_validated_vision_preset`（与 `tests/test_llm_course_e2e_scenarios.py::test_grading_uses_global_fallback_when_course_has_no_endpoint_rows` 一致）。若不在单测里显式 **降级/禁用** 全局预设，任务会 **成功** 而非失败。修复方式：在断言失败路径前，对 `LLMEndpointPreset` 统一 `is_active=False` 且 `validation_status` 非 `validated`（并去掉 `supports_vision`），确保「无可用端点」与产品意图一致。

### 8.2 当前规范（新逻辑主线）

- **自动化回归**：统一在 `<仓库根>/tests/`。根目录 `pytest.ini` 设置 `testpaths = tests`，因此直接运行 `pytest` 或 `pytest -q` 只收集 `tests/` 下文件。
- **手工 HTTP / 直连 DB 排障**：集中在 `<仓库根>/scripts/dev_smoke/`，文件名以 `manual_` 开头；说明与已知坑见同目录 `README.md`。
- **前端 API 客户端**：课程相关调用统一使用 `api.subjects`（`/api/subjects`）；不再维护 `api.courses` 别名，避免「同一资源两套入口」的维护双轨。

### 8.3 评分聚合内部 API

- `app/llm_grading.py` 中 `get_best_score_candidate(db, homework_id, student_id)` 为跨 attempt 聚合的 **唯一入口**；已移除历史上无效果且误导的 `latest_attempt_id` 关键字参数（调用方与 `refresh_submission_summary` 始终依赖全量候选查询）。

