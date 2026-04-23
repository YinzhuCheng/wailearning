# 部署前 Git 同步：稳健做法与排障（中文）

本文总结在**服务器上切换到指定远端分支并立即部署**时的常见坑与推荐流程，供运维脚本与人工操作对照。

## 结论（可直接贴在脚本旁）

- **不要只依赖**「`git fetch` + `git checkout 分支名` + `git pull --ff-only`」这类在服务器上**较脆弱**的组合：本地 tracking 异常、残留未提交修改、或无法 fast-forward 时，脚本会在**切分支阶段**失败，看起来像「部署挂了」，实则**代码尚未对齐远端**。
- **更稳妥的做法**是：先显式从远端取回目标分支，再让**本地分支名**与 **`origin/<分支>`** 指向同一提交，并清掉工作区噪音：
  1. `git fetch <remote> <branch>`（或 `git fetch --all --prune` 视团队规范而定）
  2. `git checkout -B <branch> <remote>/<branch>`（本地分支重置为跟踪该远端引用）
  3. `git reset --hard <remote>/<branch>`（工作区与索引与远端提交完全一致）
  4. `git clean -fd`（删除未跟踪文件与目录，避免旧构建产物、误放文件干扰）
  5. 若有子模块：`git submodule update --init --recursive`
  6. 再执行 `deploy_all.sh` / `redeploy.sh` 等部署步骤

仓库内 **`scripts/redeploy.sh`** 与 **`scripts/pull_and_deploy.sh`** 已按上述思路更新；自定义脚本建议复用同一模式。

## 排障经验（何时先怀疑 Git，而不是业务代码）

- 若日志显示**目标分支已从远端 fetch 到**，但 **`checkout` / tracking / fast-forward** 报错，应优先怀疑：
  - 工作区不干净（未提交修改、冲突残留）
  - 本地分支与 `origin/<branch>` 已分叉
  - 脚本未强制对齐远端，导致 `pull --ff-only` 拒绝合并
- 此时优先尝试：**强制对齐远端目标分支后再部署**。对齐成功后若构建仍失败，再转向应用依赖、配置、数据库迁移等问题。

## 可选环境变量（`redeploy.sh`）

| 变量 | 默认 | 说明 |
|------|------|------|
| `GIT_REMOTE` | `origin` | 远端名称 |
| `GIT_BRANCH` / `BRANCH` | `main` | 要部署的分支 |
| `GIT_CLEAN` | `1` | 设为 `0` 可跳过 `git clean -fd`（仅在明确需要保留未跟踪文件时使用） |

## 与「仅 rsync 同步代码」流程的关系

若生产环境采用 **rsync / 制品包** 更新代码而不在服务器上保留完整 Git 历史，则本文针对的是**仍在服务器仓库内 git pull 部署**的场景；`scripts/example_safe_upgrade_aliyun.sh` 等以 rsync 为主的流程不受 `checkout` 影响，但仍建议阅读本文以便在**混合运维**（有时 git、有时 rsync）时统一心智模型。
