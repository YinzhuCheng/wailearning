# 专项清理：迭代遗留、冗余与双轨逻辑（2026-05-06）

本文档面向 **LLM agent / 自动化编码系统**：允许冗长、表格化、可检索；人类可只读「一、系统新逻辑主线总结」与「五、测试结果」。

---

## 一、系统新逻辑主线总结

| 维度 | 当前主线（canonical） |
|------|------------------------|
| 后端框架 | FastAPI，`app/main.py` 注册各 `app/routers/*.py`；启动时 `ensure_schema_updates`、作业回填等。 |
| 作业总评聚合 | `app/llm_grading.py` → `get_best_score_candidate(db, homework_id, student_id)` 全量候选 + `counts_toward_final_score` / 教师分规则；`refresh_submission_summary` 写 `graded_best_attempt_id`。 |
| 课程 LLM 路由 | 课程配置无端点行时，`_grade_with_endpoint_group` 可回退 `get_latest_validated_vision_preset`（全局已通过视觉校验的活跃预设）。 |
| 前端 API 客户端 | `frontend/src/api/index.js` 中课程相关仅 **`api.subjects`**（`/api/subjects`），不再维护 `api.courses` 别名。 |
| 自动化测试入口 | 仓库根 `pytest.ini`：`testpaths = tests`，裸 `pytest` 仅收集 `tests/`。 |
| 手工冒烟 | `scripts/dev_smoke/manual_*.py`，非 pytest；说明见 `scripts/dev_smoke/README.md`。 |
| 路由包 `__init__` | `app/routers/__init__.py` 仅为文档性说明；**不**再维护与 `main.py` 重复的 re-export 列表。 |

---

## 二、已清理内容

| 编号 | 清理类型 | 涉及文件 | 处理方式 | 原因与影响 | 对应测试 |
|------|-----------|----------|----------|------------|----------|
| C1 | 旧文档 / 测试双轨 | 根目录 `test_*.py`（已迁移） | 移动 + 重命名 | 根目录 `test_*.py` 实为 `requests` 手工脚本，与 pytest 命名冲突，导致裸 `pytest` 收集失败（`ConnectionError`）。 | `pytest --collect-only`；`pytest tests/` |
| C2 | 配置 / 工具入口 | `pytest.ini`（新建） | 新增 | `testpaths = tests` 固定「唯一」自动化测试树根。 | 全量 `pytest tests/` |
| C3 | 前端双轨别名 | `frontend/src/api/index.js`，`frontend/src/stores/user.js`，`Scores.vue`、`Attendance.vue`、`Students.vue`、`Subjects.vue`、`MyCourses.vue` | 删除 `api.courses`，统一 `api.subjects` | 同一 `subjectsApi` 对象双命名增加维护成本。 | 无专门单测；建议 CI `npm run build` |
| C4 | 后端 API 表面冗余 | `app/llm_grading.py` `get_best_score_candidate` | 删除无效果参数 `latest_attempt_id` | 参数始终被忽略，易误导调用方以为仍按「仅最新 attempt」聚合。 | `tests/test_llm_concurrency_scenarios.py` |
| C5 | 误导性包初始化 | `app/routers/__init__.py` | 改为文档字符串 | 旧内容 re-export 子集易让 agent 以为必须在 `__init__` 注册路由。 | `from app.main import app`（pytest 内） |
| C6 | 本地遗留路径 | `scripts/dev_smoke/manual_dashboard_direct_db.py` | 重写 | 移除硬编码 `g:/ddclass`，改为基于 `__file__` 的仓库根 `sys.path`；包 `main` + `if __name__`。 | 手工运行 |
| C7 | 测试与主业务不一致 | `tests/test_llm_stress_scenarios.py::test_course_endpoints_cleared_before_grading_fails` | 更新断言与数据准备 | 主业务存在全局 fallback；旧断言 `endpoint_missing` 已不存在于代码路径。单测内显式禁用所有 `LLMEndpointPreset` 以测「真·无端点」失败。 | 该用例自身 |
| C8 | 开发者文档 | `docs/AGENT_IMPLEMENTATION_NOTES.md`、`README.md`、`scripts/dev_smoke/README.md` | 增补 | 记录 pytest 边界、全局 fallback 与单测交叉坑。 | — |

---

## 三、保留的兼容逻辑（未削弱）

| 文件 / 区域 | 保留原因 | 兼容对象 | 方式 | 未来删除条件 |
|-------------|----------|----------|------|----------------|
| `subjects._build_legacy_course_times` / `_deserialize_course_times` | 历史课程仅 `weekly_schedule` + 起止日期 | 历史数据 | 读路径合成 `course_times` JSON | 数据迁移后仅保留 JSON 时间表 |
| `app/bootstrap.normalize_legacy_branding` | 旧品牌字符串 | 历史 `system_settings` 行 | 写入时规范化 | 无旧值可读 |
| `llm_grading` 中 `legacy_priority` routing 元数据 | 无 `LLMGroup` 时的扁平端点模式 | 部署与旧库 | 与组路由统一在 `_grade_with_endpoint_group` | 产品废弃扁平模式且数据迁移完成 |
| `frontend` 中 `legacy-dashboard-*` 命名 | 班主任 vs 任课教师 UI 分支命名 | 无 | 仅 CSS/函数名，非第二套 API | 可选重命名，非功能双轨 |

---

## 四、仍待人工确认（本轮未删代码）

| 问题 | 涉及文件 | 原因 | 需确认 | 建议 |
|------|----------|------|--------|------|
| `.workflow/pr-pipeline.yml` 中 `python3 ./main.py` | `.workflow/pr-pipeline.yml` | 仓库根无 `main.py`，与 `app/main.py` 不一致；未改以免破坏外部流水线契约 | 该 CI 是否仍使用、是否应改为 `pytest` 或 `uvicorn` | 与运维对齐后修正 |
| `npm`/前端构建 | `frontend/` | 本 agent 容器无 `node`/`npm`，无法执行 `npm run build` | 在含 Node 的 CI 或本地验证 | 保持现有 Vite 工程不变 |

---

## 五、测试结果

| 命令 | 结果 | 通过 | 失败原因 | 与本轮相关性 |
|------|------|------|----------|----------------|
| `python3 -m pytest tests/ -q --tb=no` | 78 passed | 是 | — | 全量回归本轮改动 |
| `python3 -m pytest --collect-only -q` | 78 tests collected | 是 | — | 验证 `pytest.ini` |
| `npm run build`（`frontend/`） | 未执行 | — | 环境无 `npm` | 与 C3 相关，需有 Node 的环境补跑 |

---

## 六、踩坑记录（占位路径，便于 agent 检索）

| 症状 | 位置（示意） | 原因 |
|------|----------------|------|
| 裸 `pytest` 报 `ConnectionError` | `<仓库根>/test_*.py`（已迁至 `<仓库根>/scripts/dev_smoke/manual_*.py`） | 旧文件在 import 或收集阶段请求 `localhost:8001`。 |
| `test_course_endpoints_cleared_before_grading_fails` 失败，任务为 `success` | `<仓库根>/tests/test_llm_stress_scenarios.py` | 课程 `endpoints=[]` 仍会走全局 validated 预设；需在同用例内降级预设行。 |
| `npm: command not found` | `<仓库根>/frontend/` 下执行 `npm run build` | agent 容器未安装 Node；换完整前端镜像或本地。 |

---

## 七、后续建议（有证据的增量）

1. 在含 **Node.js** 的 CI 步骤中执行 `npm ci && npm run build`（与 `README`/`AGENT` 回归清单一致）。
2. 审计 `.workflow/*.yml` 与 `GITHUB_WORKFLOW.md` 是否仍引用已移动脚本路径。
3. 若产品确认不再需要「全局 fallback」，应在 `llm_grading` 单点改行为并同步删除 `test_grading_uses_global_fallback_when_course_has_no_endpoint_rows` 等对立用例（**属产品决策，本轮未做**）。
