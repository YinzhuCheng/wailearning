# 安全与运维：角色、数据落点与升级重部署

本文档面向**安全审计**与**生产升级**，说明系统中的角色与权限、账号来源、数据存储位置，以及一次典型的**带备份的代码升级与重部署**流程。内容以本仓库实现为准；部署路径以 `systemd/ddclass-backend.service` 中的生产示例为参考。

---

## 1. 系统角色与权限

后端在 `app.models.UserRole` 中定义四类主账号角色：`ADMIN`（系统管理员）、`CLASS_TEACHER`（班主任）、`TEACHER`（授课教师）、`STUDENT`（学生）。权限在路由与各模块中分散校验，下表为**典型能力**的归纳，便于做访问控制与审计，具体以代码为准。

| 能力域 | ADMIN | CLASS_TEACHER | TEACHER | STUDENT |
|--------|-------|---------------|---------|---------|
| 全局与班级/用户管理 | 是 | 部分（依班级） | 否 | 否 |
| 可访问课程范围 | 全部课程 | 本班课程 ∪ 自己任教的课程 | 仅自己任教的课程 | 本班课程（需有班级且已加入选课等逻辑） |
| 学生/成绩/考勤管理（`app/permissions.py` 中的 can_manage_*） | 是 | 是 | 是 | 否 |
| 班级/教师/全量数据查看等管理员专属能力 | 是 | 否 | 否 | 否 |
| 作业、提交与 LLM 评分业务 | 按 `ensure_course_access` 能访问到的课程 | 同左 | 同左 | 学生仅可操作本人相关数据（具体接口校验） |
| 系统设置与**全局** LLM 端点预置 | 是（系统设置、LLM 预置等） | — | — | 否 |
| 课程级 LLM 配置 | 是 | 是（`app/routers/llm_settings.py` 中 `ADMIN` / `CLASS_TEACHER` / `TEACHER` 可管） | 是 | 否（学生访问 LLM 管理接口应被拒绝） |

**家长访问**：没有独立的「家长用户表登录角色」。家长通过**学生维度的 `parent_code`（家长码）** 访问 `app/routers/parent.py` 下接口，属只读/受限能力，不承载后台管理权限。

---

## 2. 用户如何出现（注册与账号来源）

- **公开注册**（`POST /api/auth/register`）：受 `ALLOW_PUBLIC_REGISTRATION` 控制（默认 `False`，见 `app/config.py`）。开启后，**仅可创建学生账号**，且不能自选教师/管理员角色；若关闭则返回 403。
- **首次初始化**：可通过 `INIT_ADMIN_*`、`INIT_DEFAULT_DATA` 等由启动流程/bootstrap 创建默认管理员等（见 `app/config.py` 与 `app/bootstrap`）。
- **后台创建/维护**：管理员与教师管理相关接口在 `app/routers/users.py` 等模块中，用于创建或调整非公开注册能覆盖的账号与角色（需已登录且具备相应权限）。

---

## 3. 数据分类与存储位置（安全升级关注）

| 数据类别 | 主要存储位置 | 说明 |
|----------|--------------|------|
| 业务与鉴权主数据 | **PostgreSQL**（或开发用 SQLite，由 `DATABASE_URL` 决定） | 用户、密码哈希、班级/课程/选课、作业、提交、尝试、LLM 任务、评分候选、LLM 用量与端点/课程配置等，均在 ORM 模型中（`app/models.py`）。**升级/迁移时优先备份此库。** |
| 文件类（作业附件等） | **服务器文件系统** | `app/attachments.py`：默认在应用侧 `uploads/attachments/`，或 `UPLOADS_DIR` 指定目录。部署示例使用 `UPLOADS_DIR=/opt/dd-class/shared/uploads`。**与数据库共同构成完整可恢复业务状态。** |
| 密钥与运行参数 | **环境变量 / EnvironmentFile** | 如 `SECRET_KEY`、`DATABASE_URL`、`TRUSTED_HOSTS`、`BACKEND_CORS_*`、`UPLOADS_DIR`、LLM 工作进程开关等（`app/config.py`）。**不应提交到 Git；备份策略应包含受控副本（如加密的 .env 备份）。** |
| LLM 供应商密钥 | **数据库**（`LLMEndpointPreset.api_key` 等） | 与端点预置项一并持久化，属于**高敏数据**，备份与访问需与数据库同等级保护。 |
| 浏览器端会话 | **localStorage 等** | 前端以 JWT 等方式保存 access token（见前端 `api` 与登录流程），属终端侧数据，服务端升级通常**无需**单独备份终端存储。 |
| 家长码 | **数据库**（`Student` 上 `parent_code` 等） | 用于无账号访问家长接口；**泄露等同于该通道上的身份凭证**，轮换策略需在运营侧规定。 |
| 审计/日志 | 应用与系统日志、数据库中的日志表等 | 依 `LogService` 等实现，具体以代码为准；**生产应集中采集并限制访问。** |

**SQLite 注意**：仅建议开发/测试；生产请使用 PostgreSQL 并定期备份、权限隔离。

---

## 4. 系统升级与重部署示例

以下为**通用示例 Shell**，假设：

- 代码在 `/opt/dd-class/source`；
- 虚拟环境在 `/opt/dd-class/venv`；
- 与 systemd 样例一致：`EnvironmentFile=/opt/dd-class/shared/.env.production`、`UPLOADS_DIR=/opt/dd-class/shared/uploads`；
- 数据库为本地 PostgreSQL，且本机 `pg_dump` 可用。

请按实际环境替换路径、数据库名、服务名。若你使用不同进程管理或容器，只需保留「**备份 → 更新代码 → 安装依赖 → 数据库迁移/引导 → 重启**」的等价步骤。

```bash
set -euo pipefail

# ---------------------------------------------------------------------------
# 0. 变量（请按环境修改）
# ---------------------------------------------------------------------------
export DEPLOY_USER="${DEPLOY_USER:-ddclass}"
export APP_ROOT="${APP_ROOT:-/opt/dd-class}"
export SOURCE_DIR="${APP_ROOT}/source"
export VENV_DIR="${APP_ROOT}/venv"
export ENV_FILE="${APP_ROOT}/shared/.env.production"
export UPLOADS_DIR="${APP_ROOT}/shared/uploads"
export BACKUP_ROOT="${APP_ROOT}/backups"
export STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
export UNIT_NAME="${UNIT_NAME:-ddclass-backend.service}"  # 与 systemd 中实际单元名一致

# 从 .env 加载环境（本机需有 python3；DATABASE_URL 须包含数据库名，见 app/config 默认值风格）
# shellcheck disable=SC1090
if [[ -f "$ENV_FILE" ]]; then set -a && . "$ENV_FILE" && set +a; else
  echo "ERROR: missing $ENV_FILE" >&2
  exit 1
fi
DB_NAME="$(python3 - <<'PY'
import os
from urllib.parse import urlparse
u = os.environ.get("DATABASE_URL", "")
p = urlparse(u)
name = (p.path or "/").lstrip("/").split("/")[0] or "ddclass"
print(name)
PY
)"

mkdir -p "$BACKUP_ROOT"
BU_DIR="${BACKUP_ROOT}/pre-upgrade-${STAMP}"
mkdir -p "$BU_DIR"

# ---------------------------------------------------------------------------
# 1. 维护窗口：停止应用（若需要零停机，请改用多实例滚动策略，此处不展开）
# ---------------------------------------------------------------------------
sudo -n systemctl stop "$UNIT_NAME" || true

# ---------------------------------------------------------------------------
# 2. 备份：数据库 + 上传目录 + 环境文件（三者为常见故障恢复点）
# ---------------------------------------------------------------------------
# 下例假设本机可用peer或已配置好 pg_dump 认证；若数据库在别的主机，请为 pg_dump 加 -h/-U 或使用 $DATABASE_URL 配合 pg 客户端工具
echo "Dumping database ${DB_NAME} -> ${BU_DIR}/db.custom.dump.gz"
sudo -n -u postgres pg_dump -Fc -d "$DB_NAME" 2>/dev/null | gzip -1 > "${BU_DIR}/db.custom.dump.gz" \
  || { echo "If pg_dump failed, set PGHOST/PGUSER or run pg_dump with the correct -h -U and credentials." >&2; exit 1; }

# 若更习惯纯 SQL 文本: pg_dump -d "$DB_NAME" | gzip > "${BU_DIR}/db.sql.gz"
echo "Tarring uploads: $UPLOADS_DIR"
if [[ -d "$UPLOADS_DIR" ]]; then
  tar -C "$(dirname "$UPLOADS_DIR")" -czf "${BU_DIR}/uploads_$(basename "$UPLOADS_DIR").tar.gz" "$(basename "$UPLOADS_DIR")"
else
  echo "Warning: UPLOADS_DIR not found, skip: $UPLOADS_DIR" >&2
fi

# 元数据备份（**勿把含密钥的 tar 存到未授权位置**；此处仅作站点侧归档示例）
if [[ -f "$ENV_FILE" ]]; then
  install -m 600 "$ENV_FILE" "${BU_DIR}/.env.production.sav"
fi
echo "Backup set written under: $BU_DIR"

# ---------------------------------------------------------------------------
# 3. 更新代码（示例：在部署服务器上从远端拉取；也可用 CI 发布 artifact）
# ---------------------------------------------------------------------------
sudo -n -u "$DEPLOY_USER" git -C "$SOURCE_DIR" fetch origin
# 将 <branch> 换为你的发布分支，例如 main 或 cursor/... 合并后的生产分支
sudo -n -u "$DEPLOY_USER" git -C "$SOURCE_DIR" checkout <branch>
sudo -n -u "$DEPLOY_USER" git -C "$SOURCE_DIR" pull --ff-only origin <branch>

# ---------------------------------------------------------------------------
# 4. 依赖与数据库结构（与仓库提供的 bootstrap/迁移方式一致时）
# ---------------------------------------------------------------------------
sudo -n -u "$DEPLOY_USER" "$VENV_DIR/bin/pip" install -r "$SOURCE_DIR/requirements.txt" --disable-pip-version-check -q
sudo -n -u "$DEPLOY_USER" bash -c "set -a && . '$ENV_FILE' && set +a && cd '$SOURCE_DIR' && '$VENV_DIR/bin/python' -m app.bootstrap"

# ---------------------------------------------------------------------------
# 5. 启动
# ---------------------------------------------------------------------------
sudo -n systemctl start "$UNIT_NAME"
sudo -n systemctl --no-pager -l status "$UNIT_NAME" || true

echo "Done. If health checks pass, you may remove old backup trees after a retention period."
```

**可省略或调整备份的情形**（仍建议至少保留**数据库**备份）：

- 仅修改前端静态资源且**不涉及**后端/数据库结构，可减少步骤，但生产仍建议有回滚前快照。
- 全容器化部署时，用卷快照/编排平台的 backup job 替代 `tar`/`pg_dump`。
- 若 `bootstrap` 已能幂等地处理 schema，仍应在升级前对 DB 做备份，以应对数据迁移失败或回滚需要。

**回滚思路**：`systemctl stop` → 从 `${BU_DIR}` 恢复数据库与上传目录 → `git checkout` 到旧提交 → `pip install` + `bootstrap` → `systemctl start`（与团队现有流程统一即可）。

---

## 5. 与 systemd 单元的关系

样例 `systemd/ddclass-backend.service` 说明：

- 从 `shared/.env.production` 加载环境；
- `UPLOADS_DIR` 指向共享盘上的上传根目录；
- `ExecStartPre=... -m app.bootstrap` 在启动 gunicorn 前执行应用引导。

重部署时务必保证**升级后的 `bootstrap` 与数据库备份来自同一操作顺序**（先备份、再改 schema），避免在无可恢复点的情况下做破坏性变更。

---

## 6. 文档维护

本文件随产品迭代可能失效；以 `app/config.py`、`app/models.py`、各 `router` 与 `app/permissions.py` 为准确来源。若你扩展了多租户、外部 IdP 或新的文件存储，请补充「数据落点」表格。
