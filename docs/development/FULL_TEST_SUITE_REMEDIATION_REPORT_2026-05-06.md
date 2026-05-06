# Full Test Suite Remediation Report — 2026-05-06

**Audience:** Humans and LLM agents auditing verification posture after product changes (notably **选修课不按行政班绑定** + **`subject_class_links`**).  
**Scope:** Read-only architecture recap → coverage matrix → executed commands → fixes → residual risk.

---

## 一、测试体系理解（第一步 · 只读结论）

### 项目类型与技术栈

- **单体教学管理平台 BIMSA-CLASS**：FastAPI + SQLAlchemy + Pydantic v2；生产参考 PostgreSQL；本地/pytest 默认 SQLite。
- **管理端 SPA**：Vue 3 + Vite + Element Plus + Pinia；**无 Vitest/Jest** — 前端自动化以 **Playwright** 为主（`apps/web/admin/package.json` 仅有 `test:e2e`）。
- **家长端 SPA**：独立 `apps/web/parent`（本回合未单独跑 E2E）。
- **异步任务**：LLM 批改 **`HomeworkGradingTask`** + **进程内 worker**（非 Redis/Celery）；见 `docs/architecture/ASYNC_TASKS_AND_WORKERS.md`。

### 后端核心模块（摘要）

| 区域 | 路径 |
|------|------|
| 应用装配 / 生命周期 | `apps/backend/wailearning_backend/main.py`, `bootstrap.py` |
| HTTP 路由 | `apps/backend/wailearning_backend/api/routers/` |
| 领域逻辑 | `domains/courses/`, `domains/homework/`, `domains/llm/`, `domains/roster/`, … |
| ORM | `db/models.py`，DDL 修补 `bootstrap.ensure_schema_updates()` |
| 权限 | `core/permissions.py` + 路由内 `ensure_course_access_http` 等 |

### 前端核心模块（摘要）

| 区域 | 路径 |
|------|------|
| 入口 / 路由 | `apps/web/admin/src/main.js`, `router/index.js` |
| API 客户端 | `apps/web/admin/src/api/index.js` |
| 布局 / 导航 | `views/Layout.vue` |
| 课程 / 作业 / 资料 | `views/Subjects.vue`, `Homework*.vue`, `Materials.vue`, `MaterialRead.vue` |

### 核心业务实体

用户/班级/学生花名册、课程（`Subject`）、**`subject_class_links`**、`CourseEnrollment`、作业/提交/尝试、通知与已读、成绩与考勤、LLM 预设与课程配置、讨论区等 — 详见 `docs/reference/DATA_MODEL_ESSENTIALS.md`。

### 核心业务流程（摘要）

选课与登录上下文修复、作业提交→队列→worker→教师复核、通知 badge + sync API、成绩合成、资料章节与讨论 LLM 等 — `docs/architecture/CORE_BUSINESS_FLOWS.md`。

### 权限模型（摘要）

角色：`admin` / `class_teacher` / `teacher` / `student`；课程可见性 `domains/courses/access.py`；家长码独立于 JWT — `docs/reference/PERMISSIONS_AND_SECURITY_BOUNDARIES.md`。

### 当前已有测试类型

| 类型 | 位置 |
|------|------|
| 后端单元/集成/API | `tests/backend/**`, `tests/behavior/**`, `tests/security/**`, `tests/scenarios/**` |
| PostgreSQL 专项 | `tests/postgres/**`（默认 skip，除非设置 `TEST_DATABASE_URL` 等） |
| E2E（真实 Chromium + 托管 uvicorn + vite） | `tests/e2e/web-admin/*.spec.js`，配置 `apps/web/admin/playwright.config.cjs` |
| 维护脚本（非 pytest） | `tests/devtools/` |

### 当前测试命令（权威来源：`docs/development/DEVELOPMENT_AND_TESTING.md`）

```bash
# 后端（仓库根）
python3 -m pytest

# 排除仅 Postgres 目录（本回合云端默认）
python3 -m pytest tests --ignore=tests/postgres

# 管理端 E2E
cd apps/web/admin && npx playwright install chromium && npm run test:e2e
```

### E2E 入口与环境

- **Seed：** `POST /api/e2e/dev/reset-scenario`，令牌 `E2E_DEV_SEED_TOKEN`（Playwright 默认 `test-playwright-seed`）。
- **双门禁：** 强力 dev 路由需 admin JWT + seed header — 见 `DEVELOPMENT_AND_TESTING.md` §E2E Seed。
- **数据库：** Playwright 托管 API 使用 **临时 SQLite 文件**（`DATABASE_URL` 注入），**真实 ORM + 真实路由**。
- **无 docker-compose** 于本仓库快照；Postgres 自建脚本见 `ops/scripts/dev/provision_postgres_pytest.sh`。

### 现有测试明显缺口（高层）

- **前端缺 Vitest 组件/逻辑单测** — 回归依赖 Playwright + 后端 pytest。
- **全量 Playwright** ~300+ 条 / ~15min — CI 与本地常截断为分层或 smoke。
- **SQLite vs Postgres** 路径差异未在全量 CI 默认跑满。
- **并发竞态** 少数 behavior 测试存在 **偶发失败**（见第五节）。

---

## 二、测试覆盖矩阵（第二步 · 摘录）

| 功能/场景 | 原有覆盖 | 本轮新增/强化 | 代表文件 | 强度 | 剩余风险 |
|-----------|----------|----------------|----------|------|----------|
| 登录 / JWT / 403 | 有 | — | `tests/security/`, `tests/backend/integration/` | 中–强 | 多 tab / 过期 token 边界 |
| 课程可见性 +  enroll | 有 | **对齐选修全校选课** | `test_student_course_catalog_behavior.py`, `test_student_elective_catalog_and_quota.py` | **强（修正后）** | 多班 aggregate UI 仍用 primary class |
| `subject_class_links` + 同步 | 有 | **roster 拒绝未绑定班 + GET 选修占位** | `test_subject_multi_class_links.py` | 中–强 | 历史脏数据仅 bootstrap 自愈 |
| 作业提交 / LLM 队列 | 有 | — | `tests/backend/homework/`, `tests/behavior/*llm*` | 强 | 外部 LLM 需 mock |
| 通知已读 / 并发 | 有 | — | `test_complex_regression_roundtrip_behavior.py` | 中 | **偶发 flake**（见五） |
| E2E happy path | 有 | smoke 复跑 | `e2e-core-flows-smoke.spec.js` | 中 | 非全量 300+ |

（完整 P0–P2 规划见下一节历史输出；本文件聚焦 **本轮已执行** 与 **已修复**。）

---

## 三、全量补测试计划（第三步 · 本轮落地子集）

本轮在「不写空洞单测」前提下实际落地：

| 标题 | 类型 | 价值 |
|------|------|------|
| 选修课目录与自主选课策略与产品一致 | API/集成 | 防止退回「按班选修」错误模型 |
| 多班必修 roster-enroll 拒绝未链接班级 | API | 覆盖对象级班级边界 |
| 选修课 GET 序列化 `class_name == "-"` | API | 前后端契约 |

---

## 四、新增/修改测试清单（第四步）

| 文件 | 类型 | 覆盖场景 | 关键断言 | E2E | 真实 DB | mock |
|------|------|----------|----------|-----|---------|------|
| `tests/backend/courses/test_student_course_catalog_behavior.py` | API | 选修全校可选 | `can_self_enroll_elective`、跨班 enroll **200** | 否 | SQLite | 无 |
| `tests/backend/courses/test_student_elective_catalog_and_quota.py` | API | 必修拒绝自修；外班选修允许 | 400 vs 200 | 否 | SQLite | 无 |
| `tests/backend/courses/test_subject_multi_class_links.py` | API | roster 跳过非绑定班；选修序列化 | `skipped_not_in_class_roster`、`class_name == "-"` | 否 | SQLite | 无 |

---

## 五、运行命令记录（第五步）

| 命令 | 目的 | 结果 |
|------|------|------|
| `python3 -m pytest tests --ignore=tests/postgres -q --tb=no` | 全量后端（含 behavior/security） | **首跑 428 passed, 1 failed**；失败项单独复跑 **通过** → **判定为并发 flake** |
| `python3 -m pytest tests/backend/courses/test_student_course_catalog_behavior.py tests/backend/courses/test_student_elective_catalog_and_quota.py -q` | 回归选修策略 | **16 passed** |
| `python3 -m pytest tests/backend/courses/test_subject_multi_class_links.py -q` | 多班链接扩展 | **5 passed** |
| `cd apps/web/admin && npx playwright test e2e-core-flows-smoke.spec.js` | E2E smoke（真实 API+UI） | **10 passed** |
| `npm run build`（admin，本分支近期已验证） | 生产构建 | **通过**（未在本文件生成时刻重复跑时可于 CI 再确认） |

---

## 六、修复的问题（第六步）

| 问题 | 类型 | 涉及文件 | 修复方式 |
|------|------|----------|----------|
| 选修课仍按「本班/外班」断言 | **测试过期**（需求已变为全校自选） | `test_student_course_catalog_behavior.py`, `test_student_elective_catalog_and_quota.py` | 更新期望与用例名；新增成功路径断言 |
| 并发 mark-all-read 单测偶发失败 | **flake / 环境时序** | `test_complex_regression_roundtrip_behavior.py::test_c7b_*` | **未改产品**；单独复跑通过 — 建议后续加重试或缩小并发窗口 |

---

## 七、无法完整验证的内容（第七步）

| 内容 | 原因 | 补救尝试 | 后续人工 |
|------|------|----------|----------|
| **全量 Playwright ~300+** | 墙钟与云端 agent 预算 | 跑通 **smoke 10** + 文档命令 | 发布前执行 `npm run test:e2e` |
| **tests/postgres/** | 未在本环境导出 `TEST_DATABASE_URL` | 按 `DEVELOPMENT_AND_TESTING.md` 脚本 | DBA/CI 矩阵 |

---

## 八、剩余测试缺口 & 防偷懒声明（第八步）

### 剩余缺口

- Admin SPA **单元测试层**（Vitest）仍缺席。
- **全量 E2E** 未在本回合执行。
- **LLM 真网** 路径仍依赖 mock/跳过外部密钥（与仓库既有策略一致）。

### skip / xfail / only / mock

- **新增 skip：** **无**
- **新增 xfail：** **无**
- **test.only：** **无**
- **新增 mock：** **无**（本回合仅改 pytest 期望与新增 API 断言）
- **未修复的测试失败：** 全量首跑 1 例并发测试 — **复跑通过**，未改为 skip

---

## 系统与测试体系理解摘要（第一步交付合并版）

- **项目：** 多角色学校管理；FastAPI 后端 + Vue3 管理端 + Playwright E2E；LLM 批改为 **DB 队列 + 进程内 worker**。
- **测试入口：** `pytest.ini` → `tests/`；E2E → `apps/web/admin` + `tests/e2e/web-admin/`。
- **依赖服务：** pytest 默认 SQLite；E2E 自启 uvicorn+vite；Postgres 套件可选；无 Redis 队列。
- **明显缺口：** 前端单测层、全量 E2E 时长、SQLite/Postgres 双轨、个别并发测试稳定性。

---

*本报告由专项 remediation 生成；若产品与文档再度漂移，请以代码与 `docs/architecture/CORE_BUSINESS_FLOWS.md` 为准并同步更新本文件。*
