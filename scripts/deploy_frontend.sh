#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "Please run this script as root."
  exit 1
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
# shellcheck source=lib_deploy.sh
source "${REPO_ROOT}/scripts/lib_deploy.sh"
APP_ROOT="${APP_ROOT:-/opt/dd-class}"
SOURCE_DIR="${SOURCE_DIR:-${APP_ROOT}/source}"
ADMIN_WEB_ROOT="${ADMIN_WEB_ROOT:-/var/www/wailearning.xyz/admin}"
APP_USER="${APP_USER:-ddclass}"
CERT_NAME="${CERT_NAME:-www.wailearning.xyz}"
HTTP_TEMPLATE="${SOURCE_DIR}/nginx/wailearning.xyz.http.conf"
HTTPS_TEMPLATE="${SOURCE_DIR}/nginx/wailearning.xyz.conf"
CERT_DIR="/etc/letsencrypt/live/${CERT_NAME}"

if [[ -d /etc/nginx/sites-available ]]; then
  NGINX_SITE="/etc/nginx/sites-available/wailearning.xyz.conf"
  NGINX_LINK="/etc/nginx/sites-enabled/wailearning.xyz.conf"
else
  NGINX_SITE="/etc/nginx/conf.d/wailearning.xyz.conf"
  NGINX_LINK=""
fi

if [[ "${REPO_ROOT}" != "${SOURCE_DIR}" ]]; then
  install -d -m 0755 "${SOURCE_DIR}"
  rsync -a --delete \
    --exclude ".git" \
    --exclude "__pycache__" \
    --exclude ".pytest_cache" \
    --exclude "frontend/node_modules" \
    --exclude "frontend/dist" \
    --exclude "parent-portal/node_modules" \
    --exclude "parent-portal/dist" \
    "${REPO_ROOT}/" "${SOURCE_DIR}/"
fi

find "${SOURCE_DIR}" -type d -exec chmod 0755 {} +
find "${SOURCE_DIR}" -type f -exec chmod 0644 {} +
find "${SOURCE_DIR}/scripts" -type f -name "*.sh" -exec chmod 0755 {} +
chown -R "${APP_USER}:${APP_USER}" "${APP_ROOT}"

pushd "${SOURCE_DIR}/frontend" >/dev/null
npm ci
npm run build
popd >/dev/null

install -d -m 0755 /var/www/certbot
install -d -m 0755 "${ADMIN_WEB_ROOT}"
rsync -a --delete "${SOURCE_DIR}/frontend/dist/" "${ADMIN_WEB_ROOT}/"

if [[ -f "${CERT_DIR}/fullchain.pem" && -f "${CERT_DIR}/privkey.pem" ]]; then
  install -m 0644 "${HTTPS_TEMPLATE}" "${NGINX_SITE}"
else
  install -m 0644 "${HTTP_TEMPLATE}" "${NGINX_SITE}"
fi
if [[ -n "${NGINX_LINK}" ]]; then
  ln -sfn "${NGINX_SITE}" "${NGINX_LINK}"
  rm -f /etc/nginx/sites-enabled/default
fi

nginx -t
systemctl reload nginx

systemctl restart ddclass-backend.service
echo "==> Waiting for backend /health after restart"
if ! wait_for_local_backend_health; then
  exit 1
fi
