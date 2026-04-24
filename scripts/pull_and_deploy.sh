#!/usr/bin/env bash
# 与 scripts/redeploy.sh 共用 Git 同步逻辑（见 docs/DEPLOY_GIT_ROBUSTNESS.md）。
# 需 root（与 deploy_all.sh 内各脚本一致）。分支可用 BRANCH 或 GIT_BRANCH。
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "请使用 root 执行：sudo bash $0" >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck source=scripts/lib/deploy_repo_dir.sh
source "${SCRIPT_DIR}/lib/deploy_repo_dir.sh"
__dd_resolve_repo_dir "${SCRIPT_DIR}"
# shellcheck source=scripts/lib/git_sync_server.sh
source "${SCRIPT_DIR}/lib/git_sync_server.sh"

BRANCH="${BRANCH:-${GIT_BRANCH:-main}}"
GIT_REMOTE="${GIT_REMOTE:-origin}"
GIT_CLEAN="${GIT_CLEAN:-1}"
GIT_RESET_WORKTREE_BEFORE_FETCH="${GIT_RESET_WORKTREE_BEFORE_FETCH:-0}"
BACKUP_DIR="${BACKUP_DIR:-/opt/dd-class/backups}"

cd "${REPO_DIR}"
echo "==> pull_and_deploy: REPO_DIR=${REPO_DIR} 分支=${BRANCH}"
if [[ -d .git ]]; then
  echo "==> 同步前提交: $(git rev-parse --short HEAD)"
fi

git_final_clean_flag="0"
if [[ "${GIT_CLEAN}" == "1" ]]; then
  git_final_clean_flag="1"
fi
__dd_git_sync_to_remote_branch \
  "${GIT_REMOTE}" \
  "${BRANCH}" \
  "${GIT_RESET_WORKTREE_BEFORE_FETCH}" \
  "${BACKUP_DIR}" \
  "${git_final_clean_flag}"

echo "==> 同步后提交: $(git rev-parse --short HEAD)（将用此树执行 deploy_all）"

bash "${SCRIPT_DIR}/deploy_all.sh"
