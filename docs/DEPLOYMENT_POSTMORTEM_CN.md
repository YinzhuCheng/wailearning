# 部署复盘（DD-CLASS / wailearning）

本文记录一次生产部署中遇到的典型问题与最终做法，便于写入运维手册与脚本约定。与 **`docs/DEPLOY_GIT_ROBUSTNESS.md`**、`DEPLOY.md` 中的 Git / 验收说明互补。

---

## 1. `git fetch` 成功，但 `checkout origin/branch` 失败

**现象**

```text
fatal: 'origin/cursor/remaining-audit-fixes-e30f' is not a commit ...
```

脚本里常见顺序是：

```bash
git fetch origin "$BRANCH"
git checkout -B "$BRANCH" "origin/$BRANCH"
```

**原因**

`git fetch origin "$BRANCH"` 往往只更新 **`FETCH_HEAD`**，**不保证** 创建或更新 **`refs/remotes/origin/<branch>`**。后续假定 `origin/<branch>` 已存在就会失败。

**做法**

用显式 refspec 把远端分支写到 remote-tracking ref：

```bash
git ls-remote --exit-code --heads "$GIT_REMOTE" "$BRANCH" >/dev/null
git fetch "$GIT_REMOTE" "refs/heads/$BRANCH:refs/remotes/$GIT_REMOTE/$BRANCH"
git checkout -B "$BRANCH" "$GIT_REMOTE/$BRANCH"
git reset --hard "$GIT_REMOTE/$BRANCH"
```

仓库内 **`scripts/redeploy.sh`**、**`scripts/pull_and_deploy.sh`** 通过 **`scripts/lib/git_sync_server.sh`** 统一按上述方式抓取。

---

## 2. 工作区有未提交改动，`checkout` 被 Git 拦截（含仅改 `scripts/*.sh`）

**现象**

```text
error: Your local changes to the following files would be overwritten by checkout:
```

**原因**

服务器上对跟踪文件有手工修改且未提交；切换到会改动同一文件的分支时，Git 会拒绝覆盖。

**做法**

- **原则**：部署机只保留可重建状态；临时改动应进仓库，或至少先导出 patch 再清理。
- **脚本**：对需要“先清再拉”的机器，使用 **`GIT_RESET_WORKTREE_BEFORE_FETCH=1`**；会在 `BACKUP_DIR`（默认 `/opt/dd-class/backups`）写入 `source-working-tree-<时间戳>.patch`，再 `git reset --hard` 与 `git clean -ffd`，然后按第 1 节方式同步远端分支。
- **自动缓解（默认）**：若未使用 `GIT_RESET` 但 `checkout -B` 仍因「本地改动会被覆盖」失败（例如只改了 `scripts/*.sh`），**`git_sync_server.sh`** 在 **`GIT_AUTO_STASH_ON_CHECKOUT_CONFLICT=1`（默认）** 时会再写入 `checkout-conflict-<时间戳>.patch`、执行 **`git stash -u`** 并重试一次。不需要时设 **`GIT_AUTO_STASH_ON_CHECKOUT_CONFLICT=0`**。

---

## 2b. `sudo -u postgres pg_dump` 时出现 *could not change directory to "/root"*

**现象**

在 root 家目录下执行 `sudo -u postgres pg_dump ...`，日志里出现 **Permission denied** 与 **could not change directory to "/root"**。

**原因**

`postgres` 系统用户不能 `cd` 进 `/root`，属常见提示；**多数情况下 dump 仍成功**。

**做法**

在子 shell 中先 **`cd /tmp`**（或任意 postgres 可读目录）再执行 **`pg_dump`**。仓库中 **`SAFE_BACKUP_BEFORE_DEPLOY=1`** 时的备份逻辑采用 **`(cd /tmp && sudo -u postgres pg_dump ...)`**。

---

## 3. SSH heredoc 结束符写错，脚本未完整执行

**现象**

日志里出现 `echo "==> DONE"EOF` 或命令与 `EOF` 粘在同一行，后续命令在错误 shell 里执行。

**原因**

`<<'EOF'` 的结束标记必须**单独占一行**，前后不能拼接其他字符，行尾仅换行。

**做法**

```bash
ssh root@example.com 'bash -s' <<'EOF'
set -euo pipefail
# ...
echo "==> DONE"
EOF
```

文档中应明确：**heredoc 的 `EOF` 必须独占一行**，否则容易出现“日志看起来跑完了、实际只执行了一部分”的假象。

---

## 4. “仓库已切到目标分支”不等于“线上已部署该版本”

**现象**

`git status` 干净、`git log -1` 正确，公网 `/api/health` 也返回 healthy，但若未跑完 **`scripts/deploy_all.sh`** 或未重启到对应产物，仍不能认定服务进程与静态资源已是该 commit。

**原因**

对齐 Git 与 **systemd / 构建 / Nginx** 是两件事；健康检查只说明“服务活着”，不单独证明“已升级到目标提交”。

**部署完成的建议判定（需同时满足）**

| 检查项 | 说明 |
|--------|------|
| Git | 当前分支与 `HEAD` 与预期 commit 一致 |
| 部署脚本 | **`deploy_all.sh`**（或由 **`redeploy.sh`** 触发的等价流程）已完整执行 |
| 验收脚本 | **`post_deploy_check.sh`** 通过（含本机与公网健康、可选 `/api/health`） |
| systemd | 后端单元为 **active** |
| Nginx | **`nginx -t`** 通过（`post_deploy_check.sh` 已包含） |

---

## 5. 非阻塞告警（勿与部署失败混为一谈）

| 类型 | 说明 | 建议 |
|------|------|------|
| `npm audit` moderate/high | 构建成功但依赖审计有漏洞 | 单独排期安全清理 |
| Vite chunk 过大 | 构建体积告警 | 后续拆包、懒加载 |
| Pydantic `model_name` / `protected_namespaces` | 字段命名与保留命名空间冲突 | 后续改字段名或配置 `protected_namespaces` |

---

## 6. 原则摘要

1. **部署机只保留可重建状态**：备份 DB、shared、源码区 diff 后，`git reset --hard` + `git clean -ffd`（或通过 `GIT_RESET_WORKTREE_BEFORE_FETCH=1`）；或在升级脚本中设 **`SAFE_BACKUP_BEFORE_DEPLOY=1`**（由 **`redeploy.sh` / `pull_and_deploy.sh`** 在 Git 同步前执行）。
2. **Git 对齐必须用显式 refspec**：不要依赖“`git fetch origin branch` 后 `origin/branch` 一定存在”。
3. **部署完成须经统一验收**：Git + 完整部署 + `post_deploy_check.sh` + systemd + 本机与公网健康（及文档约定的路径）。

---

## 7. 管理端界面仍是旧版、但接口已新

**常见原因**

1. **`deploy_all.sh` 未跑完**：前端由 **`deploy_frontend.sh`**（`npm run build` + rsync 到 `/var/www/.../admin`）发布；若脚本在中途失败，浏览器仍加载旧静态资源。
2. **`SKIP_GIT=1` 或拉错目录**：本地仓库不是目标 commit 时，重建前端只是「旧代码重新打包」。
3. **`GIT_BRANCH` 未传**：`redeploy.sh` 默认 **`main`**，功能分支需显式设置。
4. **`REPO_DIR` 与文档不一致**：生产常见为 **`/opt/dd-class/source`**；勿与另一份 clone 混淆。
5. **浏览器缓存**：部署验证通过后可尝试强制刷新或无痕窗口。

**脚本侧缓解**：`redeploy.sh` / `pull_and_deploy.sh` 在部署前打印当前 **`git rev-parse --short HEAD`**；`deploy_frontend.sh` 在构建前打印 **`SOURCE_DIR`** 对应提交。详见 **`DEPLOY.md`** 中 *Admin SPA / stale UI* 小节。

---

## 8. 参考：稳健远程片段（按需改路径与分支）

以下仅为说明性示例；生产环境请替换 IP、分支与备份策略。

```bash
ssh root@YOUR_HOST 'bash -s' <<'EOF'
set -euo pipefail
REPO_DIR="/opt/dd-class/source"
BRANCH="main"
GIT_REMOTE="origin"
BACKUP_DIR="/opt/dd-class/backups"
cd "$REPO_DIR"
mkdir -p "$BACKUP_DIR"
git diff >"$BACKUP_DIR/source-working-tree-$(date +%F-%H%M%S).patch" || true
git reset --hard
git clean -ffd
git ls-remote --exit-code --heads "$GIT_REMOTE" "$BRANCH" >/dev/null
git fetch "$GIT_REMOTE" "refs/heads/$BRANCH:refs/remotes/$GIT_REMOTE/$BRANCH"
git checkout -B "$BRANCH" "$GIT_REMOTE/$BRANCH"
git reset --hard "$GIT_REMOTE/$BRANCH"
if [[ -f .gitmodules ]]; then
  git submodule sync --recursive
  git submodule update --init --recursive
fi
git clean -ffd
sudo bash scripts/deploy_all.sh
APP_URL="https://YOUR_DOMAIN" sudo bash scripts/post_deploy_check.sh
echo "==> DONE"
EOF
```

注意：**最后一行 `EOF` 必须单独一行。**
