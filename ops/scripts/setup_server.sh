#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "Please run this script as root."
  exit 1
fi

APP_ROOT="${APP_ROOT:-/opt/dd-class}"
WEB_ROOT="${WEB_ROOT:-/var/www/wailearning.xyz}"
APP_USER="${APP_USER:-ddclass}"

export DEBIAN_FRONTEND=noninteractive

PKG_MANAGER=""

if command -v apt-get >/dev/null 2>&1; then
  PKG_MANAGER="apt"
elif command -v dnf >/dev/null 2>&1; then
  PKG_MANAGER="dnf"
elif command -v yum >/dev/null 2>&1; then
  PKG_MANAGER="yum"
else
  echo "Unsupported package manager. Expected apt-get, dnf, or yum."
  exit 1
fi

install_nodejs() {
  if command -v node >/dev/null 2>&1 && node --version | grep -Eq '^v(18|19|20|21|22)\.'; then
    return
  fi

  case "${PKG_MANAGER}" in
    apt)
      mkdir -p /etc/apt/keyrings
      if [[ ! -f /etc/apt/keyrings/nodesource.gpg ]]; then
        curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key \
          | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg
      fi
      cat >/etc/apt/sources.list.d/nodesource.list <<'EOF'
deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_20.x nodistro main
EOF
      apt-get update
      apt-get install -y nodejs
      ;;
    dnf|yum)
      curl -fsSL https://rpm.nodesource.com/setup_20.x | bash -
      "${PKG_MANAGER}" install -y nodejs
      ;;
  esac
}

if [[ "${PKG_MANAGER}" == "apt" ]]; then
  apt-get update
  apt-get install -y \
    ca-certificates \
    curl \
    git \
    gnupg \
    build-essential \
    libpq-dev \
    nginx \
    postgresql \
    postgresql-contrib \
    python3 \
    python3-pip \
    python3-venv \
    rsync \
    ufw \
    certbot \
    python3-certbot-nginx
else
  "${PKG_MANAGER}" install -y epel-release || true
  "${PKG_MANAGER}" install -y \
    ca-certificates \
    curl \
    git \
    gcc \
    gcc-c++ \
    make \
    nginx \
    postgresql \
    postgresql-server \
    postgresql-contrib \
    postgresql-devel \
    python3 \
    python3-pip \
    python3-devel \
    python3.11 \
    python3.11-devel \
    python3.11-pip \
    rsync \
    tar \
    firewalld \
    certbot || true
  "${PKG_MANAGER}" install -y python3-certbot-nginx || "${PKG_MANAGER}" install -y certbot-nginx || true
  "${PKG_MANAGER}" install -y policycoreutils-python-utils || "${PKG_MANAGER}" install -y policycoreutils || true
fi

install_nodejs

if ! id -u "${APP_USER}" >/dev/null 2>&1; then
  useradd --system --create-home --home-dir "/home/${APP_USER}" --shell /bin/bash "${APP_USER}"
fi

install -d -m 0755 -o "${APP_USER}" -g "${APP_USER}" \
  "${APP_ROOT}" \
  "${APP_ROOT}/shared" \
  "${APP_ROOT}/backups" \
  "${WEB_ROOT}" \
  "${WEB_ROOT}/admin" \
  "${WEB_ROOT}/parent"

if [[ "${PKG_MANAGER}" != "apt" ]]; then
  if command -v postgresql-setup >/dev/null 2>&1; then
    if [[ ! -f /var/lib/pgsql/data/PG_VERSION ]]; then
      postgresql-setup --initdb || postgresql-setup --initdb --unit postgresql || true
    fi
  fi
fi

systemctl enable --now postgresql
systemctl enable --now nginx

if command -v ufw >/dev/null 2>&1; then
  ufw allow OpenSSH || true
  ufw allow 'Nginx Full' || true
fi

if systemctl list-unit-files | grep -q '^firewalld.service'; then
  systemctl enable --now firewalld || true
  firewall-cmd --permanent --add-service=ssh || true
  firewall-cmd --permanent --add-service=http || true
  firewall-cmd --permanent --add-service=https || true
  firewall-cmd --reload || true
fi

if command -v getenforce >/dev/null 2>&1 && command -v setsebool >/dev/null 2>&1; then
  if [[ "$(getenforce)" != "Disabled" ]]; then
    setsebool -P httpd_can_network_connect 1 || true
  fi
fi

echo "Server prerequisites are ready."
echo "Next steps:"
echo "1. Copy or clone this repository to the server."
echo "2. Create ${APP_ROOT}/shared/.env.production from .env.production."
echo "3. Initialize PostgreSQL with ops/scripts/init_db.sql."
echo "4. Run ops/scripts/deploy_backend.sh, ops/scripts/deploy_frontend.sh, and ops/scripts/deploy_parent_portal.sh."
