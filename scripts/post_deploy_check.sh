#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck source=lib_deploy.sh
source "${SCRIPT_DIR}/lib_deploy.sh"

APP_URL="${APP_URL:-https://wailearning.xyz}"
API_HEALTH_URL="${API_HEALTH_URL:-${APP_URL}/health}"
BACKEND_SERVICE="${BACKEND_SERVICE:-ddclass-backend}"
LOCAL_HEALTH_RETRIES="${LOCAL_HEALTH_RETRIES:-30}"
LOCAL_HEALTH_INTERVAL_SECONDS="${LOCAL_HEALTH_INTERVAL_SECONDS:-1}"

echo "==> systemd status"
systemctl --no-pager --full status "${BACKEND_SERVICE}" || true

echo "==> local backend health"
if wait_for_local_backend_health; then
  curl -fsS http://127.0.0.1:8001/health
else
  echo "Local backend health check failed after ${LOCAL_HEALTH_RETRIES} attempts."
  echo "Tip: increase LOCAL_HEALTH_RETRIES / LOCAL_HEALTH_INTERVAL_SECONDS and retry."
  exit 1
fi
echo

echo "==> public health"
# Follow HTTP->HTTPS redirects so a 301 from certbot-managed nginx is not a false failure.
if curl -fsSL "${API_HEALTH_URL}"; then
  :
else
  echo "Public health check failed. If you use HTTPS only, set API_HEALTH_URL to https://.../health" >&2
  exit 1
fi
echo

echo "==> nginx config test"
nginx -t

echo "==> recent backend logs"
journalctl -u "${BACKEND_SERVICE}" -n 30 --no-pager || true
