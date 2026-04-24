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
VENV_DIR="${VENV_DIR:-${APP_ROOT}/venv}"
SHARED_DIR="${SHARED_DIR:-${APP_ROOT}/shared}"
ENV_FILE="${ENV_FILE:-${SHARED_DIR}/.env.production}"
APP_USER="${APP_USER:-ddclass}"
SERVICE_FILE="/etc/systemd/system/ddclass-backend.service"
PYTHON_BIN="${PYTHON_BIN:-}"
SHARED_UPLOADS_DIR="${SHARED_DIR}/uploads"

if ! id -u "${APP_USER}" >/dev/null 2>&1; then
  echo "System user '${APP_USER}' does not exist. Run scripts/setup_server.sh first."
  exit 1
fi

install -d -m 0755 "${APP_ROOT}" "${SHARED_DIR}" "${SHARED_UPLOADS_DIR}" "${SHARED_UPLOADS_DIR}/attachments"

for legacy_uploads_dir in "${REPO_ROOT}/uploads" "${SOURCE_DIR}/uploads"; do
  if [[ -d "${legacy_uploads_dir}" ]]; then
    rsync -a "${legacy_uploads_dir}/" "${SHARED_UPLOADS_DIR}/"
  fi
done

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
    --exclude "uploads" \
    "${REPO_ROOT}/" "${SOURCE_DIR}/"
fi

if [[ ! -f "${ENV_FILE}" ]]; then
  install -m 0640 "${SOURCE_DIR}/.env.production" "${ENV_FILE}"
  echo "Created ${ENV_FILE}. Update all CHANGE_ME values, then rerun this script."
  exit 1
fi

if grep -q "CHANGE_ME" "${ENV_FILE}"; then
  echo "Please replace every CHANGE_ME placeholder in ${ENV_FILE} before deploying."
  exit 1
fi

if [[ -z "${PYTHON_BIN}" ]]; then
  for candidate in python3.11 python3.10 python3.9 python3.8 python3; do
    if command -v "${candidate}" >/dev/null 2>&1; then
      if "${candidate}" - <<'PY' >/dev/null 2>&1
import sys
raise SystemExit(0 if sys.version_info >= (3, 8) else 1)
PY
      then
        PYTHON_BIN="${candidate}"
        break
      fi
    fi
  done
fi

if [[ -z "${PYTHON_BIN}" ]]; then
  echo "Could not find a supported Python interpreter (>= 3.8)."
  exit 1
fi

echo "Using Python interpreter: ${PYTHON_BIN}"
"${PYTHON_BIN}" -m venv "${VENV_DIR}"
"${VENV_DIR}/bin/pip" install --upgrade pip wheel
"${VENV_DIR}/bin/pip" install -r "${SOURCE_DIR}/requirements.txt"

install -m 0644 "${SOURCE_DIR}/systemd/ddclass-backend.service" "${SERVICE_FILE}"

chown -R "${APP_USER}:${APP_USER}" "${APP_ROOT}"

systemctl daemon-reload
systemctl enable ddclass-backend.service
systemctl restart ddclass-backend.service
systemctl --no-pager --full status ddclass-backend.service || true

echo "==> Waiting for backend /health after restart"
if ! wait_for_local_backend_health; then
  exit 1
fi
