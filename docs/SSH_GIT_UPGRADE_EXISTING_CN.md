# 已部署系统的 SSH 代码流升级（保留数据）

> 适用场景：系统已经在线运行过一次，你现在只想“拉取新代码并升级服务”，**不重装、不清库、不删除上传附件**。

本文基于仓库现有部署文档与脚本整理：`DEPLOY.md`、`docs/DEPLOY_GIT_ROBUSTNESS.md`、`scripts/redeploy.sh`、`scripts/post_deploy_check.sh`。

---

## 0. 原则（先看）

- 升级时不要删除：
  - `/opt/dd-class/shared/.env.production`
  - `/opt/dd-class/shared/uploads`
  - PostgreSQL `ddclass` 库
- 生产升级优先使用：`scripts/redeploy.sh`
  - 这个脚本会做 Git 对齐（分支/远端）、再调用完整部署与检查流程。

---

## 1. 本机一条命令触发远程升级（推荐）

把下面命令在你本机终端执行即可（会 SSH 到服务器）：

```bash
ssh root@<你的服务器IP> "REPO_DIR=/opt/dd-class/source GIT_BRANCH=main GIT_REMOTE=origin bash /opt/dd-class/source/scripts/redeploy.sh"
```

如果你发的是其他分支，把 `GIT_BRANCH=main` 改成目标分支名。

---

## 2. 更稳妥的“先备份再升级”SSH代码流

如果是正式环境，建议用这个多行版本（先备份数据库和 shared，再升级）：

```bash
ssh root@<你的服务器IP> 'bash -se' <<'SH'
set -euo pipefail

REPO_DIR="/opt/dd-class/source"
BRANCH="main"
BACKUP_DIR="/opt/dd-class/backups"

# 1) 备份（关键）
install -d -m 0755 "${BACKUP_DIR}"
sudo -u postgres pg_dump -Fc ddclass > "${BACKUP_DIR}/ddclass-$(date +%F-%H%M%S).dump"
tar -czf "${BACKUP_DIR}/shared-$(date +%F-%H%M%S).tar.gz" /opt/dd-class/shared

# 2) 升级（保留数据）
REPO_DIR="${REPO_DIR}" GIT_BRANCH="${BRANCH}" GIT_REMOTE=origin \
  bash "${REPO_DIR}/scripts/redeploy.sh"

# 3) 健康检查
API_HEALTH_URL="http://127.0.0.1:8001/health" bash "${REPO_DIR}/scripts/post_deploy_check.sh"
SH
```

---

## 3. 如果服务器有人手改代码导致拉取失败

当你看到 checkout/reset 相关冲突（工作区脏），可以启用“先备份 patch 再硬重置工作区”模式：

```bash
ssh root@<你的服务器IP> "REPO_DIR=/opt/dd-class/source GIT_BRANCH=main GIT_RESET_WORKTREE_BEFORE_FETCH=1 BACKUP_DIR=/opt/dd-class/backups bash /opt/dd-class/source/scripts/redeploy.sh"
```

> 该模式会把工作区差异备份到 `BACKUP_DIR`，再继续拉取与部署。

---

## 4. 升级后验收（最少检查）

登录服务器执行：

```bash
cd /opt/dd-class/source
sudo systemctl status ddclass-backend --no-pager
sudo journalctl -u ddclass-backend -n 100 --no-pager
sudo bash scripts/post_deploy_check.sh
curl -fsS http://127.0.0.1:8001/health
```

如果有公网域名，补一条：

```bash
APP_URL="https://你的域名" sudo bash /opt/dd-class/source/scripts/post_deploy_check.sh
```

---

## 5. 常见误区

- 误区 1：只 `git pull` 不跑 `deploy_all/redeploy`，前端可能看起来“没更新”。
- 误区 2：`SKIP_GIT=1` 但 `REPO_DIR` 不是新代码，结果重打包了旧前端。
- 误区 3：把升级当重装，误删 `shared/uploads` 或数据库。

---

## 6. 回滚最小方案（升级失败时）

1. 停后端服务：`systemctl stop ddclass-backend`
2. 恢复代码到上一个稳定提交（或备份目录）
3. 必要时恢复数据库 dump 与 `shared` 备份
4. 重跑：`bash /opt/dd-class/source/scripts/deploy_all.sh`
5. 再跑：`bash /opt/dd-class/source/scripts/post_deploy_check.sh`

