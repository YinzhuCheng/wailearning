#!/usr/bin/env bash
# Server-side Git sync helpers (sourced by redeploy.sh / pull_and_deploy.sh).
# See docs/DEPLOY_GIT_ROBUSTNESS.md — explicit refspec fetch so refs/remotes/<remote>/<branch> exists.

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  echo "This file is meant to be sourced from other scripts, not executed directly." >&2
  exit 1
fi

# Args: remote_name branch_name reset_worktree(0|1) backup_dir git_final_clean(0|1)
# When reset_worktree=1: save git diff to backup_dir, then reset --hard and clean -ffd before fetch.
__dd_git_sync_to_remote_branch() {
  local git_remote="$1"
  local branch="$2"
  local reset_worktree="${3:-0}"
  local backup_dir="${4:-/opt/dd-class/backups}"
  local git_final_clean="${5:-1}"

  if [[ "${reset_worktree}" == "1" ]]; then
    mkdir -p "${backup_dir}"
    local stamp
    stamp="$(date +%F-%H%M%S)"
    echo "==> Git: backup local diff -> ${backup_dir}/source-working-tree-${stamp}.patch (if any)"
    git diff >"${backup_dir}/source-working-tree-${stamp}.patch" || true
    echo "==> Git: reset --hard + clean -ffd (discard local commits/changes to tracked files)"
    git reset --hard
    git clean -ffd
  fi

  echo "==> Git: ls-remote + fetch explicit refspec refs/heads/${branch} -> refs/remotes/${git_remote}/${branch}"
  git ls-remote --exit-code --heads "${git_remote}" "${branch}" >/dev/null
  git fetch "${git_remote}" "refs/heads/${branch}:refs/remotes/${git_remote}/${branch}"
  echo "==> Git: checkout -B ${branch} + reset --hard ${git_remote}/${branch}"
  git checkout -B "${branch}" "${git_remote}/${branch}"
  git reset --hard "${git_remote}/${branch}"
  if [[ -f .gitmodules ]]; then
    git submodule sync --recursive
    git submodule update --init --recursive
  fi
  if [[ "${git_final_clean}" == "1" ]]; then
    git clean -ffd
  fi
}
