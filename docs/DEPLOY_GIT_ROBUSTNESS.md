# 部署前 Git 同步：稳健做法与排障（中文）

本文说明在**服务器仓库内**切换到指定远端分支并部署时的常见坑、推荐流程，以及与「部署是否真正完成」的关系。更完整的复盘见 **`docs/DEPLOYMENT_POSTMORTEM_CN.md`**。

## 结论（可直接贴在脚本旁）

- **不要假定** `git fetch <remote> <branch>` 之后一定存在 **`refs/remotes/<remote>/<branch>`**。在不少 Git 版本/配置下，这种 fetch 主要更新 **`FETCH_HEAD`**，随后 `git checkout -B ... origin/branch` 可能报 **「is not a commit」**。
- **推荐**：用显式 refspec 把远端分支写入 remote-tracking ref，再检出并重置：

  ```bash
  git ls-remote --exit-code --heads "$GIT_REMOTE" "$BRANCH" >/dev/null
  git fetch "$GIT_REMOTE" "refs/heads/$BRANCH:refs/remotes/$GIT_REMOTE/$BRANCH"
  git checkout -B "$BRANCH" "$GIT_REMOTE/$BRANCH"
  git reset --hard "$GIT_REMOTE/$BRANCH"
  ```

- **工作区不干净**（未提交修改）时，`checkout` 会被 Git 保护性拒绝。部署机应只保留可重建状态：先 **`git diff` 备份到 patch**（可选），再 **`git reset --hard`** + **`git clean -ffd`**，然后再 fetch。仓库脚本中可通过 **`GIT_RESET_WORKTREE_BEFORE_FETCH=1`** 启用该前置步骤（见下）。
- **子模块**：存在 `.gitmodules` 时，在更新主仓库后执行 **`git submodule sync --recursive`** 与 **`git submodule update --init --recursive`**。
- **「Git 对齐」≠「已上线该版本」**：还必须完整执行 **`deploy_all.sh`**（或等价流程）、**`post_deploy_check.sh`** 通过、**systemd** 后端为 **active**。详见下文「部署完成的判定」。

仓库内 **`scripts/lib/git_sync_server.sh`** 封装上述 fetch/checkout/reset/submodule/clean；**`scripts/redeploy.sh`** 与 **`scripts/pull_and_deploy.sh`** 默认调用该逻辑。

## 不推荐的模式（易踩坑）

```bash
git fetch origin "$BRANCH"
git checkout -B "$BRANCH" "origin/$BRANCH"
```

若 **`origin/$BRANCH`** 未被创建，第二步会失败。请改用上一节的显式 refspec。

## 排障经验（何时先怀疑 Git，而不是业务代码）

- 日志显示 fetch 成功，但 **`checkout` / `reset`** 报错：优先查 **remote-tracking ref 是否存在**、**工作区是否有未提交修改**、**本地分支是否与远端分叉**。
- 对齐 Git 后若 **构建仍失败**，再查依赖、配置、数据库迁移等。

## 环境变量（`redeploy.sh` / `pull_and_deploy.sh`）

| 变量 | 默认 | 说明 |
|------|------|------|
| `GIT_REMOTE` | `origin` | 远端名称 |
| `GIT_BRANCH`（redeploy） / `BRANCH`（pull_and_deploy） | `main` | 要部署的分支 |
| `GIT_CLEAN` | `1` | `1` 时在同步末尾执行 `git clean -ffd`；`0` 跳过（慎用） |
| `GIT_RESET_WORKTREE_BEFORE_FETCH` | `0` | `1` 时先备份 `git diff` 到 `BACKUP_DIR`，再 `reset --hard` + `clean -ffd`，再 fetch |
| `BACKUP_DIR` | `/opt/dd-class/backups` | 上述 patch 输出目录 |
| `REPO_DIR` | 未设置时：**若存在** `/opt/dd-class/source/.git` **则默认使用该路径**，否则为 redeploy 脚本所在仓库根目录；仍可通过环境变量显式指定 | 服务器上的仓库路径（须与 `deploy_*` 使用的 `SOURCE_DIR` 一致） |
| `DD_DEFAULT_REPO_DIR` | `/opt/dd-class/source` | 覆盖「首选生产 clone 路径」（与 `DEPLOY.md` 目录约定一致） |
| `BRANCH` / `GIT_BRANCH` | `pull_and_deploy` 接受 **`BRANCH`** 或 **`GIT_BRANCH`**（前者优先）；`redeploy` 使用 **`GIT_BRANCH`** | 要部署的远端分支名 |

## SSH / heredoc 注意

使用 `ssh ... <<'EOF'` 时，**结束行必须是单独一行的 `EOF`**，不能与上一行命令或提示符拼接；否则远端脚本可能只执行一部分。见 **`docs/DEPLOYMENT_POSTMORTEM_CN.md`** 第 3 节。

## 部署完成的判定（建议写进验收清单）

至少同时满足：

1. **Git**：`HEAD` 与目标 commit 一致（**`post_deploy_check.sh`** 会打印当前分支与 `HEAD`）。
2. **部署**：**`deploy_all.sh`** 已完整跑完（或由 **`redeploy.sh`** 调用）。
3. **验收**：**`post_deploy_check.sh`** 通过：本机 **`http://127.0.0.1:8001/health`**、公网 **`API_HEALTH_URL`**（默认 **`${APP_URL}/health`**）、若公网 URL 为 `${APP_URL}/health` 则额外检查 **`${APP_URL}/api/health`**、**`nginx -t`**、**systemd** 状态摘要。
4. **非阻塞告警**：`npm audit`、Vite chunk 体积、Pydantic 命名告警等**不应**单独作为「部署失败」依据（见复盘文档第 5 节）。

## 与「仅 rsync 同步代码」流程的关系

若生产采用 **rsync / 制品包** 而非服务器上 Git 拉取，则本文针对的是**仍在服务器保留 clone 并用 git 更新**的场景；混合运维时建议统一心智模型。
