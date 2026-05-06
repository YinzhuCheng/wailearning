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

---

## 5. 与产品文档的交叉引用

- 生产部署总览：`DEPLOY.md`、`docs/FRESH_SERVER_DEPLOY_CN.md`
- 运维与安全：`docs/SECURITY-AND-OPERATIONS.md`
- 项目功能概览：`README.md`（若需对外同步「评分要点双框」等行为，可择机增补，本任务以代码与本文为准）

---

## 6. 回归检查清单（agent 自测）

1. `pytest tests/test_llm_settings_api.py -q` 通过。
2. `pytest tests/test_homework_llm_grading.py -q`（若存在对 `HomeworkResponse` 字段数的假设，需更新）。
3. `pytest tests/test_llm_course_e2e_scenarios.py -q` 通过（15 条 LLM/课程/作业交叉场景）。
4. 前端：`npm run build`（在 `frontend/`）无语法错误。
5. 手动：学生账号打开作业详情页，只能看到 **评分要点（对学生可见）**，看不到教师框与参考答案。
