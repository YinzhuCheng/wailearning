# 测试说明

本仓库包含两类自动化测试：**后端 pytest**（`tests/`）与 **前端 Playwright E2E**（`frontend/e2e/`）。二者互补：pytest 覆盖 API 与业务规则；E2E 从浏览器登录与点击出发，必要时用 HTTP 校验后端状态。

## 后端（pytest）

在项目根目录安装依赖后运行：

```bash
pip install -r requirements.txt
pytest
```

行为与压力类场景多在 `tests/behavior/`、`tests/llm_scenario.py` 等模块中。

## 前端 E2E（Playwright）

目录：`frontend/e2e/`。配置：`frontend/playwright.config.cjs`。

- **启动方式**：`npm run test:e2e`（在 `frontend/` 下）会由 Playwright 拉起 **FastAPI**（默认 `127.0.0.1:8012`）与 **Vite**（默认 `127.0.0.1:3012`），并在 `globalSetup` 中调用 `POST /api/e2e/dev/reset-scenario` 写入隔离数据，结果缓存在 `frontend/e2e/.cache/scenario.json`。
- **环境变量**（可选）：`E2E_DEV_SEED_TOKEN`、`E2E_API_PORT`、`E2E_UI_PORT`、`E2E_API_URL`、`PLAYWRIGHT_BASE_URL`。本地若已占用端口，可先结束占用进程或改端口。
- **共享步骤**：`frontend/e2e/fixtures.cjs` 中的 `enterSeededRequiredCourse(page, suffix)` 用于在「我的课程」中打开种子数据里的 **必修课**（避免列表首项为其他课程时「进入课程」按钮处于禁用态）。

### 用例分类（场景难度）

| 类型 | 文件 | 说明 |
|------|------|------|
| **边界** | `e2e-scenario-boundary-dynamic-complex.spec.js`（前半） | 首次进入工作台、管理员新建/删除课程、新建学生用户等 |
| **动态** | 同上（发布作业、个人资料改名） | 信息变更后 UI 与（部分用例）`/api/homeworks` 列表一致 |
| **复杂** | 同上（教师↔学生多轮登录、管理员与教师双浏览器） | 多角色、多步骤交互；管理员建课后教师端可见 |

其他文件（`roster-and-users.spec.js`、`homework-llm-routing.spec.js`、`ui-homework-student-actions.spec.js`）为既有回归用例，同样依赖 `globalSetup` 种子数据。

### E2E 种子数据（`app/routers/e2e_dev.py`）

仅在 `E2E_DEV_SEED_ENABLED=true` 且请求头 `X-E2E-Seed-Token` 与配置一致时可用。种子中教师的 **显示姓名** 带 `suffix`，避免历史 SQLite 库中多名教师同名导致管理端「任课老师」下拉选错人。
