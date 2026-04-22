# 阿里云 SSH 一键清空并重拉分支部署（含管理员重置）

> 适用：你已经通过 SSH 登录到服务器，希望**清空旧资产（代码 + 数据库 + 前端构建产物 + 上传附件）**，然后重新拉取指定分支并部署。
>
> 风险：以下流程会删除历史业务数据，请确认已备份。

## 为什么不建议盲目直接跑仓库里的所有脚本

仓库里确实有很多部署脚本，但职责不同：

- `scripts/redeploy.sh`：默认是“更新并部署”，**不会**主动清库；适合常规升级。
- `scripts/pull_and_deploy.sh`：也是拉取并部署，默认路径偏旧（`/root/dd-class`），通常要改环境变量。
- `scripts/deploy_all.sh`：做完整部署，但同样不负责“删库删资产”。
- `scripts/reset_user_password.sh`：适合“保留现有数据库，仅改密码”。

所以这次需求（先清空再重建）建议用**可审计的一次性命令**，把删除动作写清楚，再调用已有部署脚本。

## 一次性多行执行（推荐）

> 先根据你的真实环境修改前 8 个变量，再整体粘贴执行。

```bash
sudo bash -euxo pipefail <<'SH'
# ====== 0) 按需修改变量 ======
REPO_URL="<YOUR_GIT_REMOTE_URL>"
BRANCH="<YOUR_BRANCH>"
REPO_DIR="/opt/dd-class/source"
APP_ROOT="/opt/dd-class"
ENV_FILE="/opt/dd-class/shared/.env.production"
DB_NAME="ddclass"
DB_USER="ddclass"
DB_PASS="<DB_PASSWORD_PLACEHOLDER>"
ADMIN_USER="<ADMIN_USERNAME_PLACEHOLDER>"
ADMIN_PASS="<ADMIN_PASSWORD_PLACEHOLDER>"

# ====== 1) 停服务，避免删除时有进程占用 ======
systemctl stop ddclass-backend || true

# ====== 2) 清空原仓库资产（危险操作） ======
# 2.1 清理部署目录（保留 shared 目录给 .env 使用）
rm -rf "${REPO_DIR}"
mkdir -p "${REPO_DIR}"

# 2.2 清理前端构建产物
rm -rf /var/www/wailearning.xyz/admin/* || true
rm -rf /var/www/wailearning.xyz/parent/* || true

# 2.3 清理上传附件（如果你确认要删除历史作业/资料文件）
rm -rf "${APP_ROOT}/shared/uploads" || true

# 2.4 重建数据库（彻底清空业务数据）
sudo -u postgres psql -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='${DB_NAME}';" || true
sudo -u postgres psql -c "DROP DATABASE IF EXISTS ${DB_NAME};"
sudo -u postgres psql -c "DROP ROLE IF EXISTS ${DB_USER};"

# ====== 3) 重新拉取这个分支 ======
git clone --branch "${BRANCH}" --single-branch "${REPO_URL}" "${REPO_DIR}"
cd "${REPO_DIR}"
chmod +x scripts/*.sh

# ====== 4) 重建数据库用户和库 ======
cp scripts/init_db.sql /tmp/init_db.sql
chmod 644 /tmp/init_db.sql
sudo -u postgres psql \
  -v db_name="${DB_NAME}" \
  -v db_user="${DB_USER}" \
  -v db_password="${DB_PASS}" \
  -f /tmp/init_db.sql

# ====== 5) 配置管理员占位符（写入生产环境变量） ======
# 如果 ENV 文件不存在，先从模板安装
if [ ! -f "${ENV_FILE}" ]; then
  install -m 640 .env.production "${ENV_FILE}"
fi

# 确保这两个变量存在并被替换为你传入的占位符/真实值
sed -i "s|^INIT_ADMIN_USERNAME=.*|INIT_ADMIN_USERNAME=${ADMIN_USER}|" "${ENV_FILE}" || true
sed -i "s|^INIT_ADMIN_PASSWORD=.*|INIT_ADMIN_PASSWORD=${ADMIN_PASS}|" "${ENV_FILE}" || true

grep -q '^INIT_ADMIN_USERNAME=' "${ENV_FILE}" || echo "INIT_ADMIN_USERNAME=${ADMIN_USER}" >> "${ENV_FILE}"
grep -q '^INIT_ADMIN_PASSWORD=' "${ENV_FILE}" || echo "INIT_ADMIN_PASSWORD=${ADMIN_PASS}" >> "${ENV_FILE}"

# ====== 6) 重新部署 ======
bash scripts/deploy_all.sh

# ====== 7) 健康检查 ======
API_HEALTH_URL="http://127.0.0.1:8001/health" bash scripts/post_deploy_check.sh
systemctl status ddclass-backend --no-pager -l | sed -n '1,60p'
SH
```

## 管理员账号/密码占位符示例

- `ADMIN_USER="<ADMIN_USERNAME_PLACEHOLDER>"`
- `ADMIN_PASS="<ADMIN_PASSWORD_PLACEHOLDER>"`

首次启动会按 `INIT_ADMIN_USERNAME/INIT_ADMIN_PASSWORD` 创建管理员；若用户已存在，不会覆盖旧密码。若要强制改密码，请执行：

```bash
sudo REPO_DIR=/opt/dd-class/source \
  VENV_DIR=/opt/dd-class/venv \
  ENV_FILE=/opt/dd-class/shared/.env.production \
  bash /opt/dd-class/source/scripts/reset_user_password.sh \
  "<ADMIN_USERNAME_PLACEHOLDER>" "<ADMIN_PASSWORD_PLACEHOLDER>"
```

## 执行前建议

1. 先备份 PostgreSQL 与上传目录。
2. 先在低峰期执行，避免用户在线写入。
3. 如果你只想“重拉 + 重新部署，不删数据”，直接用：

```bash
sudo REPO_DIR=/opt/dd-class/source GIT_BRANCH=<YOUR_BRANCH> bash scripts/redeploy.sh
```
