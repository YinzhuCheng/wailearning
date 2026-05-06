# Documentation upgrade report — 2026-05 (implementation-aligned pass)

This report satisfies the “final output” requirement for the documentation system upgrade round. It is stored **in-repo** so agents can diff it like code.

---

## 一、实际实现主线总结（fact-aligned）

| Area | Current ground truth |
|------|---------------------|
| Product shell | FastAPI backend package `apps.backend.wailearning_backend`; Vue 3 admin + parent SPAs under `apps/web/*`. |
| HTTP surface | Routers included explicitly from `main.py` (see [`reference/CODE_MAP_AND_ENTRYPOINTS.md`](reference/CODE_MAP_AND_ENTRYPOINTS.md)). |
| Persistence | SQLAlchemy models in `db/models.py`; startup uses `create_all` + `bootstrap.ensure_schema_updates()` (no Alembic tree in-repo snapshot). |
| AuthZ | JWT staff/student users + separate parent-code flows; course scope primarily `domains/courses/access.py`; coarse role helpers in `core/permissions.py`. |
| LLM grading async | DB-backed `HomeworkGradingTask` rows processed by **in-process** worker thread (`llm_grading.py` / `_WorkerManager`), gated by env vars. |
| Tests | Root `pytest.ini` targets `tests/`; `tests/conftest.py` injects `DATABASE_URL`, disables demo seed, adjusts worker flags. |
| CI reference | `ops/ci/pr-pipeline.yml` runs `python3 -m pytest -q` — **no** `.github/workflows/` present in this snapshot. |

---

## 二、已更新 / 新增文档清单

| 文件路径 | 更新类型 | 摘要 | 原因 |
|----------|----------|------|------|
| [`AGENTS.md`](../AGENTS.md) | 新增 | Root-level agent handbook：边界、grep 关键词、高风险模块、验证清单 | 用户要求 AGENTS；此前缺失 |
| [`docs/agent-playbook.md`](agent-playbook.md) | 新增 | 流程型操作手册：读仓库顺序、bootstrap 顺序、测试命令 | 补足“如何做”而非仅“地图” |
| [`docs/reference/CODE_MAP_AND_ENTRYPOINTS.md`](reference/CODE_MAP_AND_ENTRYPOINTS.md) | 新增 | 路径级代码地图：后端入口、router 列表、前端关键路径、CI 路径 | 满足“落到路径” hard requirement |
| [`docs/reference/PERMISSIONS_AND_SECURITY_BOUNDARIES.md`](reference/PERMISSIONS_AND_SECURITY_BOUNDARIES.md) | 新增 | 角色、课程访问 helper、E2E 门 | 权限文档化 |
| [`docs/reference/DATA_MODEL_ESSENTIALS.md`](reference/DATA_MODEL_ESSENTIALS.md) | 新增 | 核心表 / 模型分组与命名陷阱 | 数据模型速查 |
| [`docs/architecture/ASYNC_TASKS_AND_WORKERS.md`](architecture/ASYNC_TASKS_AND_WORKERS.md) | 新增 | LLM worker 真实线程模型与任务表 | 对齐“无 Redis”现实 |
| [`docs/known-issues-and-risks.md`](known-issues-and-risks.md) | 新增 | 已知风险、pytest sqlite 观察、CI 位置 | 不确定性与坑点集中登记 |
| [`docs/README.md`](README.md) | 补充 | “§0 Agent bundle” 与 reference 索引 | 导航升级 |
| [`README.md`](../README.md) | 补充 | 指向 `AGENTS.md`；`python3` 启动提示 | 对齐 Linux agent 环境 |
| [`docs/architecture/MAINTAINER_AGENT_GUIDE.md`](architecture/MAINTAINER_AGENT_GUIDE.md) | 补充 | 指向新 reference / playbook / known issues | 避免重复维护 |
| [`docs/architecture/TROUBLESHOOTING.md`](architecture/TROUBLESHOOTING.md) | 补充 | pytest sqlite 损坏排查 | 实测失败入口 |
| [`docs/development/DEVELOPMENT_AND_TESTING.md`](development/DEVELOPMENT_AND_TESTING.md) | 补充 | CI YAML 路径；解释 `python` vs `python3` | 命令真实性 |
| [`docs/development/TEST_EXECUTION_PITFALLS.md`](development/TEST_EXECUTION_PITFALLS.md) | 补充 | `.pytest_tmp/test.sqlite` + metadata 导入次序坑 | 记录本轮实测 |

---

## 三、文档与实现不一致的修正要点

| 原描述（抽象） | 实际代码行为 | 处理方式 |
|----------------|--------------|----------|
| “LLM 异步 = 通用消息队列” | SQL + 进程内线程 worker | 新建 `ASYNC_TASKS_AND_WORKERS.md` 澄清 |
| “GitHub Actions 一定存在” | 仅有 `ops/ci/*.yml` 模板 | `known-issues` + `CODE_MAP` 写明 snapshot 现状 |
| README 仅用 `python` | 多处 CI / Linux 使用 `python3` | README / DEVELOPMENT_AND_TESTING 双语表述 |

---

## 四、已写入仓库的坑点（本轮）

| 标题 | 写入位置 | 涉及路径 | 风险 | 后续 |
|------|-----------|----------|------|------|
| pytest 持久 sqlite 文件损坏 | `TEST_EXECUTION_PITFALLS.md`, `known-issues-and-risks.md` | `tests/conftest.py`, `.pytest_tmp/test.sqlite` | 假阴性/假阳性测试 | 删除 sqlite；调研是否应在 `db_reset` 强制 import models |
| `ensure_schema_updates` 报缺表 | `known-issues-and-risks.md` | `bootstrap.py`, `tests/db_reset.py` | CI 不稳定 | **待人工确认** 根因 |
| 无 `.github/workflows` | `known-issues-and-risks.md`, `AGENTS.md` | `ops/ci/` | 搜错自动化入口 | 若迁移至 GH Actions 需新增文档 |

---

## 五、测试 / 验证记录（本轮）

| 命令 | 是否运行 | 结果 | 失败原因 | 是否写入文档 |
|------|-----------|------|----------|--------------|
| `python3 -m pytest tests/backend/e2e_dev -q` | 是 | 大量失败/错误 | sqlite 状态 + 集合污染 + 缺表/唯一约束 | 是（known issues + pitfalls） |
| `python3 -m pytest tests/backend/e2e_dev/test_demo_course_seed.py -q` | 是 | 失败（缺 `course_llm_configs`） | 见 §四 | 是 |
| `python3 -m pytest -q`（全量） | 尝试 | **未完成**（超时后台） | 全量耗时超出本轮交互预算 | 在报告中诚实记录 |

**补充对照实验：** 手动新建 sqlite + `import models` + `create_all` + `ensure_schema_updates` 成功 — 记录在 `known-issues-and-risks.md` 作为证据。

---

## 六、仍待人工确认

| 问题 | 涉及路径 | 无法确认原因 | 建议人工动作 |
|------|-----------|--------------|--------------|
| pytest 缺表是否源自 db_reset 未加载 metadata | `tests/db_reset.py`, SQLAlchemy import graph | 未做全量 bisect + 全绿 CI | 最小复现 PR；必要时在 `db_reset` 增加模型导入 |
| `HomeworkGradingTask.status` 全部历史取值 | `db/models.py`, `llm_grading.py` | 未枚举历史 DB | grep + 生产样本 |

---

## 七、后续文档建议

1. 自动从 OpenAPI 导出静态 API reference（或 CI artifact）。
2. ER 图（选修：从 models 生成）。
3. 权限矩阵（role × route）自动化校验测试。
4. 若引入 Alembic：新增 `docs/migrations.md` 并淡化“仅靠 bootstrap”叙述。
5. Playwright 与 pytest 双栈并行时的 sqlite 隔离策略（每 worker 独立 DB 文件）。

---

## 八、声明

- 本轮遵循约束：**未修改业务代码**（仅文档与导航性 README 补充）。
- 若后续代码改动使本文过时，请同时更新本文件或删除过时段落。
