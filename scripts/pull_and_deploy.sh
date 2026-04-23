#!/usr/bin/env bash
# 与 scripts/redeploy.sh 一致：强制对齐远端分支后再部署（见 docs/DEPLOY_GIT_ROBUSTNESS.md）。
set -euo pipefail

REPO_DIR="${REPO_DIR:-/root/dd-class}"
BRANCH="${BRANCH:-main}"
GIT_REMOTE="${GIT_REMOTE:-origin}"
GIT_CLEAN="${GIT_CLEAN:-1}"

cd "${REPO_DIR}"

echo "==> Git: fetch ${GIT_REMOTE} ${BRANCH}"
git fetch "${GIT_REMOTE}" "${BRANCH}"
echo "==> Git: checkout -B + reset --hard ${GIT_REMOTE}/${BRANCH}"
git checkout -B "${BRANCH}" "${GIT_REMOTE}/${BRANCH}"
git reset --hard "${GIT_REMOTE}/${BRANCH}"
if [[ -f .gitmodules ]]; then
  git submodule update --init --recursive
fi
if [[ "${GIT_CLEAN}" == "1" ]]; then
  git clean -fd
fi

bash scripts/deploy_all.sh
