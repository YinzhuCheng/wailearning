#!/usr/bin/env bash
# 在 ECS 上从 Git 更新代码并执行完整部署（后端 venv + 管理端前端 + 家长端 + Nginx + 重启后端）。
# 用法（需 root）：
#   sudo bash /path/to/repo/scripts/redeploy.sh
# 可选环境变量：
#   REPO_DIR=/root/wailearning     代码仓库路径（默认：本脚本所在仓库根目录）
#   GIT_BRANCH=main               要检出的分支
#   GIT_REMOTE=origin             远端名称
#   GIT_CLEAN=1                   是否 git clean -fd（0=跳过，保留未跟踪文件时请慎用）
#   SKIP_GIT=1                    跳过 git 同步（已在目标目录准备好代码时）
#   FRONTEND_ONLY=1               只跑 deploy_frontend.sh（例如仅修复管理端静态资源）
#   APP_URL=https://你的域名       部署后 post_deploy_check 使用的公网健康检查地址
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "请使用 root 执行：sudo bash $0"
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_DIR="${REPO_DIR:-$(cd "${SCRIPT_DIR}/.." && pwd -P)}"
GIT_BRANCH="${GIT_BRANCH:-main}"
GIT_REMOTE="${GIT_REMOTE:-origin}"
GIT_CLEAN="${GIT_CLEAN:-1}"
SKIP_GIT="${SKIP_GIT:-0}"
FRONTEND_ONLY="${FRONTEND_ONLY:-0}"
APP_URL="${APP_URL:-}"

echo "==> 仓库目录: ${REPO_DIR}"
echo "==> 分支: ${GIT_BRANCH}"

if [[ "${SKIP_GIT}" != "1" ]]; then
  if [[ ! -d "${REPO_DIR}/.git" ]]; then
    echo "错误: ${REPO_DIR} 不是 git 仓库。设置 REPO_DIR 或先 clone，或使用 SKIP_GIT=1。"
    exit 1
  fi
  cd "${REPO_DIR}"
  echo "==> Git: fetch ${GIT_REMOTE} ${GIT_BRANCH}"
  git fetch "${GIT_REMOTE}" "${GIT_BRANCH}"
  echo "==> Git: 强制对齐 ${GIT_REMOTE}/${GIT_BRANCH}（见 docs/DEPLOY_GIT_ROBUSTNESS.md）"
  git checkout -B "${GIT_BRANCH}" "${GIT_REMOTE}/${GIT_BRANCH}"
  git reset --hard "${GIT_REMOTE}/${GIT_BRANCH}"
  if [[ -f .gitmodules ]]; then
    git submodule update --init --recursive
  fi
  if [[ "${GIT_CLEAN}" == "1" ]]; then
    git clean -fd
  else
    echo "==> GIT_CLEAN=0，跳过 git clean"
  fi
else
  echo "==> 已 SKIP_GIT=1，跳过 git 更新"
fi

if [[ "${FRONTEND_ONLY}" == "1" ]]; then
  echo "==> FRONTEND_ONLY=1，仅部署管理端前端"
  bash "${SCRIPT_DIR}/deploy_frontend.sh"
else
  echo "==> 完整部署（后端 + 管理端 + 家长端）"
  bash "${SCRIPT_DIR}/deploy_all.sh"
fi

if [[ -n "${APP_URL}" ]]; then
  echo "==> 公网检查 APP_URL=${APP_URL}"
  APP_URL="${APP_URL}" bash "${SCRIPT_DIR}/post_deploy_check.sh"
else
  echo "==> 仅本机健康检查（未设置 APP_URL 则跳过公网 /health）"
  API_HEALTH_URL="http://127.0.0.1:8001/health" bash "${SCRIPT_DIR}/post_deploy_check.sh"
fi

echo "==> 重新部署完成。"
