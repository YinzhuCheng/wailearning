#!/usr/bin/env bash
# 与 scripts/redeploy.sh 共用 Git 同步逻辑（见 docs/DEPLOY_GIT_ROBUSTNESS.md）。
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck source=scripts/lib/git_sync_server.sh
source "${SCRIPT_DIR}/lib/git_sync_server.sh"

REPO_DIR="${REPO_DIR:-/root/dd-class}"
BRANCH="${BRANCH:-main}"
GIT_REMOTE="${GIT_REMOTE:-origin}"
GIT_CLEAN="${GIT_CLEAN:-1}"
GIT_RESET_WORKTREE_BEFORE_FETCH="${GIT_RESET_WORKTREE_BEFORE_FETCH:-0}"
BACKUP_DIR="${BACKUP_DIR:-/opt/dd-class/backups}"

cd "${REPO_DIR}"

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

bash scripts/deploy_all.sh
